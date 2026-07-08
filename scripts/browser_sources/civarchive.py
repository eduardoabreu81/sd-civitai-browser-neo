"""CivArchive browser source adapter.

CivArchive (https://civarchive.com) is a metadata aggregator and mirror index
for models that were originally published on CivitAI (including deleted ones).
This adapter exposes its search-by-name, lookup-by-hash and model-detail
endpoints through the common :class:`BrowserSource` contract.

API surface used:
- ``GET /api/search?q=...&type=...&base_model=...&limit=...&offset=...``
- ``GET /api/models/{model_id}?modelVersionId={version_id}``
- ``GET /api/sha256/{sha256}``
"""

from __future__ import annotations

from typing import Any, Optional
from urllib.parse import urlencode

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


class CivArchiveSource(BrowserSource):
    """Browser source adapter for CivArchive (civarchive.com)."""

    BASE_URL = "https://civarchive.com/api"

    # CivArchive content types map 1:1 with CivitAI internal names.
    CONTENT_TYPE_MAP = {
        "Checkpoint": "Checkpoint",
        "LORA": "LORA",
        "LoCon": "LoCon",
        "DoRA": "DoRA",
        "TextualInversion": "TextualInversion",
        "VAE": "VAE",
        "Controlnet": "Controlnet",
        "Upscaler": "Upscaler",
        "MotionModule": "MotionModule",
        "AestheticGradient": "AestheticGradient",
        "Poses": "Poses",
        "Detection": "Detection",
        "Wildcards": "Wildcards",
        "Workflows": "Workflows",
        "Other": "Other",
    }

    def __init__(self) -> None:
        super().__init__("civarchive", "CivArchive")

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------
    def supports(self, content_type: Optional[str]) -> bool:
        """CivArchive indexes all content types CivitAI has."""
        return True

    def supported_search_types(self) -> list[str]:
        """CivArchive supports full-text search and SHA256 lookup."""
        return ["Model name", "SHA256"]

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
        """Search CivArchive and return results in canonical format."""
        if search_type == "SHA256" and query:
            return self._search_by_sha256(query)

        return self._search_by_name(
            query=query,
            content_type=content_type,
            base_filter=base_filter,
            page=page,
            page_size=page_size,
        )

    def get_model(self, source_id: str, **kwargs: Any) -> Optional[dict]:
        """Fetch a single CivArchive model by id."""
        version_id = kwargs.get("version_id")
        data = self._request_json(f"/models/{source_id}", params={"modelVersionId": version_id} if version_id else None)
        if not isinstance(data, dict):
            return None
        return self._normalize_model(data)

    def get_version_by_hash(self, sha256: str) -> Optional[dict]:
        """Look up a CivArchive model version by SHA256."""
        result = self._search_by_sha256(sha256)
        if isinstance(result, dict) and result.get("items"):
            return result["items"][0]
        return None

    # ------------------------------------------------------------------
    # Download helpers
    # ------------------------------------------------------------------
    def get_download_url(self, file_info: dict, **kwargs: Any) -> Optional[str]:
        """Return the best available download URL for a canonical file dict.

        Preference order:
        1. CivArchive ``downloadUrl`` field (usually a CivitAI redirect).
        2. First active CivArchive mirror that is not marked as deleted.
        3. Any mirror URL as a last resort.
        """
        if not isinstance(file_info, dict):
            return None

        raw = file_info.get("browserSourceFileRaw") or {}
        download_url = raw.get("downloadUrl") or file_info.get("downloadUrl")
        if download_url:
            return download_url

        mirrors = raw.get("mirrors") or []
        active = next(
            (m for m in mirrors if isinstance(m, dict) and m.get("deletedAt") is None and m.get("url")),
            None,
        )
        if active:
            return active.get("url")

        if mirrors and isinstance(mirrors[0], dict):
            return mirrors[0].get("url")

        return None

    def get_preview_url(self, image_info: dict, **kwargs: Any) -> Optional[str]:
        """Return CivArchive image URL."""
        if not isinstance(image_info, dict):
            return None
        return image_info.get("url")

    # ------------------------------------------------------------------
    # Internal request helpers
    # ------------------------------------------------------------------
    def _request_json(self, path: str, params: Optional[dict] = None) -> Optional[dict]:
        """Make a GET request to the CivArchive API and return JSON."""
        url = f"{self.BASE_URL}{path}"
        if params:
            query = urlencode({k: v for k, v in params.items() if v is not None}, doseq=True)
            url = f"{url}?{query}"

        headers = _api.get_headers()
        proxies, verify = _api.get_proxies()
        try:
            response = requests.get(url, headers=headers, proxies=proxies, verify=verify, timeout=(60, 30))
        except requests.exceptions.RequestException as exc:
            debug_print(f"[CivArchive] request failed: {exc}")
            return "offline"

        if response.status_code == 404:
            return "not_found"
        if response.status_code == 429:
            return "error"
        if response.status_code >= 500:
            return "offline"
        if response.status_code != 200:
            debug_print(f"[CivArchive] unexpected status {response.status_code} for {url}")
            return "error"

        try:
            return response.json()
        except Exception as exc:
            debug_print(f"[CivArchive] JSON decode failed: {exc}")
            return "error"

    # ------------------------------------------------------------------
    # Search implementations
    # ------------------------------------------------------------------
    def _search_by_name(
        self,
        *,
        query: str,
        content_type: Optional[str | list[str]],
        base_filter: Optional[str | list[str]],
        page: int,
        page_size: int,
    ) -> dict:
        """Search CivArchive by name and normalize to canonical models."""
        if not query or not query.strip():
            return paginated_result([], current_page=page, page_size=page_size, source=self.name)

        page = max(1, int(page or 1))
        page_size = max(1, int(page_size or 20))

        params: dict[str, Any] = {
            "q": query.strip(),
            "limit": page_size,
            "offset": (page - 1) * page_size,
        }

        # CivArchive accepts a single type and a single base_model.
        if content_type:
            types = content_type if isinstance(content_type, list) else [content_type]
            if types:
                params["type"] = types[0]
        if base_filter:
            bases = base_filter if isinstance(base_filter, list) else [base_filter]
            if bases:
                params["base_model"] = bases[0]

        data = self._request_json("/search", params=params)
        if isinstance(data, str):
            return data

        results = data.get("results", []) if isinstance(data, dict) else []
        debug_print(
            f"[CivArchive] search query={query.strip()!r} page={page} "
            f"raw_results={len(results)}"
        )
        if not results:
            return paginated_result(
                [],
                current_page=page,
                page_size=page_size,
                total_items=0,
                total_pages=1,
                source=self.name,
            )

        # Search returns mixed file/version rows; collect unique model IDs and
        # fetch full model details for each one.
        model_ids: list[str] = []
        seen_model_ids: set[str] = set()
        for item in results:
            if not isinstance(item, dict):
                continue
            model_id = item.get("model_id")
            normalized_id = str(model_id) if model_id is not None else None
            if normalized_id and normalized_id not in seen_model_ids:
                seen_model_ids.add(normalized_id)
                model_ids.append(normalized_id)

        # CivArchive currently returns a fixed search window and ignores
        # limit/offset. Paginate the stable unique model IDs client-side so
        # Next/Prev do not repeat the first result set.
        start = (page - 1) * page_size
        page_model_ids = model_ids[start:start + page_size]
        total_items = len(model_ids)
        total_pages = max(1, (total_items + page_size - 1) // page_size)
        debug_print(
            f"[CivArchive] unique_model_ids={total_items} "
            f"page_model_ids={len(page_model_ids)}"
        )

        models: list[dict] = []
        for model_id in page_model_ids:
            model_data = self._request_json(f"/models/{model_id}")
            if isinstance(model_data, dict):
                normalized = self._normalize_model(model_data)
                if normalized:
                    models.append(normalized)

        debug_print(f"[CivArchive] normalized_models={len(models)}")
        has_more = page < total_pages

        return paginated_result(
            models,
            current_page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            next_page=f"browser_source://{self.name}/page/{page + 1}" if has_more else None,
            prev_page=f"browser_source://{self.name}/page/{page - 1}" if page > 1 else None,
            source=self.name,
        )

    def _search_by_sha256(self, sha256_hash: str) -> dict:
        """Search CivArchive by SHA256 hash."""
        normalized_hash = _api.normalize_sha256(sha256_hash)
        if not normalized_hash:
            return "invalid_hash"

        data = self._request_json(f"/sha256/{normalized_hash.lower()}")
        if isinstance(data, str):
            return data

        model = self._normalize_model(data)
        if not model:
            return "sha256_not_found"

        return paginated_result(
            [model],
            current_page=1,
            page_size=1,
            total_items=1,
            total_pages=1,
            source=self.name,
        )

    # ------------------------------------------------------------------
    # Normalization
    # ------------------------------------------------------------------
    def _normalize_model(self, data: dict) -> Optional[dict]:
        """Convert a CivArchive model payload to canonical format."""
        if not isinstance(data, dict):
            return None

        model_id = data.get("id")
        if model_id is None:
            return None

        model_type = self.CONTENT_TYPE_MAP.get(data.get("type"), data.get("type", "Other"))
        creator = self._build_creator(data)
        versions = self._build_versions(data)
        if not versions:
            return None

        # Use the first/payload version as the display version; keep all
        # versions in modelVersions for the card/detail views.
        primary_version = versions[0]

        return canonical_model(
            source=self.name,
            source_id=str(model_id),
            name=data.get("name", "Unknown"),
            model_type=model_type,
            source_url=f"https://civarchive.com/models/{model_id}",
            description=data.get("description") or "",
            creator=creator,
            tags=data.get("tags") or [],
            base_model=primary_version.get("baseModel"),
            nsfw=bool(data.get("is_nsfw", False)),
            versions=versions,
            stats=self._build_stats(data),
            raw=data,
        )

    def _build_creator(self, data: dict) -> dict:
        """Build a CivitAI-compatible creator dict from CivArchive fields."""
        username = data.get("creator_username") or data.get("username") or ""
        creator: dict = {"username": username}
        if data.get("creator_name"):
            creator["name"] = data["creator_name"]
        if data.get("creator_url"):
            creator["url"] = data["creator_url"]
        if data.get("creator_image"):
            creator["image"] = data["creator_image"]
        return creator

    def _build_versions(self, data: dict) -> list[dict]:
        """Build canonical versions from the CivArchive payload.

        CivArchive returns the primary version under ``data["version"]`` and a
        compact list of all versions under ``data["versions"]``.  We resolve
        each version via ``/models/{id}?modelVersionId={vid}`` when needed so
        every canonical version carries full files/images.
        """
        primary = data.get("version")
        if not isinstance(primary, dict):
            primary = {}

        versions_meta = data.get("versions") or []
        if not isinstance(versions_meta, list):
            versions_meta = []

        # If no versions list, use the primary version alone.
        if not versions_meta and primary:
            normalized = self._normalize_version(primary, data)
            return [normalized] if normalized else []

        # Resolve each version to get full file/image data.  This matches the
        # behaviour of CivArchive's own UI and ensures consistent cards.
        result: list[dict] = []
        seen_ids: set[str] = set()
        model_id = str(data.get("id", ""))

        for meta in versions_meta:
            if not isinstance(meta, dict):
                continue
            version_id = meta.get("id")
            if version_id is None or str(version_id) in seen_ids:
                continue
            seen_ids.add(str(version_id))

            # The primary version is already expanded in the payload; avoid an
            # extra round-trip when the IDs match.
            if primary and str(primary.get("id")) == str(version_id):
                normalized = self._normalize_version(primary, data)
            else:
                version_data = self._request_json(
                    f"/models/{model_id}", params={"modelVersionId": version_id}
                )
                if not isinstance(version_data, dict):
                    continue
                normalized = self._normalize_version(
                    version_data.get("version", {}), version_data
                )

            if normalized:
                result.append(normalized)

        # Fallback: if versions meta failed, return primary.
        if not result and primary:
            normalized = self._normalize_version(primary, data)
            if normalized:
                result.append(normalized)

        return result

    def _normalize_version(self, version: dict, context: dict) -> Optional[dict]:
        """Convert a CivArchive version dict to canonical format."""
        if not isinstance(version, dict):
            return None

        version_id = version.get("id")
        if version_id is None:
            return None

        files = self._normalize_files(version.get("files") or [])
        if not files:
            return None

        images = self._normalize_images(version.get("images") or [])

        trained_words = version.get("trigger") or version.get("trainedWords") or []
        if isinstance(trained_words, str):
            trained_words = [trained_words]

        return canonical_version(
            source_version_id=str(version_id),
            name=version.get("name", "Unknown"),
            base_model=version.get("baseModel"),
            created_at=version.get("createdAt"),
            updated_at=version.get("updatedAt"),
            description=version.get("description") or "",
            trained_words=trained_words,
            activation_tags=[],
            files=files,
            images=images,
            download_url=files[0].get("downloadUrl") if files else None,
            stats=self._build_stats(version),
            raw=version,
        )

    def _normalize_files(self, files: list) -> list[dict]:
        """Convert CivArchive file entries to canonical files."""
        result: list[dict] = []
        for f in files:
            if not isinstance(f, dict):
                continue
            name = f.get("name")
            if not name and isinstance(f.get("mirrors"), list) and f["mirrors"]:
                name = f["mirrors"][0].get("filename")
            if not name:
                continue

            sha256 = f.get("sha256")
            hashes = {"SHA256": str(sha256).upper()} if sha256 else {}

            # Pick the best active mirror as the canonical download URL.
            mirrors = f.get("mirrors") or []
            active_mirror = next(
                (m for m in mirrors if isinstance(m, dict) and m.get("deletedAt") is None and m.get("url")),
                None,
            )
            download_url = f.get("downloadUrl") or (active_mirror.get("url") if active_mirror else None)

            # Infer format from filename extension for parity with CivitAI.
            metadata = dict(f.get("metadata") or {})
            lower_name = name.lower()
            if lower_name.endswith(".safetensors"):
                metadata.setdefault("format", "SafeTensor")
            elif lower_name.endswith(".ckpt"):
                metadata.setdefault("format", "PickleTensor")

            result.append(canonical_file(
                filename=name,
                size_kb=f.get("sizeKB"),
                sha256=sha256,
                download_url=download_url,
                format=metadata.get("format"),
                primary=True,
                raw=f,
            ))

        # Prefer .safetensors over .ckpt, matching CivArchive client behaviour.
        result.sort(key=lambda f: (
            0 if str(f.get("name", "")).lower().endswith(".safetensors") else
            1 if str(f.get("name", "")).lower().endswith(".ckpt") else
            2
        ))
        return result

    def _normalize_images(self, images: list) -> list[dict]:
        """Convert CivArchive image entries to canonical images."""
        result: list[dict] = []
        for img in images:
            if not isinstance(img, dict):
                continue
            url = img.get("url")
            if not url:
                continue
            result.append(canonical_image(
                url=url,
                width=img.get("width"),
                height=img.get("height"),
                nsfw=img.get("nsfwLevel"),
                hash=img.get("hash"),
                prompt=img.get("meta", {}).get("prompt") if isinstance(img.get("meta"), dict) else None,
                raw=img,
            ))
        return result

    def _build_stats(self, data: dict) -> dict:
        """Extract CivitAI-compatible stats from CivArchive fields."""
        stats: dict = {}
        for key in ("downloadCount", "ratingCount", "rating", "favoriteCount", "commentCount"):
            if key in data:
                stats[key] = data[key]
        return stats


# Register on import.
register_source(CivArchiveSource())
