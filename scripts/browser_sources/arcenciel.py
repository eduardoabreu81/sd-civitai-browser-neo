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

    CONTENT_TYPE_ALIASES = {
        "CHECKPOINT": "Checkpoint",
        "LORA": "LORA",
        "LORAS": "LORA",
        "LOCON": "LoCon",
        "DORA": "DoRA",
        "TEXTUALINVERSION": "TextualInversion",
        "TEXTUAL_INVERSION": "TextualInversion",
        "VAE": "VAE",
        "UPSCALER": "Upscaler",
        "CONTROLNET": "ControlNet",
        "CONTROLNETS": "ControlNet",
        "MOTIONMODULE": "MotionModule",
        "MOTION_MODULE": "MotionModule",
    }

    def __init__(self) -> None:
        super().__init__("arcenciel", "Arc en Ciel")

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
        page = max(1, int(page or 1))
        page_size = max(1, int(page_size or 20))
        clean_query = query.strip() if isinstance(query, str) else ""
        target_content_types = self._resolve_content_type_filter(content_type)
        target_base_models = self._resolve_base_model_filter(base_filter)
        use_local_filters = bool(target_content_types or target_base_models)
        fetch_limit = min(max(page * page_size * 4, page_size), 300) if use_local_filters else page_size
        debug_print(
            f"[Arc en Ciel] search query='{clean_query or '<browse>'}' page={page} "
            f"page_size={page_size} fetch_limit={fetch_limit} "
            f"content_filter={target_content_types or '<any>'} base_filter={target_base_models or '<any>'}"
        )

        params: dict[str, Any] = {"limit": fetch_limit}
        if clean_query:
            params["q"] = clean_query
        else:
            debug_print("[Arc en Ciel] empty query, using browse mode")
        if page > 1 and not use_local_filters:
            params["page"] = page

        url = f"{self.API_URL}/models/search?{self._encode_params(params)}"
        data = self._request_json(url)
        if isinstance(data, str):
            debug_print(f"[Arc en Ciel] search returned error string: {data}")
            return data
        if not isinstance(data, dict):
            debug_print(f"[Arc en Ciel] unexpected search response type: {type(data)}")
            return paginated_result([], current_page=page, page_size=page_size, source=self.name)

        raw_items = [item for item in data.get("data", []) if isinstance(item, dict)]
        normalized_items = [
            model
            for item in raw_items
            for model in [self._normalize_model(item)]
            if model is not None
        ]
        filtered_items = [
            model
            for model in normalized_items
            if self._matches_content_type_filter(model, target_content_types)
            and self._matches_base_model_filter(model, target_base_models)
        ]
        if target_base_models:
            filtered_items = [
                self._with_filtered_versions(model, target_base_models)
                for model in filtered_items
            ]
            filtered_items = [model for model in filtered_items if model.get("modelVersions")]

        if use_local_filters:
            start = (page - 1) * page_size
            items = filtered_items[start:start + page_size]
            current_page = page
            limit = page_size
            total_items = len(filtered_items)
            total_pages = max(1, (total_items + page_size - 1) // page_size)
        else:
            items = filtered_items
            # arcenciel returns page/limit plus totalCount/totalPages when available.
            current_page = data.get("page", page)
            limit = data.get("limit", page_size)
            total_items = data.get("totalCount", len(items))
            total_pages = data.get("totalPages")
            if not total_pages:
                has_more = len(items) >= limit
                total_pages = current_page if not has_more else current_page + 1

        debug_print(
            f"[Arc en Ciel] raw_items={len(raw_items)} normalized_models={len(normalized_items)} "
            f"filtered_models={len(filtered_items)} page_items={len(items)} "
            f"current_page={current_page} total_pages={total_pages}"
        )

        return paginated_result(
            items,
            current_page=current_page,
            page_size=limit,
            total_items=total_items,
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
            trained_words = self._normalize_activation_tags(activation_tags)

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

    def _normalize_activation_tags(self, activation_tags: Any) -> list[str]:
        """Normalize arcenciel activationTags into a list of trigger words."""
        if isinstance(activation_tags, str):
            return [tag.strip() for tag in re.split(r"[,;\n]+", activation_tags) if tag.strip()]
        if isinstance(activation_tags, list):
            return [tag.strip() for tag in activation_tags if isinstance(tag, str) and tag.strip()]
        return []

    def _resolve_content_type_filter(self, content_type: Optional[str | list[str]]) -> list[str]:
        """Normalize UI content type values into canonical Arc en Ciel model types."""
        if not content_type:
            return []
        values = content_type if isinstance(content_type, list) else [content_type]
        result: list[str] = []
        for value in values:
            key = re.sub(r"[^A-Z0-9]+", "_", str(value).upper()).strip("_")
            mapped = self.CONTENT_TYPE_ALIASES.get(key) or self.CONTENT_TYPE_ALIASES.get(key.replace("_", ""))
            if mapped and mapped not in result:
                result.append(mapped)
        return result

    def _resolve_base_model_filter(self, base_filter: Optional[str | list[str]]) -> list[str]:
        """Normalize UI base model values for case-insensitive matching."""
        if not base_filter:
            return []
        values = base_filter if isinstance(base_filter, list) else [base_filter]
        result: list[str] = []
        for value in values:
            normalized = str(value or "").strip()
            if normalized and normalized != "All":
                result.append(normalized)
        return result

    def _matches_content_type_filter(self, model: dict, target_content_types: list[str]) -> bool:
        if not target_content_types:
            return True
        model_type = str(model.get("type", "")).lower()
        return any(model_type == str(target).lower() for target in target_content_types)

    def _matches_base_model_filter(self, model: dict, target_base_models: list[str]) -> bool:
        if not target_base_models:
            return True
        versions = model.get("modelVersions") or []
        return any(
            self._base_matches(version.get("baseModel"), target)
            for version in versions
            for target in target_base_models
        )

    def _with_filtered_versions(self, model: dict, target_base_models: list[str]) -> dict:
        """Return a shallow copy with only versions matching the selected base model."""
        versions = [
            version
            for version in (model.get("modelVersions") or [])
            if any(self._base_matches(version.get("baseModel"), target) for target in target_base_models)
        ]
        model_copy = dict(model)
        model_copy["modelVersions"] = versions
        if versions:
            model_copy["baseModel"] = versions[0].get("baseModel")
        return model_copy

    @staticmethod
    def _base_matches(value: Any, target: str) -> bool:
        value_text = str(value or "").lower()
        target_text = str(target or "").lower()
        if not value_text or not target_text:
            return False
        return value_text == target_text or target_text in value_text

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
