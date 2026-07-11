"""ModelScope browser source adapter.

Search and fetch models from www.modelscope.cn and expose them in the
extension's canonical format. Download URLs point to the HF-compatible
``https://www.modelscope.cn/models/{owner}/{repo}/resolve/master/{path}``
endpoint.
"""

from __future__ import annotations

import json
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


class ModelScopeSource(BrowserSource):
    """Browser source adapter for ModelScope (www.modelscope.cn)."""

    BASE_URL = "https://www.modelscope.cn"
    API_URL = "https://www.modelscope.cn/api/v1"

    # ModelScope MuseInfo modelType → extension content type
    MUSE_CONTENT_TYPE_MAP = {
        "lora": "LORA",
        "checkpoint": "Checkpoint",
        "stable-diffusion": "Checkpoint",
        "stable_diffusion": "Checkpoint",
        "textual-inversion": "TextualInversion",
        "textual_inversion": "TextualInversion",
        "vae": "VAE",
        "upscaler": "Upscaler",
        "controlnet": "ControlNet",
        "control_net": "ControlNet",
        "motion-module": "MotionModule",
        "motion_module": "MotionModule",
    }

    # Tags / repo ids → extension content type
    CONTENT_TYPE_HINTS = {
        "lora": "LORA",
        "stable-diffusion": "Checkpoint",
        "checkpoint": "Checkpoint",
        "diffusion-single-file": "Checkpoint",
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
        "hunyuanvideo": "HunyuanVideo",
        "svd": "Stable Video Diffusion",
        "stable-diffusion-xl": "SDXL",
        "stable-diffusion-3": "SD 3.5",
        "sd3": "SD 3.5",
        "stable-diffusion-2": "SD 2.1",
        "stable-diffusion-1": "SD 1.5",
        "stable-diffusion-v1-5": "SD 1.5",
        "stable-diffusion-xl-base": "SDXL",
        "lightricks/ltx": "LTX",
        "ltx": "LTX",
        "qwen": "Qwen",
        "qwen-image": "Qwen Image",
    }

    # ModelScope MuseInfo stableDiffusionVersion → extension base model
    MUSE_BASE_MODEL_MAP = {
        "SD_1_5": "SD 1.5",
        "SD_1_4": "SD 1.5",
        "SD_2_1": "SD 2.1",
        "SDXL_1_0": "SDXL",
        "PONY": "Pony",
        "ILLUSTRIOUS": "Illustrious",
        "NOOBAI": "NoobAI",
        "FLUX_1_D": "FLUX.1",
        "FLUX_1_S": "FLUX.1",
        "FLUX_1": "FLUX.1",
        "WAN_2_1": "Wan",
        "WAN": "Wan",
        "WAN_2_2": "Wan",
        "HUNYUAN_VIDEO": "HunyuanVideo",
        "HUNYUAN": "HunyuanVideo",
        "LTX": "LTX",
        "LTXV": "LTX",
        "LTX_VIDEO": "LTX",
        "ANEMA": "Anima",
        "ANIMA": "Anima",
        "QWEN_IMAGE": "Qwen Image",
        "QWEN_IMAGE_20_B": "Qwen Image",
        "QWEN": "Qwen",
    }

    def __init__(self) -> None:
        super().__init__("modelscope", "ModelScope", visible_in_dropdown=True)

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------
    def supports(self, content_type: Optional[str]) -> bool:
        """ModelScope repos can hold any model type; detection is heuristic."""
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
        """Search ModelScope models and return canonical results."""
        clean_query = (query or "").strip()
        normalized_page = max(1, int(page or 1))
        normalized_page_size = max(1, int(page_size or 20))
        target_content_types = self._resolve_content_type_filter(content_type)
        target_base_models = self._resolve_base_model_filter(base_filter, clean_query)

        body = {
            "PageSize": normalized_page_size,
            "PageNumber": normalized_page,
            "SortBy": "Default",
            "Target": "",
            "SingleCriterion": [],
            "Name": clean_query,
            "Criterion": [],
        }

        debug_print(
            f"[ModelScope] search query='{clean_query or '<browse>'}' "
            f"page={normalized_page} page_size={normalized_page_size} "
            f"content_filter={target_content_types or '<any>'} "
            f"base_filter={target_base_models or '<any>'}"
        )

        url = f"{self.API_URL}/dolphin/models"
        data = self._request_json(url, method="PUT", json=body)
        if isinstance(data, str):
            debug_print(f"[ModelScope] search returned error string: {data}")
            return data
        if not isinstance(data, dict):
            debug_print(f"[ModelScope] unexpected search response type: {type(data)}")
            return paginated_result(
                [],
                current_page=normalized_page,
                page_size=normalized_page_size,
                source=self.name,
            )

        models_data = data.get("Data", {}).get("Model", {}).get("Models", [])
        if not isinstance(models_data, list):
            models_data = []

        normalized_items: list[dict] = []
        discarded_type = 0
        discarded_base = 0
        discarded_no_files = 0
        for item in models_data:
            if not isinstance(item, dict):
                continue
            model = self._normalize_search_item(item)
            if not model:
                continue
            versions = model.get("modelVersions", [])
            files = versions[0].get("files", []) if versions else []
            if not files:
                discarded_no_files += 1
                continue
            if not self._matches_content_type_filter(model, target_content_types):
                discarded_type += 1
                continue
            if not self._matches_base_model_filter(model, target_base_models):
                discarded_base += 1
                continue
            normalized_items.append(model)

        # ModelScope already paginates server-side; use its envelope when available.
        total_items = data.get("Data", {}).get("Model", {}).get("TotalCount") if isinstance(data.get("Data"), dict) else None
        total_pages = None
        if total_items is None:
            total_items = len(normalized_items)
            total_pages = normalized_page
            if len(models_data) >= normalized_page_size:
                total_pages = normalized_page + 1
        else:
            total_pages = max(1, (total_items + normalized_page_size - 1) // normalized_page_size)

        debug_print(
            f"[ModelScope] raw_models={len(models_data)} normalized={len(normalized_items)} "
            f"discarded_type={discarded_type} discarded_base={discarded_base} "
            f"discarded_no_files={discarded_no_files} "
            f"current_page={normalized_page} total_pages={total_pages}"
        )

        return paginated_result(
            normalized_items,
            current_page=normalized_page,
            page_size=normalized_page_size,
            total_items=total_items,
            total_pages=total_pages,
            source=self.name,
        )

    def get_model(self, source_id: str, **kwargs: Any) -> Optional[dict]:
        """Fetch a single ModelScope repo by id (owner/repo)."""
        repo_id = source_id.strip().strip("/")
        url = f"{self.API_URL}/models/{quote(repo_id, safe='/')}"
        data = self._request_json(url)
        if isinstance(data, str) or not isinstance(data, dict):
            return None
        return self._normalize_repo_detail(repo_id, data.get("Data", data))

    # ------------------------------------------------------------------
    # Download helpers
    # ------------------------------------------------------------------
    def get_download_url(self, file_info: dict, **kwargs: Any) -> Optional[str]:
        """Return a direct ModelScope resolve URL for a canonical file dict."""
        if not isinstance(file_info, dict):
            return None
        raw = file_info.get("browserSourceFileRaw") or {}
        repo_id = raw.get("repo_id")
        path = raw.get("path") or file_info.get("name")
        revision = raw.get("revision") or "master"
        if repo_id and path:
            return f"{self.BASE_URL}/models/{quote(repo_id, safe='/')}/resolve/{quote(revision, safe='/')}/{quote(path, safe='/')}"
        return file_info.get("downloadUrl") or file_info.get("download_url")

    # ------------------------------------------------------------------
    # Normalization
    # ------------------------------------------------------------------
    def _normalize_search_item(self, item: dict) -> Optional[dict]:
        """Build a canonical model from a ModelScope search result item."""
        repo_id = self._repo_id_from_item(item)
        if not repo_id:
            return None

        tags = self._extract_tags(item)
        name = item.get("Name") or repo_id.split("/")[-1]
        muse = item.get("MuseInfo") or {}
        model_type = self._detect_content_type(tags, repo_id, item.get("Libraries", []), muse)
        base_model = self._detect_base_model(tags, repo_id, name, item.get("BaseModel"), muse)
        nsfw = any("nsfw" in t.lower() for t in tags) or "nsfw" in repo_id.lower()

        versions = self._build_versions_from_muse(repo_id, muse, model_type, base_model)
        if not versions:
            versions = self._build_versions_from_model_infos(repo_id, item.get("ModelInfos"), model_type, base_model)
        if not versions:
            versions = self._build_fallback_version(repo_id, model_type, base_model)

        return canonical_model(
            source=self.name,
            source_id=repo_id,
            name=name,
            model_type=model_type,
            source_url=f"{self.BASE_URL}/models/{quote(repo_id, safe='/')}",
            description=item.get("Description") or "",
            creator={"username": item.get("Path", "").split("/")[-1] or repo_id.split("/")[0]},
            tags=tags,
            base_model=base_model,
            nsfw=nsfw,
            versions=versions,
            stats={
                "downloadCount": item.get("Downloads"),
                "starCount": item.get("Stars"),
            },
            raw=item,
        )

    def _normalize_repo_detail(self, repo_id: str, data: dict) -> Optional[dict]:
        """Build a canonical model from a full ModelScope repo detail response."""
        tags = self._extract_tags(data)
        name = data.get("Name") or repo_id.split("/")[-1]
        muse = data.get("MuseInfo") or {}
        model_type = self._detect_content_type(tags, repo_id, data.get("Libraries", []), muse)
        base_model = self._detect_base_model(tags, repo_id, name, data.get("BaseModel"), muse)
        nsfw = any("nsfw" in t.lower() for t in tags) or "nsfw" in repo_id.lower()

        versions = self._build_versions_from_muse(repo_id, muse, model_type, base_model)
        if not versions:
            versions = self._build_versions_from_model_infos(repo_id, data.get("ModelInfos"), model_type, base_model)
        if not versions:
            versions = self._build_fallback_version(repo_id, model_type, base_model)

        return canonical_model(
            source=self.name,
            source_id=repo_id,
            name=name,
            model_type=model_type,
            source_url=f"{self.BASE_URL}/models/{quote(repo_id, safe='/')}",
            description=data.get("Description") or "",
            creator={"username": data.get("Path", "").split("/")[-1] or repo_id.split("/")[0]},
            tags=tags,
            base_model=base_model,
            nsfw=nsfw,
            versions=versions,
            stats={
                "downloadCount": data.get("Downloads"),
                "starCount": data.get("Stars"),
            },
            raw=data,
        )

    def _build_versions_from_muse(
        self,
        repo_id: str,
        muse: dict,
        model_type: str,
        base_model: Optional[str],
    ) -> list[dict]:
        """Build canonical versions from ModelScope MuseInfo payload."""
        if not isinstance(muse, dict):
            return []

        muse_model = muse.get("model") or {}
        versions = muse.get("versions") or []
        if not versions:
            return []

        result: list[dict] = []
        version_type = self._muse_content_type(muse_model.get("modelType")) or model_type
        version_base = self._muse_base_model(muse_model.get("stableDiffusionVersion")) or base_model

        for v in versions:
            if not isinstance(v, dict):
                continue
            mv = v.get("modelVersion") or {}
            stats = v.get("stats") or {}
            file_list = stats.get("fileList") or []
            file_sizes = stats.get("fileSizes") or []

            files: list[dict] = []
            for idx, filename in enumerate(file_list):
                if not isinstance(filename, str):
                    continue
                size = file_sizes[idx] if idx < len(file_sizes) else None
                size_bytes = self._parse_size(size)
                files.append(canonical_file(
                    filename=filename.split("/")[-1],
                    size_kb=size_bytes / 1024 if size_bytes else None,
                    size_bytes=size_bytes,
                    download_url=f"{self.BASE_URL}/models/{quote(repo_id, safe='/')}/resolve/master/{quote(filename, safe='/')}",
                    primary=idx == 0,
                    raw={"repo_id": repo_id, "path": filename, "revision": "master"},
                ))

            if not files:
                continue

            # Prefer .safetensors as primary.
            files.sort(key=lambda f: self._file_sort_key(
                (f.get("browserSourceFileRaw") or {}).get("path") or f.get("name", ""),
                version_type,
            ))
            for i, f in enumerate(files):
                f["primary"] = i == 0

            cover_images = v.get("coverImages") or []
            images = [
                canonical_image(url=img.get("url"), raw=img)
                for img in cover_images
                if isinstance(img, dict) and img.get("url")
            ]

            trigger_words = mv.get("triggerWords") or []
            if isinstance(trigger_words, str):
                trigger_words = [t.strip() for t in re.split(r"[,;\n]+", trigger_words) if t.strip()]

            result.append(canonical_version(
                source_version_id=str(mv.get("id") or mv.get("versionName") or "1"),
                name=mv.get("versionName") or mv.get("showName") or "v1",
                base_model=version_base,
                description=mv.get("description") or "",
                trained_words=trigger_words if isinstance(trigger_words, list) else [],
                files=files,
                images=images[:9],
                download_url=f"{self.BASE_URL}/models/{quote(repo_id, safe='/')}",
                stats={"downloadCount": mv.get("downloadCount")},
                raw=v,
            ))

        return result

    def _build_versions_from_model_infos(
        self,
        repo_id: str,
        model_infos: Any,
        model_type: str,
        base_model: Optional[str],
    ) -> list[dict]:
        """Build a canonical version from ModelInfos.safetensor.files when available."""
        if not isinstance(model_infos, dict):
            return []
        safetensor = model_infos.get("safetensor") or model_infos.get("safetensors") or {}
        if not isinstance(safetensor, dict):
            return []
        raw_files = safetensor.get("files")
        if not isinstance(raw_files, list) or not raw_files:
            return []

        files: list[dict] = []
        for entry in raw_files:
            if not isinstance(entry, dict):
                continue
            path = entry.get("name") or entry.get("path") or ""
            if not path:
                continue
            # ModelInfos.safetensor.files sizes are always bytes.
            size_bytes = self._parse_size(entry.get("size"), assume_bytes=True)
            files.append(canonical_file(
                filename=path.split("/")[-1],
                size_kb=size_bytes / 1024 if size_bytes else None,
                size_bytes=size_bytes,
                sha256=entry.get("sha256"),
                download_url=f"{self.BASE_URL}/models/{quote(repo_id, safe='/')}/resolve/master/{quote(path, safe='/')}",
                primary=False,
                raw={"repo_id": repo_id, "path": path, "revision": "master"},
            ))

        if not files:
            return []

        files.sort(key=lambda f: self._file_sort_key(
            (f.get("browserSourceFileRaw") or {}).get("path") or f.get("name", ""),
            model_type,
        ))
        for i, f in enumerate(files):
            f["primary"] = i == 0

        return [canonical_version(
            source_version_id="master",
            name="master",
            base_model=base_model,
            files=files,
            download_url=f"{self.BASE_URL}/models/{quote(repo_id, safe='/')}",
            raw=model_infos,
        )]

    def _build_fallback_version(
        self,
        repo_id: str,
        model_type: str,
        base_model: Optional[str],
    ) -> list[dict]:
        """Create a minimal version so the card can still render."""
        return [canonical_version(
            source_version_id="master",
            name="master",
            base_model=base_model,
            files=[canonical_file(
                filename="model.safetensors",
                download_url=f"{self.BASE_URL}/models/{quote(repo_id, safe='/')}",
                primary=True,
                raw={"repo_id": repo_id, "path": "model.safetensors", "revision": "master"},
            )],
            download_url=f"{self.BASE_URL}/models/{quote(repo_id, safe='/')}",
        )]

    # ------------------------------------------------------------------
    # Detection helpers
    # ------------------------------------------------------------------
    def _repo_id_from_item(self, item: dict) -> Optional[str]:
        """Return owner/repo from a ModelScope item."""
        path = item.get("Path")
        name = item.get("Name")
        if path and name:
            return f"{path.strip('/')}/{name}"
        # BackendSupport sometimes exposes the HF-style model_id.
        backend = item.get("BackendSupport") or {}
        model_id = backend.get("model_id")
        if model_id and "/" in str(model_id):
            return str(model_id)
        return None

    def _extract_tags(self, item: dict) -> list[str]:
        """Return a flat list of tag strings from a ModelScope item."""
        tags: list[str] = []
        for tag in item.get("Tags", []) or []:
            if isinstance(tag, str) and tag:
                tags.append(tag)
        for lib in item.get("Libraries", []) or []:
            if isinstance(lib, str) and lib:
                tags.append(lib)
        # MuseInfo tags are sometimes present.
        muse = item.get("MuseInfo") or {}
        if isinstance(muse, dict):
            for tag in muse.get("tags") or []:
                if isinstance(tag, str) and tag:
                    tags.append(tag)
            muse_model = muse.get("model") or {}
            for tag in muse_model.get("tags") or []:
                if isinstance(tag, str) and tag:
                    tags.append(tag)
        return tags

    def _detect_content_type(
        self,
        tags: list[str],
        repo_id: str,
        libraries: list[str],
        muse: Optional[dict],
    ) -> str:
        """Infer extension content type from ModelScope metadata."""
        if isinstance(muse, dict):
            muse_model = muse.get("model") or {}
            muse_type = self._muse_content_type(muse_model.get("modelType"))
            if muse_type:
                return muse_type

        lower_tags = [t.lower() for t in tags]
        lower_libs = [str(l).lower() for l in libraries if l]
        combined = " ".join(lower_tags + lower_libs) + " " + repo_id.lower()

        for hint, ctype in self.CONTENT_TYPE_HINTS.items():
            if hint in lower_tags or hint in lower_libs or hint in repo_id.lower():
                return ctype

        for hint, ctype in self.FILENAME_TYPE_HINTS.items():
            if hint in combined:
                return ctype

        return "Other"

    def _detect_base_model(
        self,
        tags: list[str],
        repo_id: str,
        name: str,
        base_model_field: Any,
        muse: Optional[dict],
    ) -> Optional[str]:
        """Infer extension base model family from ModelScope metadata."""
        if isinstance(muse, dict):
            muse_model = muse.get("model") or {}
            muse_base = self._muse_base_model(muse_model.get("stableDiffusionVersion"))
            if muse_base:
                return muse_base
            muse_base = self._muse_base_model(muse.get("stableDiffusionVersion"))
            if muse_base:
                return muse_base

        if isinstance(base_model_field, list):
            text = " ".join(str(b) for b in base_model_field if b)
        elif isinstance(base_model_field, str):
            text = base_model_field
        else:
            text = ""
        text += " " + " ".join(tags).lower() + " " + repo_id.lower() + " " + name.lower()

        for hint, base in self.BASE_MODEL_HINTS.items():
            if self._matches_base_model_hint(hint, text):
                return base
        return None

    @staticmethod
    def _muse_content_type(raw_type: Any) -> Optional[str]:
        """Map a MuseInfo modelType value to extension content type."""
        if not raw_type:
            return None
        key = str(raw_type).strip().lower().replace(" ", "_").replace("-", "_")
        return ModelScopeSource.MUSE_CONTENT_TYPE_MAP.get(key)

    @staticmethod
    def _muse_base_model(raw_version: Any) -> Optional[str]:
        """Map a MuseInfo stableDiffusionVersion value to extension base model."""
        if not raw_version:
            return None
        key = str(raw_version).strip().upper().replace(" ", "_").replace("-", "_").replace(".", "_")
        return ModelScopeSource.MUSE_BASE_MODEL_MAP.get(key)

    @staticmethod
    def _matches_base_model_hint(hint: str, text: str) -> bool:
        """Return True when a base-model hint matches without broad false positives."""
        hint = str(hint or "").lower()
        text = str(text or "").lower()
        if not hint or not text:
            return False

        if hint == "anima":
            return bool(re.search(r"(?<![a-z0-9])anima(?!t(?:e|ed|es|ing|ion)|diff)", text))

        if " " in hint or "/" in hint or "." in hint or "-" in hint:
            return hint in text

        return bool(re.search(rf"(?<![a-z0-9]){re.escape(hint)}(?![a-z0-9])", text))

    def _resolve_content_type_filter(self, content_type: Optional[str | list[str]]) -> list[str]:
        """Return canonical model type names requested by the Browser."""
        if not content_type:
            return []
        values = content_type if isinstance(content_type, list) else [content_type]
        resolved: list[str] = []
        for value in values:
            key = str(value).strip().lower().replace(" ", "")
            if key in {"all", "none"}:
                continue
            if key == "checkpoint":
                resolved.append("checkpoint")
            elif key == "lora":
                resolved.append("lora")
            elif key in {"locon", "lycoris"}:
                resolved.append("locon")
            elif key == "dora":
                resolved.append("dora")
            elif key in {"textualinversion", "textual-inversion", "embedding"}:
                resolved.append("textualinversion")
            elif key == "vae":
                resolved.append("vae")
            elif key == "upscaler":
                resolved.append("upscaler")
            elif key == "controlnet":
                resolved.append("controlnet")
            elif key == "motionmodule":
                resolved.append("motionmodule")
        return resolved

    def _resolve_base_model_filter(
        self,
        base_filter: Optional[str | list[str]],
        query: str = "",
    ) -> list[str]:
        """Resolve UI base-model filters and exact base-model query terms."""
        resolved: list[str] = []
        raw_filters = base_filter if isinstance(base_filter, list) else [base_filter] if base_filter else []
        for value in raw_filters:
            if not value:
                continue
            normalized = self._normalize_base_model_value(str(value))
            if normalized and normalized not in resolved:
                resolved.append(normalized)

        query_base = self._normalize_base_model_value(query, exact=True)
        if query_base and query_base not in resolved:
            resolved.append(query_base)
        return resolved

    def _normalize_base_model_value(self, value: str, *, exact: bool = False) -> Optional[str]:
        """Normalize a possible base-model label to the extension's naming."""
        lower = str(value or "").strip().lower()
        if not lower:
            return None
        if exact:
            candidates = {
                hint: base
                for hint, base in self.BASE_MODEL_HINTS.items()
                if " " not in hint and "/" not in hint
            }
            if lower in candidates:
                return candidates[lower]
            return None
        for hint, base in self.BASE_MODEL_HINTS.items():
            if self._matches_base_model_hint(hint, lower):
                return base
        return value.strip()

    @staticmethod
    def _matches_content_type_filter(model: dict, target_content_types: list[str]) -> bool:
        """Return True when a normalized model matches requested content types."""
        if not target_content_types:
            return True
        model_type = str(model.get("type") or "").strip().lower()
        groups = {
            "checkpoint": {"checkpoint"},
            "lora": {"lora"},
            "locon": {"locon"},
            "dora": {"dora"},
            "textualinversion": {"textualinversion"},
            "vae": {"vae"},
            "upscaler": {"upscaler"},
            "controlnet": {"controlnet"},
            "motionmodule": {"motionmodule"},
        }
        accepted: set[str] = set()
        for target in target_content_types:
            accepted.update(groups.get(target, {target}))
        return model_type in accepted

    @staticmethod
    def _matches_base_model_filter(model: dict, target_base_models: list[str]) -> bool:
        """Return True when a normalized model matches requested base filters."""
        if not target_base_models:
            return True
        base_model = str(model.get("baseModel") or "").strip().lower()
        if not base_model:
            return False
        return any(base_model == str(target).strip().lower() for target in target_base_models)

    @staticmethod
    def _parse_size(value: Any, *, assume_bytes: bool = False) -> Optional[int]:
        """Normalize a size value to bytes.

        ModelInfos.safetensor.files expose sizes in bytes. MuseInfo stats
        historically use bytes, but some early payloads reported KB for very
        small files. When ``assume_bytes`` is False we keep tiny values as-is
        and treat anything over 1 MB as already in bytes.
        """
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            if value <= 0:
                return None
            if assume_bytes:
                return int(value)
            # Heuristic: values smaller than 1 KB are kept as bytes; values
            # larger than 1 MB are already bytes; everything in between is KB.
            if value < 1024:
                return int(value)
            if value >= 1024 * 1024:
                return int(value)
            return int(value * 1024)
        return None

    def _file_sort_key(self, path: str, model_type: str = "Other") -> tuple[int, int, str]:
        """Sort ModelScope files so downloadable artifacts appear before components."""
        lower = str(path or "").lower()
        extension_rank = (
            0 if lower.endswith(".safetensors") else
            1 if lower.endswith(".ckpt") else
            2 if lower.endswith((".pt", ".pth")) else
            3 if lower.endswith(".bin") else
            4 if lower.endswith(".onnx") else
            5
        )

        segments = [segment for segment in lower.split("/") if segment]
        component_segments = {
            "feature_extractor",
            "safety_checker",
            "scheduler",
            "text_encoder",
            "text_encoder_2",
            "text_encoder_3",
            "tokenizer",
            "tokenizer_2",
            "tokenizer_3",
            "vae",
            "vae_1_0",
            "vae_decoder",
            "vae_encoder",
        }
        if str(model_type).lower() != "vae" and any(segment in component_segments for segment in segments[:-1]):
            location_rank = 30
        elif "/" not in lower:
            location_rank = 0
        elif any(segment in {"diffusion_models", "unet", "transformer", "comfyui_checkpoints"} for segment in segments[:-1]):
            location_rank = 10
        else:
            location_rank = 20

        return (location_rank, extension_rank, lower)

    # ------------------------------------------------------------------
    # Request helpers
    # ------------------------------------------------------------------
    def _request_json(
        self,
        url: str,
        method: str = "GET",
        json: Optional[dict] = None,
    ) -> Any:
        """Make a request and return JSON or an error string."""
        headers = _api.get_headers()
        headers.setdefault("Accept", "application/json")
        if method == "PUT":
            headers.setdefault("Content-Type", "application/json")
        proxies, verify = _api.get_proxies()
        try:
            if method == "PUT":
                response = requests.put(url, json=json, headers=headers, proxies=proxies, verify=verify, timeout=(60, 30))
            else:
                response = requests.get(url, headers=headers, proxies=proxies, verify=verify, timeout=(60, 30))
        except requests.exceptions.RequestException as exc:
            debug_print(f"[ModelScope] request failed: {exc}")
            return "offline"

        if response.status_code == 404:
            return "not_found"
        if response.status_code == 503:
            return "offline"
        if response.status_code == 429:
            return "error"
        if response.status_code != 200:
            debug_print(f"[ModelScope] unexpected status {response.status_code} for {url}")
            return "error"

        try:
            return response.json()
        except Exception as exc:
            debug_print(f"[ModelScope] JSON decode failed: {exc}")
            return "error"


# Register on import.
register_source(ModelScopeSource())
