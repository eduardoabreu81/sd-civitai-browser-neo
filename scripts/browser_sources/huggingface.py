"""Hugging Face browser source adapter.

Search public Hugging Face repositories and expose them as canonical models.
Download URLs point directly to ``https://huggingface.co/{repo_id}/resolve/main/{file}``.
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
    get_sha256,
    paginated_result,
)
from .registry import register_source


class HuggingFaceSource(BrowserSource):
    """Browser source adapter for Hugging Face (huggingface.co)."""

    BASE_URL = "https://huggingface.co"
    API_URL = "https://huggingface.co/api/models"

    # HF tags / repo ids → extension content type
    CONTENT_TYPE_HINTS = {
        "lora": "LORA",
        "stable-diffusion": "Checkpoint",
        "checkpoint": "Checkpoint",
        "textual-inversion": "TextualInversion",
        "vae": "VAE",
        "upscaler": "Upscaler",
        "embeddings": "TextualInversion",
        "motion-module": "MotionModule",
        "controlnet": "ControlNet",
    }

    # Filename substrings → extension content type
    FILENAME_TYPE_HINTS = {
        "lora": "LORA",
        "lycoris": "LoCon",
        "locon": "LoCon",
        "dora": "DoRA",
        "checkpoint": "Checkpoint",
        "textual_inversion": "TextualInversion",
        "embedding": "TextualInversion",
        "vae": "VAE",
        "upscaler": "Upscaler",
        "control_net": "ControlNet",
        "controlnet": "ControlNet",
    }

    # Base model detection: keyword → normalized name
    BASE_MODEL_HINTS = {
        "sdxl": "SDXL",
        "sd 1.5": "SD 1.5",
        "sd1.5": "SD 1.5",
        "pony": "Pony",
        "illustrious": "Illustrious",
        "anima": "Anima",
        "flux": "FLUX.1",
        "flux.1": "FLUX.1",
        "flux-schnell": "FLUX.1",
        "flux-dev": "FLUX.1",
        "wan": "Wan",
        "noobai": "NoobAI",
        "hunyuan": "HunyuanVideo",
        "svd": "Stable Video Diffusion",
        "stable-diffusion-xl": "SDXL",
        "stable-diffusion-3": "SD 3.5",
        "sd3": "SD 3.5",
        "stable-diffusion-2": "SD 2.1",
        "stable-diffusion-1": "SD 1.5",
        "stable-diffusion-v1-5": "SD 1.5",
        "stable-diffusion-xl-base": "SDXL",
        "stable-diffusion-xl": "SDXL",
        "lightricks/ltx": "LTX",
    }

    # HF pipeline_tag / tags → extension content type
    PIPELINE_TYPE_HINTS = {
        "text-to-image": "Checkpoint",
        "image-to-image": "Checkpoint",
        "text-to-video": "Checkpoint",
        "video-to-video": "Checkpoint",
        "text-to-image-generation": "Checkpoint",
    }

    def __init__(self) -> None:
        super().__init__("huggingface", "Hugging Face")

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------
    def supports(self, content_type: Optional[str]) -> bool:
        """Hugging Face repos can hold any model type; detection is heuristic."""
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
        """Search Hugging Face repositories and return canonical models."""
        if not query or not query.strip():
            return paginated_result([], current_page=page, page_size=page_size, source=self.name)

        # Map extension content type(s) to HF filters when possible.
        hf_filter = self._content_type_to_hf_filter(content_type)
        params: dict[str, Any] = {
            "search": query.strip(),
            "limit": page_size,
            "full": "true",
        }
        if hf_filter:
            params["filter"] = hf_filter

        url = f"{self.API_URL}?{self._encode_params(params)}"
        data = self._request_json(url)
        if isinstance(data, str):
            return data
        if not isinstance(data, list):
            return paginated_result([], current_page=page, page_size=page_size, source=self.name)

        # Build canonical models from repo summaries.
        models: list[dict] = []
        for repo in data:
            if not isinstance(repo, dict):
                continue
            model = self._normalize_repo_summary(repo)
            if model:
                models.append(model)

        # Apply simple client-side pagination (HF search is cursor-based).
        total_items = len(models)
        total_pages = max(1, (total_items + page_size - 1) // page_size)
        start = (page - 1) * page_size
        page_models = models[start:start + page_size]

        return paginated_result(
            page_models,
            current_page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            source=self.name,
        )

    def get_model(self, source_id: str, **kwargs: Any) -> Optional[dict]:
        """Fetch a single HF repo by id (repo_id)."""
        repo_id = source_id.strip()
        url = f"{self.API_URL}/{repo_id}"
        data = self._request_json(url)
        if isinstance(data, str) or not isinstance(data, dict):
            return None
        return self._normalize_repo_detail(repo_id, data)

    # ------------------------------------------------------------------
    # Download helpers
    # ------------------------------------------------------------------
    def get_download_url(self, file_info: dict, **kwargs: Any) -> Optional[str]:
        """Return a direct Hugging Face resolve URL for a canonical file dict."""
        if not isinstance(file_info, dict):
            return None
        raw = file_info.get("browserSourceFileRaw") or {}
        repo_id = raw.get("repo_id")
        path = raw.get("path") or file_info.get("name")
        if repo_id and path:
            return f"{self.BASE_URL}/{quote(repo_id, safe='/')}/resolve/main/{quote(path, safe='/')}"
        return file_info.get("downloadUrl") or file_info.get("download_url")

    # ------------------------------------------------------------------
    # Normalization
    # ------------------------------------------------------------------
    def _normalize_repo_summary(self, repo: dict) -> Optional[dict]:
        """Build a canonical model from a HF search result item."""
        repo_id = repo.get("id")
        if not repo_id:
            return None

        tags = [str(t) for t in repo.get("tags", []) if t]
        pipeline_tag = repo.get("pipeline_tag", "")
        model_type = self._detect_content_type(tags, repo_id, pipeline_tag)
        base_model = self._detect_base_model(tags, repo_id, repo.get("modelId", ""))
        nsfw = any("nsfw" in t.lower() for t in tags) or "nsfw" in repo_id.lower()

        # Search result may include siblings (file list). Build real files when available.
        siblings = repo.get("siblings") or []
        files = self._siblings_to_files(repo_id, siblings)

        version = canonical_version(
            source_version_id="main",
            name="main",
            base_model=base_model,
            description=repo.get("description") or "",
            files=files,
            images=self._siblings_to_images(repo_id, siblings),
            download_url=f"{self.BASE_URL}/{quote(repo_id, safe='/')}",
            raw=repo,
        )

        return canonical_model(
            source=self.name,
            source_id=repo_id,
            name=repo.get("modelId") or repo_id.split("/")[-1],
            model_type=model_type,
            source_url=f"{self.BASE_URL}/{quote(repo_id, safe='/')}",
            description=repo.get("description") or "",
            creator={"username": repo_id.split("/")[0]} if "/" in repo_id else {},
            tags=tags,
            base_model=base_model,
            nsfw=nsfw,
            versions=[version],
            raw=repo,
        )

    def _normalize_repo_detail(self, repo_id: str, data: dict) -> Optional[dict]:
        """Build a canonical model from a full HF repo detail response."""
        tags = [str(t) for t in data.get("tags", []) if t]
        model_type = self._detect_content_type(tags, repo_id)
        base_model = self._detect_base_model(tags, repo_id, data.get("modelId", ""))
        nsfw = any("nsfw" in t.lower() for t in tags) or "nsfw" in repo_id.lower()

        files = self._fetch_repo_files(repo_id)
        if not files:
            # Fallback: one synthetic file so the card can still render.
            files = [canonical_file(
                filename="model.safetensors",
                download_url=f"{self.BASE_URL}/{quote(repo_id, safe='/')}",
                primary=True,
                raw={"repo_id": repo_id, "path": ""},
            )]

        # Try to find a preview image in the repo files.
        images = self._pick_preview_images(repo_id, files)

        version = canonical_version(
            source_version_id="main",
            name="main",
            base_model=base_model,
            description=data.get("description") or "",
            files=files,
            images=images,
            download_url=f"{self.BASE_URL}/{quote(repo_id, safe='/')}",
            raw=data,
        )

        return canonical_model(
            source=self.name,
            source_id=repo_id,
            name=data.get("modelId") or repo_id.split("/")[-1],
            model_type=model_type,
            source_url=f"{self.BASE_URL}/{quote(repo_id, safe='/')}",
            description=data.get("description") or "",
            creator={"username": repo_id.split("/")[0]} if "/" in repo_id else {},
            tags=tags,
            base_model=base_model,
            nsfw=nsfw,
            versions=[version],
            raw=data,
        )

    def _fetch_repo_files(self, repo_id: str) -> list[dict]:
        """List downloadable model files in the repo's main branch."""
        url = f"{self.API_URL}/{quote(repo_id, safe='/')}/tree/main"
        data = self._request_json(url)
        if not isinstance(data, list):
            return []

        result: list[dict] = []
        model_extensions = (".safetensors", ".ckpt", ".pt", ".pth", ".bin", ".onnx")
        for entry in data:
            if not isinstance(entry, dict):
                continue
            path = entry.get("path", "")
            lower_path = path.lower()
            if not any(lower_path.endswith(ext) for ext in model_extensions):
                continue
            size = entry.get("size")
            size_kb = size / 1024 if isinstance(size, (int, float)) else None
            result.append(canonical_file(
                filename=path.split("/")[-1],
                size_kb=size_kb,
                size_bytes=size,
                download_url=f"{self.BASE_URL}/{quote(repo_id, safe='/')}/resolve/main/{quote(path, safe='/')}",
                primary=lower_path.endswith(".safetensors") and result == [],
                raw={"repo_id": repo_id, "path": path},
            ))

        # Prefer .safetensors as primary.
        result.sort(key=lambda f: (
            0 if str(f.get("name", "")).lower().endswith(".safetensors") else
            1 if str(f.get("name", "")).lower().endswith(".ckpt") else
            2
        ))
        for i, f in enumerate(result):
            f["primary"] = i == 0
        return result

    def _pick_preview_images(self, repo_id: str, files: list[dict]) -> list[dict]:
        """Return canonical preview images found in repo files."""
        images: list[dict] = []
        for f in files:
            raw = f.get("browserSourceFileRaw") or {}
            path = raw.get("path") or f.get("name", "")
            lower = path.lower()
            if lower.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
                url = f"{self.BASE_URL}/{quote(repo_id, safe='/')}/resolve/main/{quote(path, safe='/')}"
                images.append(canonical_image(url=url, raw={"repo_id": repo_id, "path": path}))
        # Limit to a reasonable number of previews.
        return images[:9]

    # ------------------------------------------------------------------
    # Detection helpers
    # ------------------------------------------------------------------
    def _siblings_to_files(self, repo_id: str, siblings: list[dict]) -> list[dict]:
        """Convert HF sibling entries into canonical file dicts."""
        result: list[dict] = []
        model_extensions = (".safetensors", ".ckpt", ".pt", ".pth", ".bin", ".onnx")
        for s in siblings:
            if not isinstance(s, dict):
                continue
            path = s.get("rfilename", "")
            lower = path.lower()
            if not any(lower.endswith(ext) for ext in model_extensions):
                continue
            result.append(canonical_file(
                filename=path.split("/")[-1],
                download_url=f"{self.BASE_URL}/{quote(repo_id, safe='/')}/resolve/main/{quote(path, safe='/')}",
                primary=False,
                raw={"repo_id": repo_id, "path": path},
            ))
        result.sort(key=lambda f: (
            0 if str(f.get("name", "")).lower().endswith(".safetensors") else
            1 if str(f.get("name", "")).lower().endswith(".ckpt") else
            2
        ))
        for i, f in enumerate(result):
            f["primary"] = i == 0
        return result

    def _siblings_to_images(self, repo_id: str, siblings: list[dict]) -> list[dict]:
        """Convert HF image siblings into canonical image dicts."""
        images: list[dict] = []
        for s in siblings:
            if not isinstance(s, dict):
                continue
            path = s.get("rfilename", "")
            lower = path.lower()
            if not lower.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
                continue
            url = f"{self.BASE_URL}/{quote(repo_id, safe='/')}/resolve/main/{quote(path, safe='/')}"
            images.append(canonical_image(url=url, raw={"repo_id": repo_id, "path": path}))
        return images[:9]

    def _detect_content_type(self, tags: list[str], repo_id: str, pipeline_tag: str = "") -> str:
        """Infer extension content type from HF tags, pipeline_tag and repo name."""
        lower_tags = [t.lower() for t in tags]
        combined = " ".join(lower_tags) + " " + repo_id.lower() + " " + str(pipeline_tag).lower()

        for hint, ctype in self.CONTENT_TYPE_HINTS.items():
            if hint in lower_tags or hint in repo_id.lower():
                return ctype

        for hint, ctype in self.PIPELINE_TYPE_HINTS.items():
            if hint in str(pipeline_tag).lower():
                return ctype

        for hint, ctype in self.FILENAME_TYPE_HINTS.items():
            if hint in combined:
                return ctype

        return "Other"

    def _detect_base_model(self, tags: list[str], repo_id: str, model_id: str) -> Optional[str]:
        """Infer base model family from HF tags/repo names."""
        # HF sometimes encodes the base model in tags like "base_model:runwayml/stable-diffusion-v1-5"
        for tag in tags:
            lower = str(tag).lower()
            if lower.startswith("base_model:"):
                base_value = lower.split(":", 1)[1]
                for hint, base in self.BASE_MODEL_HINTS.items():
                    if hint in base_value:
                        return base
                # Return the raw base_model value if no known mapping.
                return base_value

        text = " ".join(tags).lower() + " " + repo_id.lower() + " " + model_id.lower()
        for hint, base in self.BASE_MODEL_HINTS.items():
            if hint in text:
                return base
        return None

    def _content_type_to_hf_filter(self, content_type: Optional[str | list[str]]) -> Optional[str]:
        """Map extension content type to a HF model tag filter."""
        if not content_type:
            return None
        types = content_type if isinstance(content_type, list) else [content_type]
        for t in types:
            lower = str(t).lower()
            if lower in ("lora", "locon", "dora"):
                return "lora"
            if lower == "textualinversion":
                return "textual-inversion"
            if lower == "checkpoint":
                return "stable-diffusion"
            if lower == "vae":
                return "vae"
            if lower == "upscaler":
                return "upscaler"
        return None

    # ------------------------------------------------------------------
    # Request helpers
    # ------------------------------------------------------------------
    def _request_json(self, url: str) -> Any:
        """Make a GET request and return JSON or an error string."""
        headers = _api.get_headers()
        proxies, verify = _api.get_proxies()
        try:
            response = requests.get(url, headers=headers, proxies=proxies, verify=verify, timeout=(60, 30))
        except requests.exceptions.RequestException as exc:
            debug_print(f"[HuggingFace] request failed: {exc}")
            return "offline"

        if response.status_code == 404:
            return "not_found"
        if response.status_code == 503:
            return "offline"
        if response.status_code == 429:
            return "error"
        if response.status_code != 200:
            debug_print(f"[HuggingFace] unexpected status {response.status_code} for {url}")
            return "error"

        try:
            return response.json()
        except Exception as exc:
            debug_print(f"[HuggingFace] JSON decode failed: {exc}")
            return "error"

    @staticmethod
    def _encode_params(params: dict[str, Any]) -> str:
        """URL-encode parameters, keeping lists as repeated keys."""
        parts: list[tuple[str, str]] = []
        for key, value in params.items():
            if isinstance(value, list):
                for v in value:
                    parts.append((key, str(v)))
            else:
                parts.append((key, str(value)))
        return "&".join(f"{quote(k, safe='')}={quote(v, safe='')}" for k, v in parts)


# Register on import.
register_source(HuggingFaceSource())
