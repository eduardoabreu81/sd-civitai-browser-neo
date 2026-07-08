"""CivitAI browser source adapter.

This adapter wraps the existing CivitAI API helpers in ``scripts.civitai_api``
so the extension can treat CivitAI as just one of many browser sources while
keeping all current behaviour intact.
"""

from __future__ import annotations

import re
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

import requests

# Reuse existing transport/auth helpers so behaviour stays identical.
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


class CivitAISource(BrowserSource):
    """Browser source adapter for CivitAI (civitai.com / civitai.red)."""

    # Internal mapping of UI sort labels to CivitAI API values.
    SORT_MAP = {
        "Newest": "Newest",
        "Oldest": "Oldest",
        "Most Downloaded": "Most Downloaded",
        "Highest Rated": "Highest Rated",
        "Most Liked": "Most Liked",
        "Most Buzz": "Most Buzz",
        "Most Discussed": "Most Discussed",
        "Most Collected": "Most Collected",
        "Most Images": "Most Images",
    }

    PERIOD_MAP = {
        "All Time": "AllTime",
        "Year": "Year",
        "Month": "Month",
        "Week": "Week",
        "Day": "Day",
    }

    def __init__(self) -> None:
        super().__init__("civitai", "CivitAI")

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------
    def supports(self, content_type: Optional[str]) -> bool:
        """CivitAI supports all content types the extension knows about."""
        return True

    def supported_search_types(self) -> list[str]:
        return ["Model name", "User name", "Tag", "SHA256"]

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
        """Search CivitAI and return results in canonical format."""
        if search_type == "SHA256" and query:
            return self._search_by_sha256(query)

        api_url = self._create_api_url(
            query=query,
            search_type=search_type,
            content_type=content_type,
            base_filter=base_filter,
            sort=sort,
            period=period,
            nsfw=nsfw,
            exact=exact,
            page_size=page_size,
            only_liked=only_liked,
            page_url=kwargs.get("page_url"),
        )
        if not api_url:
            return {"items": [], "metadata": {"currentPage": 1, "pageSize": page_size, "totalItems": 0, "totalPages": 1}}

        data = _api.request_civit_api(api_url)
        if isinstance(data, str):
            # Existing error strings: 'error', 'not_found', 'offline', 'timeout', 'dns_error'
            return data

        result = self._normalize_search_result(data)
        # Store the real CivitAI page URLs so pagination can reuse them directly.
        result['metadata']['nextPage'] = data.get('metadata', {}).get('nextPage')
        result['metadata']['prevPage'] = data.get('metadata', {}).get('prevPage')
        result['metadata']['_civitaiPageUrl'] = api_url
        return result

    def get_model(self, source_id: str, **kwargs: Any) -> Optional[dict]:
        """Fetch a single CivitAI model by id."""
        api_url = f"https://{_api.get_civitai_domain()}/api/v1/models/{source_id}"
        data = _api.request_civit_api(api_url)
        if not isinstance(data, dict) or "error" in data:
            return None
        return self._normalize_model(data)

    def get_version_by_hash(self, sha256: str) -> Optional[dict]:
        """Look up a CivitAI version by SHA256."""
        result = self._search_by_sha256(sha256)
        if isinstance(result, dict) and "items" in result and result["items"]:
            return result["items"][0]
        return None

    # ------------------------------------------------------------------
    # Download helpers
    # ------------------------------------------------------------------
    def get_download_url(self, file_info: dict, **kwargs: Any) -> Optional[str]:
        """Return the download URL from a canonical CivitAI file dict."""
        if not isinstance(file_info, dict):
            return None
        return file_info.get("downloadUrl") or file_info.get("download_url")

    def get_preview_url(self, image_info: dict, **kwargs: Any) -> Optional[str]:
        """Return CivitAI image URL."""
        if not isinstance(image_info, dict):
            return None
        return image_info.get("url")

    # ------------------------------------------------------------------
    # Internal URL builders (mirrors original create_api_url behaviour)
    # ------------------------------------------------------------------
    def _create_api_url(
        self,
        *,
        query: str,
        search_type: str,
        content_type: Optional[str | list[str]],
        base_filter: Optional[str | list[str]],
        sort: str,
        period: str,
        nsfw: bool,
        exact: bool,
        page_size: int,
        only_liked: bool,
        page_url: Optional[str] = None,
        page: int = 1,
    ) -> Optional[str]:
        """Build a CivitAI /api/v1/models URL matching the original logic."""
        domain = _api.get_civitai_domain()
        base_url = f"https://{domain}/api/v1/models"

        # If a real next/prev page URL is provided, use it directly.  Ignore
        # browser_source:// opaque tokens (they only mark that a search happened)
        # and validate that the URL actually points to the requested page.
        if page_url and not page_url.startswith("browser_source://"):
            try:
                parsed = urlparse(page_url)
                qs = parse_qs(parsed.query)
                url_page = qs.get("page", [None])[0]
                # CivitAI uses 1-based page numbers; accept the URL when it
                # matches the requested page or when no page param is present.
                if url_page is None or int(url_page) == page:
                    return page_url
            except Exception:
                pass
            # Mismatch: fall through and rebuild from parameters.

        params: dict[str, Any] = {
            "limit": page_size,
            "sort": self.SORT_MAP.get(sort, sort),
            "period": self.PERIOD_MAP.get(period, period.replace(" ", "") if period else None),
            "page": page,
        }

        if content_type:
            params["types"] = content_type

        if query:
            lower_query = query.replace("\\", "\\\\").lower()

            # Exact search quoting for multi-word terms
            if exact and search_type in ("Model name", "User name", "Tag"):
                if not (lower_query.startswith('"') and lower_query.endswith('"')) and " " in lower_query:
                    lower_query = f'"{lower_query}"'

            # CivitAI link pasted into search box
            if "civitai.com" in lower_query or "civitai.red" in lower_query:
                if "/api/download/models" in lower_query:
                    m = re.search(r"models/(\d+)", lower_query)
                    if m:
                        version_data = _api.request_civit_api(
                            f"https://{domain}/api/v1/model-versions/{m.group(1)}",
                            skip_error_check=True,
                        )
                        if isinstance(version_data, dict) and "modelId" in version_data:
                            params = {"ids": str(version_data["modelId"])}
                else:
                    m = re.search(r"models/(\d+)", lower_query)
                    if m:
                        params = {"ids": m.group(1)}
            else:
                key_map = {"User name": "username", "Tag": "tag"}
                params[key_map.get(search_type, "query")] = lower_query

        if base_filter:
            params["baseModels"] = base_filter

        if only_liked:
            params["favorites"] = "true"

        params["nsfw"] = "true" if nsfw else "false"

        # Flatten lists for urlencode
        query_parts = []
        for key, value in params.items():
            if isinstance(value, list):
                for item in value:
                    query_parts.append((key, item))
            else:
                query_parts.append((key, value))

        from urllib.parse import urlencode, quote
        query_string = urlencode(query_parts, doseq=True, quote_via=quote)
        return f"{base_url}?{query_string}"

    def _search_by_sha256(self, sha256_hash: str) -> dict:
        """Search CivitAI by SHA256 across both domains."""
        normalized_hash = _api.normalize_sha256(sha256_hash)
        if not normalized_hash or not re.match(r"^[A-F0-9]{64}$", normalized_hash):
            return "invalid_hash"

        headers = _api.get_headers()
        proxies, ssl = _api.get_proxies()
        candidates = []
        domains = ["https://civitai.com", "https://civitai.red"]

        for domain in domains:
            api_url = f"{domain}/api/v1/model-versions/by-hash/{normalized_hash}"
            try:
                response = requests.get(api_url, headers=headers, timeout=(60, 30), proxies=proxies, verify=ssl)
            except requests.exceptions.RequestException:
                continue

            if response.status_code == 200:
                data = response.json()
                if not data or "error" in data:
                    continue
                files = data.get("files", []) or []
                for f in files:
                    file_sha = (f.get("hashes", {}) or {}).get("SHA256", "")
                    if file_sha and file_sha.strip().upper() == normalized_hash:
                        candidates.append({
                            "domain": domain,
                            "modelId": data.get("modelId"),
                            "versionId": data.get("id"),
                            "version_name": data.get("name"),
                            "file_name": f.get("name"),
                            "downloadUrl": f.get("downloadUrl") or data.get("downloadUrl"),
                        })
                        break
            elif response.status_code == 404:
                continue
            elif response.status_code == 503:
                return "offline"

        if not candidates:
            return "sha256_not_found"
        if len(candidates) == 1:
            candidate = candidates[0]
            model_id = candidate.get("modelId")
            if not model_id:
                return "not_found"
            model_url = f"https://{_api.get_civitai_domain()}/api/v1/models/{model_id}"
            model_response = requests.get(model_url, headers=headers, timeout=(60, 30), proxies=proxies, verify=ssl)
            if model_response.status_code == 200:
                model_data = model_response.json()
                return self._normalize_search_result({
                    "items": [model_data],
                    "metadata": {
                        "totalItems": 1,
                        "currentPage": 1,
                        "pageSize": 1,
                        "totalPages": 1,
                    },
                })
            return "not_found"

        return {"ambiguous": candidates}

    # ------------------------------------------------------------------
    # Normalization
    # ------------------------------------------------------------------
    def _normalize_search_result(self, data: dict) -> dict:
        """Add browser-source metadata to a CivitAI search result."""
        metadata = data.get("metadata", {})
        items = [self._normalize_model(item) for item in data.get("items", []) if isinstance(item, dict)]
        return {
            "items": items,
            "metadata": {
                "currentPage": metadata.get("currentPage", 1),
                "pageSize": metadata.get("pageSize", len(items) or 20),
                "totalItems": metadata.get("totalItems", len(items)),
                "totalPages": metadata.get("totalPages", 1),
                "nextPage": metadata.get("nextPage"),
                "prevPage": metadata.get("prevPage"),
                "source": self.name,
            },
        }

    def _normalize_model(self, item: dict) -> dict:
        """Tag a CivitAI model dict with browser-source provenance."""
        if not isinstance(item, dict):
            return item

        # Avoid mutating the original API response.
        model = dict(item)
        model.setdefault("browserSource", self.name)
        model.setdefault("browserSourceId", str(model.get("id", "")))
        model.setdefault(
            "browserSourceUrl",
            f"https://{_api.get_civitai_domain()}/models/{model.get('id', '')}",
        )

        # Tag versions/files/images if present.
        for version in model.get("modelVersions", []) or []:
            version.setdefault("browserSource", self.name)
            version.setdefault("browserSourceVersionId", str(version.get("id", "")))
            for file_info in version.get("files", []) or []:
                file_info.setdefault("browserSource", self.name)
                file_info.setdefault("sha256", get_sha256(file_info))
            for image in version.get("images", []) or []:
                image.setdefault("browserSource", self.name)

        return model


# Register on import.
register_source(CivitAISource())
