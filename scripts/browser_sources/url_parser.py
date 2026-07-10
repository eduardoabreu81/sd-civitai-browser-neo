"""Parse a pasted model URL and dispatch to the right browser source adapter.

This module turns any supported model page URL into a single-item canonical
search result so the Browser tab can render a card and offer download without
needing a curated catalog or source-specific browse flow.
"""

from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse

import scripts.civitai_api as _api
from scripts.civitai_global import debug_print

from .normalizer import paginated_result
from .registry import get_browser_source


def _normalize_url(url: str) -> str:
    """Strip whitespace and ensure a scheme is present for parsing."""
    url = (url or "").strip()
    if url and not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url


def _extract_civitai_model_id(url: str) -> Optional[str]:
    """Return a CivitAI model id from a model page URL, or None."""
    parsed = urlparse(url)
    path = parsed.path or ""
    # https://civitai.com/models/12345 or /models/12345-model-name
    match = re.search(r"/models/(\d+)", path)
    if match:
        return match.group(1)
    return None


def _extract_civitai_version_id(url: str) -> Optional[str]:
    """Return a CivitAI model version id from a download URL, or None."""
    parsed = urlparse(url)
    path = parsed.path or ""
    # https://civitai.com/api/download/models/67890
    match = re.search(r"/api/download/models/(\d+)", path)
    if match:
        return match.group(1)
    return None


def _extract_civarchive_model_id(url: str) -> Optional[str]:
    """Return a CivArchive model id from a model page URL, or None."""
    parsed = urlparse(url)
    path = parsed.path or ""
    match = re.search(r"/models/(\d+)", path)
    if match:
        return match.group(1)
    return None


def _extract_hf_repo_id(url: str) -> Optional[str]:
    """Return a Hugging Face repo_id (owner/repo) from a repo URL, or None."""
    parsed = urlparse(url)
    path = parsed.path or ""
    # Remove /tree/main, /blob/main, /resolve/main, trailing slashes.
    path = re.sub(r"/(tree|blob|resolve)/.*$", "", path).strip("/")
    parts = [p for p in path.split("/") if p]
    if len(parts) >= 2:
        return "/".join(parts[:2])
    return None


def _extract_arcenciel_model_id(url: str) -> Optional[str]:
    """Return an Arc en Ciel model id from a model page URL, or None."""
    parsed = urlparse(url)
    path = parsed.path or ""
    match = re.search(r"/models/(\d+)", path)
    if match:
        return match.group(1)
    return None


def _resolve_civitai_version_to_model(version_id: str) -> Optional[str]:
    """Fetch a CivitAI model version and return its parent model id."""
    domain = _api.get_civitai_domain()
    api_url = f"https://{domain}/api/v1/model-versions/{version_id}"
    try:
        data = _api.request_civit_api(api_url, skip_error_check=True)
    except Exception as exc:
        debug_print(f"[URLParser] CivitAI version lookup failed: {exc}")
        return None
    if isinstance(data, dict) and data.get("modelId"):
        return str(data["modelId"])
    return None


def parse_model_url(url: str) -> dict | str:
    """Parse a model URL and return a single-item paginated result.

    Returns an error string (``invalid_url``, ``not_found``, ``offline``,
    ``error``) when the URL is unsupported or the model cannot be fetched.
    """
    url = _normalize_url(url)
    if not url or not urlparse(url).netloc:
        return "invalid_url"

    parsed = urlparse(url)
    netloc = parsed.netloc.lower().lstrip("www.")

    # CivitAI (both SFW and full domains)
    configured_domain = _api.get_civitai_domain().lower()
    if netloc in (configured_domain, "civitai.com", "civitai.red"):
        version_id = _extract_civitai_version_id(url)
        if version_id:
            model_id = _resolve_civitai_version_to_model(version_id)
        else:
            model_id = _extract_civitai_model_id(url)

        if not model_id:
            return "invalid_url"

        adapter = get_browser_source("civitai")
        if adapter is None:
            return "error"
        model = adapter.get_model(model_id)
        if model is None:
            return "not_found"
        return paginated_result(
            [model],
            current_page=1,
            page_size=1,
            total_items=1,
            total_pages=1,
            source=adapter.name,
        )

    # CivArchive
    if netloc in ("civarchive.com",):
        model_id = _extract_civarchive_model_id(url)
        if not model_id:
            return "invalid_url"
        adapter = get_browser_source("civarchive")
        if adapter is None:
            return "error"
        model = adapter.get_model(model_id)
        if model is None:
            return "not_found"
        return paginated_result(
            [model],
            current_page=1,
            page_size=1,
            total_items=1,
            total_pages=1,
            source=adapter.name,
        )

    # Hugging Face
    if netloc in ("huggingface.co", "hf.co"):
        repo_id = _extract_hf_repo_id(url)
        if not repo_id:
            return "invalid_url"
        adapter = get_browser_source("huggingface")
        if adapter is None:
            return "error"
        model = adapter.get_model(repo_id)
        if model is None:
            return "not_found"
        return paginated_result(
            [model],
            current_page=1,
            page_size=1,
            total_items=1,
            total_pages=1,
            source=adapter.name,
        )

    # Arc en Ciel
    if netloc in ("arcenciel.io",):
        model_id = _extract_arcenciel_model_id(url)
        if not model_id:
            return "invalid_url"
        adapter = get_browser_source("arcenciel")
        if adapter is None:
            return "error"
        model = adapter.get_model(model_id)
        if model is None:
            return "not_found"
        return paginated_result(
            [model],
            current_page=1,
            page_size=1,
            total_items=1,
            total_pages=1,
            source=adapter.name,
        )

    return "invalid_url"
