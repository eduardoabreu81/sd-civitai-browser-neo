"""arcenciel.io browser source adapter.

arcenciel.io hosts anime/NoobAI/Anima/etc. models and provides rich metadata
including base model, activation tags, images and direct downloads.
"""

from __future__ import annotations

import re
from typing import Any, Optional
from urllib.parse import quote

import requests

import scripts.civitai_api as _api
from scripts.civitai_global import debug_print

from .base import BrowserSource
from .normalizer import (
    canonical_file,
    canonical_image,
    canonical_model,
    canonical_version,
    paginated_result,
)
from .registry import register_source


class ArcencielSource(BrowserSource):
    """Browser source adapter for arcenciel.io."""

    BASE_URL = "https://arcenciel.io"
    API_URL = "https://arcenciel.io/api"
    UPLOADS_URL = "https://uploads.arcenciel.io/api"
    MEDIA_URL = "https://media.arcenciel.io/uploads"

    CONTENT_TYPE_MAP = {
        "LORA": "LORA",
        "CHECKPOINT": "Checkpoint",
        "TEXTUAL_INVERSION": "TextualInversion",
        "VAE": "VAE",
        "UPSCALER": "Upscaler",
        "CONTROLNET": "ControlNet",
        "MOTION_MODULE": "MotionModule",
        "LORA_SLIDER": "LORA",
        "STYLE": "LORA",
    }

    def __init__(self) -> None:
        super().__init__("arcenciel", "arcenciel.io")

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------
    def supports(self, content_type: Optional[str]) -> bool:
        return True

    def supported_search_types(self) -> list[str]:
        return ["Model name"]

    def supports_pagination(self) -> bool:
        return True

    # ------------------------------------------------------------------
    # Search / fetch
    # ------------------------------------------------------------------
    def search(
        self,
        *,
        query: str = "",
        search_type: str = "Model name",
        content_type: Optional[str | list[str]] = None,
        base_filter: Optional[str | list[str]] = None,
        sort: str = "Highest Rated",
        period: str = "Month",
        nsfw: bool = False,
        exact: bool = True,
        page: int = 1,
        page_size: int = 20,
        only_liked: bool = False,
        **kwargs: Any,
    ) -> dict:
        """Search arcenciel.io models and return canonical results."""
        if not query or not query.strip():
            return paginated_result([], current_page=page, page_size=page_size, source=self.name)

        params: dict[str, Any] = {"q": query.strip(), "limit": page_size}
        if page > 1:
            params["page"] = page

        url = f"{self.API_URL}/models/search?{self._encode_params(params)}"
        data = self._request_json(url)
        if isinstance(data, str):
            return data
        if not isinstance(data, dict):
            return paginated_result([], current_page=page, page_size=page_size, source=self.name)

        items = [self._normalize_model(item) for item in data.get("data", []) if isinstance(item, dict)]

        # arcenciel returns page/limit in the response; estimate total pages.
        current_page = data.get("page", page)
        limit = data.get("limit", page_size)
        has_more = len(items) >= limit
        total_pages = current_page if not has_more else current_page + 1

        return paginated_result(
            items,
            current_page=current_page,
            page_size=limit,
            total_items=len(items),
            total_pages=total_pages,
            source=self.name,
        )

    def get_model(self, source_id: str, **kwargs: Any) -> Optional[dict]:
        """Fetch a single arcenciel model by id."""
        url = f"{self.API_URL}/models/{source_id}"
        data = self._request_json(url)
        if isinstance(data, str) or not isinstance(data, dict):
            return None
        return self._normalize_model(data)

    # ------------------------------------------------------------------
    # Download helpers
    # ------------------------------------------------------------------
    def get_download_url(self, file_info: dict, **kwargs: Any) -> Optional[str]:
        """Return the arcenciel direct download URL for a canonical file dict."""
        if not isinstance(file_info, dict):
            return None
        raw = file_info.get("browserSourceFileRaw") or {}
        model_id = raw.get("model_id")
        version_id = raw.get("version_id")
        if model_id and version_id:
            return f"{self.UPLOADS_URL}/models/{model_id}/versions/{version_id}/download"
        return file_info.get("downloadUrl") or file_info.get("download_url")

    def get_preview_url(self, image_info: dict, **kwargs: Any) -> Optional[str]:
        """Return an arcenciel media URL for an image dict."""
        if not isinstance(image_info, dict):
            return None
        raw = image_info.get("browserSourceImageRaw") or {}
        file_path = raw.get("file_path")
        if file_path:
            return self._image_url(file_path)
        return image_info.get("url")

    # ------------------------------------------------------------------
    # Normalization
    # ------------------------------------------------------------------
    def _normalize_model(self, item: dict) -> Optional[dict]:
        """Convert an arcenciel model payload to canonical format."""
        if not isinstance(item, dict):
            return None

        model_id = item.get("id")
        if model_id is None:
            return None

        tags = [str(t.get("name", "")) for t in item.get("tags", []) if isinstance(t, dict)]
        raw_type = str(item.get("type", "")).upper()
        model_type = self.CONTENT_TYPE_MAP.get(raw_type, raw_type.title() or "Other")
        nsfw = any("nsfw" in t.lower() or "adult" in t.lower() for t in tags)

        creator = item.get("uploader") or {}
        creator_dict = {"username": creator.get("username", "")} if isinstance(creator, dict) else {}

        versions = self._build_versions(item, model_id)

        return canonical_model(
            source=self.name,
            source_id=str(model_id),
            name=item.get("title") or f"Model {model_id}",
            model_type=model_type,
            source_url=f"{self.BASE_URL}/models/{model_id}",
            description=item.get("description") or "",
            creator=creator_dict,
            tags=tags,
            nsfw=nsfw,
            versions=versions,
            raw=item,
        )

    def _build_versions(self, item: dict, model_id: Any) -> list[dict]:
        """Build canonical versions from arcenciel version entries."""
        versions: list[dict] = []
        version_order = item.get("versionOrder") or []

        # Prefer versionOrder to keep the display order consistent with the site.
        raw_versions = item.get("versions", []) or []
        ordered = []
        seen_ids = set()
        by_id = {}
        for v in raw_versions:
            if isinstance(v, dict):
                by_id[v.get("id")] = v

        for vid in version_order:
            if vid in by_id and vid not in seen_ids:
                ordered.append(by_id[vid])
                seen_ids.add(vid)
        for v in raw_versions:
            if isinstance(v, dict) and v.get("id") not in seen_ids:
                ordered.append(v)

        for v in ordered:
            version_id = v.get("id")
            file_name = v.get("fileName") or "model.safetensors"
            file_path = v.get("filePath") or ""
            base_model = v.get("baseModel") or self._base_model_from_class(v.get("modelClassId"))

            file_info = canonical_file(
                filename=file_name,
                size_kb=v.get("fileSizeKb"),
                sha256=v.get("sha256"),
                download_url=f"{self.UPLOADS_URL}/models/{model_id}/versions/{version_id}/download",
                primary=True,
                raw={"model_id": model_id, "version_id": version_id, "file_path": file_path},
            )

            activation_tags = v.get("activationTags") or []
            trained_words = [t for t in activation_tags if isinstance(t, str)]

            images = self._build_images(v.get("images", []) or [])

            versions.append(canonical_version(
                source_version_id=str(version_id),
                name=v.get("versionName") or "v1",
                base_model=base_model,
                description=v.get("aboutThisVersion") or "",
                trained_words=trained_words,
                files=[file_info],
                images=images,
                download_url=f"{self.UPLOADS_URL}/models/{model_id}/versions/{version_id}/download",
                stats={"downloadCount": v.get("downloadCount")},
                raw=v,
            ))

        return versions

    def _build_images(self, images: list[dict]) -> list[dict]:
        """Convert arcenciel image entries to canonical images."""
        result: list[dict] = []
        for img in images:
            if not isinstance(img, dict):
                continue
            file_path = img.get("filePath")
            if not file_path:
                continue
            variants = img.get("variants") or []
            # Prefer a medium webp variant when available.
            preferred = next(
                (v for v in variants if isinstance(v, dict) and v.get("label") in ("w1024", "w512")),
                None,
            )
            if preferred:
                url = f"{self.MEDIA_URL}/{preferred.get('path')}"
            else:
                url = self._image_url(file_path)
            result.append(canonical_image(
                url=url,
                width=img.get("width"),
                height=img.get("height"),
                raw={"file_path": file_path, "variants": variants},
            ))
        return result[:9]

    def _image_url(self, file_path: str) -> str:
        """Build a media URL from an arcenciel file path."""
        return f"{self.MEDIA_URL}/{quote(file_path, safe='/')}"

    def _base_model_from_class(self, class_id: Optional[int]) -> Optional[str]:
        """Map arcenciel modelClassId to a base model name.

        This is a lightweight fallback; the API already provides baseModel
        on versions in most cases.
        """
        mapping = {
            1: "Illustrious 0.1",
            2: "SD 3.5 Medium",
            3: "WAN 2.1 Video",
            4: "Illustrious",
            5: "Chroma",
            6: "SD 3.5 Large",
            7: "Flux.1 D",
            8: "SD 1.5",
            9: "NoobAI Eps",
            10: "Other",
            11: "Pony",
            12: "SDXL 1.0",
            13: "Hunyuan Framepack",
            14: "SD1.5",
            15: "NoobAI V-Pred",
            16: "NoobAI Flux2V",
            17: "Lumina",
            18: "Wan",
            19: "Chenkin RF",
            20: "Anima",
        }
        return mapping.get(class_id)

    # ------------------------------------------------------------------
    # Request helpers
    # ------------------------------------------------------------------
    def _request_json(self, url: str) -> Any:
        """Make a GET request and return JSON or an error string."""
        headers = _api.get_headers()
        headers.setdefault("Referer", f"{self.BASE_URL}/")
        proxies, verify = _api.get_proxies()
        try:
            response = requests.get(url, headers=headers, proxies=proxies, verify=verify, timeout=(60, 30))
        except requests.exceptions.RequestException as exc:
            debug_print(f"[arcenciel] request failed: {exc}")
            return "offline"

        if response.status_code == 404:
            return "not_found"
        if response.status_code == 503:
            return "offline"
        if response.status_code == 429:
            return "error"
        if response.status_code != 200:
            debug_print(f"[arcenciel] unexpected status {response.status_code} for {url}")
            return "error"

        try:
            return response.json()
        except Exception as exc:
            debug_print(f"[arcenciel] JSON decode failed: {exc}")
            return "error"

    @staticmethod
    def _encode_params(params: dict[str, Any]) -> str:
        """URL-encode parameters."""
        parts: list[tuple[str, str]] = []
        for key, value in params.items():
            if isinstance(value, list):
                for v in value:
                    parts.append((key, str(v)))
            else:
                parts.append((key, str(value)))
        return "&".join(f"{quote(k, safe='')}={quote(v, safe='')}" for k, v in parts)


# Register on import.
register_source(ArcencielSource())
