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
        "image-to-video": "Checkpoint",
        "video-to-video": "Checkpoint",
        "text-to-image-generation": "Checkpoint",
    }

    def __init__(self) -> None:
        super().__init__("huggingface", "Hugging Face", visible_in_dropdown=False)

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
        clean_query = (query or "").strip()
        normalized_page = max(1, int(page or 1))
        normalized_page_size = max(1, int(page_size or 20))
        target_base_models = self._resolve_base_model_filter(base_filter, clean_query)
        # HF model search is cursor-based and doesn't expose offset. Fetch enough
        # rows to slice the requested page client-side, capped to keep runtime sane.
        fetch_limit = min(max(normalized_page * normalized_page_size, normalized_page_size), 100)
        if target_base_models:
            fetch_limit = min(max(fetch_limit * 4, 50), 100)
        target_content_types = self._resolve_content_type_filter(content_type)
        hf_filters = self._resolve_hf_filters(content_type, target_base_models)
        base_params: dict[str, Any] = {
            "limit": fetch_limit,
            "full": "true",
            "sort": "downloads",
            "direction": "-1",
        }
        if clean_query:
            base_params["search"] = clean_query

        debug_print(
            f"[HuggingFace] search query='{clean_query or '<browse>'}' "
            f"page={normalized_page} page_size={normalized_page_size} "
            f"fetch_limit={fetch_limit} filters={hf_filters or ['<none>']} "
            f"base_filter={target_base_models or '<none>'}"
        )

        raw_repos_by_id: dict[str, dict] = {}
        raw_repo_count = 0
        query_filters = hf_filters or [None]
        for hf_filter in query_filters:
            params = dict(base_params)
            if hf_filter:
                params["filter"] = hf_filter

            url = f"{self.API_URL}?{self._encode_params(params)}"
            data = self._request_json(url)
            if isinstance(data, str):
                debug_print(f"[HuggingFace] search returned error string: {data}")
                return data
            if not isinstance(data, list):
                debug_print(f"[HuggingFace] unexpected search response type: {type(data)}")
                return paginated_result(
                    [],
                    current_page=normalized_page,
                    page_size=normalized_page_size,
                    source=self.name,
                )
            raw_repo_count += len(data)
            for repo in data:
                if not isinstance(repo, dict):
                    continue
                repo_id = repo.get("id") or repo.get("modelId")
                if repo_id and repo_id not in raw_repos_by_id:
                    raw_repos_by_id[str(repo_id)] = repo

        data = list(raw_repos_by_id.values())

        # Build canonical models from repo summaries.
        models: list[dict] = []
        discarded_no_files = 0
        discarded_base_filter = 0
        discarded_type_filter = 0
        for repo in data:
            if not isinstance(repo, dict):
                continue
            model = self._normalize_repo_summary(repo)
            versions = model.get("modelVersions", []) if model else []
            files = versions[0].get("files", []) if versions else []
            if model and files and not self._matches_content_type_filter(model, target_content_types):
                discarded_type_filter += 1
            elif model and files and not self._matches_base_model_filter(model, target_base_models):
                discarded_base_filter += 1
            elif model and files:
                models.append(model)
            elif model:
                discarded_no_files += 1

        # Apply simple client-side pagination (HF search is cursor-based).
        total_items = len(models)
        has_more = len(data) >= fetch_limit and fetch_limit < 100
        total_pages = max(1, (total_items + normalized_page_size - 1) // normalized_page_size)
        if has_more:
            total_pages = max(total_pages, normalized_page + 1)
        start = (normalized_page - 1) * normalized_page_size
        page_models = models[start:start + normalized_page_size]

        debug_print(
            f"[HuggingFace] raw_repos={raw_repo_count} unique_repos={len(data)} "
            f"normalized_models={len(models)} "
            f"discarded_no_files={discarded_no_files} "
            f"discarded_type_filter={discarded_type_filter} "
            f"discarded_base_filter={discarded_base_filter} "
            f"page_items={len(page_models)} current_page={normalized_page} total_pages={total_pages}"
        )

        return paginated_result(
            page_models,
            current_page=normalized_page,
            page_size=normalized_page_size,
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
    def _normalize_repo_summary(self, repo: dict, *, enrich_readme: bool = False) -> Optional[dict]:
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
        files = self._siblings_to_files(repo_id, siblings, model_type)

        # Try to enrich from README.md when no base model or triggers were detected.
        readme = ""
        if enrich_readme and not base_model:
            readme = self._fetch_readme(repo_id)
            base_model = self._extract_base_model_from_readme(readme)
        trained_words = self._extract_trigger_words_from_readme(readme) if enrich_readme else []

        version = canonical_version(
            source_version_id="main",
            name="main",
            base_model=base_model,
            description=repo.get("description") or "",
            trained_words=trained_words,
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

        files = self._fetch_repo_files(repo_id, model_type)
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

        # Try to enrich from README.md when no base model or triggers were detected.
        readme = ""
        if not base_model:
            readme = self._fetch_readme(repo_id)
            base_model = self._extract_base_model_from_readme(readme)
        trained_words = self._extract_trigger_words_from_readme(readme)

        version = canonical_version(
            source_version_id="main",
            name="main",
            base_model=base_model,
            description=data.get("description") or "",
            trained_words=trained_words,
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

    def _fetch_repo_files(self, repo_id: str, model_type: str = "Other") -> list[dict]:
        """List downloadable model files in the repo's main branch."""
        url = f"{self.API_URL}/{quote(repo_id, safe='/')}/tree/main"
        data = self._request_json(url)
        if not isinstance(data, list):
            return []

        result: list[dict] = []
        model_extensions = self._model_file_extensions(model_type)
        for entry in data:
            if not isinstance(entry, dict):
                continue
            path = entry.get("path", "")
            lower_path = path.lower()
            if not any(lower_path.endswith(ext) for ext in model_extensions):
                continue
            if self._is_auxiliary_component_path(path, model_type):
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
        result.sort(key=lambda f: self._file_sort_key(
            (f.get("browserSourceFileRaw") or {}).get("path") or f.get("name", ""),
            model_type,
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
    def _siblings_to_files(self, repo_id: str, siblings: list[dict], model_type: str = "Other") -> list[dict]:
        """Convert HF sibling entries into canonical file dicts."""
        result: list[dict] = []
        model_extensions = self._model_file_extensions(model_type)
        for s in siblings:
            if not isinstance(s, dict):
                continue
            path = s.get("rfilename", "")
            lower = path.lower()
            if not any(lower.endswith(ext) for ext in model_extensions):
                continue
            if self._is_auxiliary_component_path(path, model_type):
                continue
            result.append(canonical_file(
                filename=path.split("/")[-1],
                download_url=f"{self.BASE_URL}/{quote(repo_id, safe='/')}/resolve/main/{quote(path, safe='/')}",
                primary=False,
                raw={"repo_id": repo_id, "path": path},
            ))
        result.sort(key=lambda f: self._file_sort_key(
            (f.get("browserSourceFileRaw") or {}).get("path") or f.get("name", ""),
            model_type,
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
                    if self._matches_base_model_hint(hint, base_value):
                        return base
                # Return the raw base_model value if no known mapping.
                return base_value

        text = " ".join(tags).lower() + " " + repo_id.lower() + " " + model_id.lower()
        for hint, base in self.BASE_MODEL_HINTS.items():
            if self._matches_base_model_hint(hint, text):
                return base
        return None

    @staticmethod
    def _matches_base_model_hint(hint: str, text: str) -> bool:
        """Return True when a base-model hint matches without broad false positives."""
        hint = str(hint or "").lower()
        text = str(text or "").lower()
        if not hint or not text:
            return False

        if hint == "anima":
            # "anima" should match Anima/Animagine/KiwimixAnima-style repos,
            # but not generic animation terms like animate/animatediff.
            return bool(re.search(r"(?<![a-z0-9])anima(?!t(?:e|ed|es|ing|ion)|diff)", text))

        if " " in hint or "/" in hint or "." in hint or "-" in hint:
            return hint in text

        return bool(re.search(rf"(?<![a-z0-9]){re.escape(hint)}(?![a-z0-9])", text))

    def _resolve_hf_filters(
        self,
        content_type: Optional[str | list[str]],
        target_base_models: list[str],
    ) -> list[str]:
        """Map extension filters to Hugging Face pipeline/tag filters."""
        types = self._content_type_values(content_type)
        video_search = self._is_video_base_model_search(target_base_models)

        if any(t in {"lora", "locon", "dora"} for t in types):
            return ["lora"]
        if "textualinversion" in types:
            return ["textual-inversion"]
        if "vae" in types:
            return ["vae"]
        if "upscaler" in types:
            return ["upscaler"]

        # Forge Neo supports video model families such as Wan, HunyuanVideo,
        # Stable Video Diffusion and LTX. HF classifies those by pipeline tags,
        # not by the broad "stable-diffusion" tag.
        if video_search:
            return ["text-to-video", "image-to-video"]

        # Default checkpoint/common-model search should prefer actual image
        # generation pipelines. The old "stable-diffusion" tag was too broad
        # and pulled unrelated repos into semantic searches like "anima".
        if not types or "checkpoint" in types:
            return ["text-to-image"]

        return []

    @staticmethod
    def _content_type_values(content_type: Optional[str | list[str]]) -> list[str]:
        """Normalize Browser content type selections for matching."""
        if not content_type:
            return []
        values = content_type if isinstance(content_type, list) else [content_type]
        return [
            str(value).strip().lower().replace(" ", "")
            for value in values
            if value and str(value).strip().lower() not in {"all", "none"}
        ]

    def _resolve_content_type_filter(self, content_type: Optional[str | list[str]]) -> list[str]:
        """Return canonical model type names requested by the Browser."""
        resolved: list[str] = []
        for value in self._content_type_values(content_type):
            if value == "checkpoint":
                resolved.append("checkpoint")
            elif value == "lora":
                resolved.append("lora")
            elif value == "locon":
                resolved.append("locon")
            elif value == "dora":
                resolved.append("dora")
            elif value == "textualinversion":
                resolved.append("textualinversion")
            elif value == "vae":
                resolved.append("vae")
            elif value == "upscaler":
                resolved.append("upscaler")
            elif value == "controlnet":
                resolved.append("controlnet")
        return resolved

    @staticmethod
    def _is_video_base_model_search(target_base_models: list[str]) -> bool:
        """Return True for Forge Neo video-capable model families."""
        video_base_models = {
            "wan",
            "hunyuanvideo",
            "stable video diffusion",
            "ltx",
        }
        return any(str(base).strip().lower() in video_base_models for base in target_base_models)

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

        # HF's text search is broad. When the whole query is exactly a known
        # base-model family (e.g. "anima", "wan", "flux"), use it as an
        # additional semantic filter instead of showing unrelated text matches.
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
    def _matches_base_model_filter(model: dict, target_base_models: list[str]) -> bool:
        """Return True when a normalized HF model matches requested base filters."""
        if not target_base_models:
            return True
        base_model = str(model.get("baseModel") or "").strip().lower()
        if not base_model:
            return False
        return any(base_model == str(target).strip().lower() for target in target_base_models)

    @staticmethod
    def _matches_content_type_filter(model: dict, target_content_types: list[str]) -> bool:
        """Return True when a normalized HF model matches requested content types."""
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
        }
        accepted: set[str] = set()
        for target in target_content_types:
            accepted.update(groups.get(target, {target}))
        return model_type in accepted

    def _model_file_extensions(self, model_type: str) -> tuple[str, ...]:
        """Return allowed file extensions for a given content type.

        Checkpoint and LoRA downloads are restricted to Safetensors for safety.
        Other types keep their original extension set.
        """
        if str(model_type).lower() in ("checkpoint", "lora", "locon", "dora"):
            return (".safetensors",)
        return (".safetensors", ".ckpt", ".pt", ".pth", ".bin", ".onnx")

    def _file_sort_key(self, path: str, model_type: str = "Other") -> tuple[int, int, str]:
        """Sort HF files so downloadable model artifacts appear before components.

        Diffusers repos often contain many ``model.safetensors`` files under
        ``text_encoder/``, ``vae/`` or ``safety_checker/``. For Forge-style
        downloads, root-level checkpoints or diffusion model folders are better
        primary candidates than those auxiliary components.
        """
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

    @staticmethod
    def _is_auxiliary_component_path(path: str, model_type: str = "Other") -> bool:
        """Return True for component files that should not be primary checkpoints."""
        if str(model_type).lower() != "checkpoint":
            return False

        lower = str(path or "").lower()
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
        if any(segment in component_segments for segment in segments[:-1]):
            return True

        filename = segments[-1] if segments else lower
        auxiliary_filename_tokens = (
            "clip_vision",
            "clip-g",
            "clip_l",
            "clip_g",
            "text_encoder",
            "t5xxl",
            "umt5",
            "vae",
            "lora",
        )
        return any(token in filename for token in auxiliary_filename_tokens)

    def _fetch_readme(self, repo_id: str) -> str:
        """Fetch README.md raw text from a HF repo, if it exists."""
        url = f"{self.BASE_URL}/{quote(repo_id, safe='/')}/resolve/main/README.md"
        headers = _api.get_headers()
        proxies, verify = _api.get_proxies()
        try:
            response = requests.get(url, headers=headers, proxies=proxies, verify=verify, timeout=(30, 15))
        except requests.exceptions.RequestException:
            return ""
        if response.status_code != 200:
            return ""
        try:
            return response.text
        except Exception:
            return ""

    def _extract_base_model_from_readme(self, readme: str) -> Optional[str]:
        """Try to extract the base model from README.md contents."""
        if not readme:
            return None
        lines = readme.splitlines()
        # Look for explicit base model declarations.
        for line in lines:
            lower = line.lower()
            if any(k in lower for k in ("base model", "base_model", "basemodel", "base: ", "model base")):
                for hint, base in self.BASE_MODEL_HINTS.items():
                    if self._matches_base_model_hint(hint, lower):
                        return base
                # If no known mapping, return the cleaned line value.
                cleaned = re.sub(r"^[^:：]+[:：]\s*", "", line).strip()
                if cleaned:
                    return cleaned
        return None

    def _extract_trigger_words_from_readme(self, readme: str) -> list[str]:
        """Try to extract trigger words from README.md contents."""
        if not readme:
            return []
        triggers: list[str] = []
        lines = readme.splitlines()
        in_trigger_section = False
        for line in lines:
            stripped = line.strip()
            lower = stripped.lower()
            if any(k in lower for k in ("trigger word", "trigger words", "trigger:", "triggers:", "activation text", "activation words")):
                in_trigger_section = True
                # If the trigger is on the same line after the label, capture it.
                value = re.sub(r"^[^:：]*[:：]\s*", "", stripped).strip()
                if value and value.lower() not in ("trigger word", "trigger words"):
                    triggers.extend(self._split_triggers(value))
                continue
            if in_trigger_section:
                if not stripped or stripped.startswith("#") or stripped.startswith("-") and not any(c.isalnum() for c in stripped):
                    in_trigger_section = False
                    continue
                triggers.extend(self._split_triggers(stripped))
        # Deduplicate while preserving order.
        seen: set[str] = set()
        result: list[str] = []
        for t in triggers:
            if t and t.lower() not in seen:
                seen.add(t.lower())
                result.append(t)
        return result

    @staticmethod
    def _split_triggers(text: str) -> list[str]:
        """Split a trigger string by common separators."""
        text = text.strip("\"'[]()")
        if "," in text:
            return [t.strip().strip("\"'") for t in text.split(",") if t.strip()]
        if ";" in text:
            return [t.strip().strip("\"'") for t in text.split(";") if t.strip()]
        return [text.strip().strip("\"'")]

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
