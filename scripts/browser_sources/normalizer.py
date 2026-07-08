"""Canonical model format used across all browser sources.

The extension was originally built around the CivitAI API v1 response shape.
Instead of rewriting every consumer (card HTML, download queue, organization,
etc.), adapters normalize foreign payloads into that same shape and add a few
browser-source metadata fields.
"""

from __future__ import annotations

from typing import Any, Optional


# Fields that must exist at the top level of every canonical model.
REQUIRED_MODEL_FIELDS = (
    "id",
    "name",
    "type",
    "browserSource",
    "browserSourceId",
)

# Fields that must exist inside each canonical version.
REQUIRED_VERSION_FIELDS = ("id", "name", "files")


def canonical_model(
    *,
    source: str,
    source_id: str,
    name: str,
    model_type: str,
    source_url: Optional[str] = None,
    description: Optional[str] = None,
    creator: Optional[dict] = None,
    tags: Optional[list] = None,
    base_model: Optional[str] = None,
    nsfw: bool = False,
    versions: Optional[list] = None,
    stats: Optional[dict] = None,
    raw: Optional[dict] = None,
) -> dict:
    """Build a canonical model dict.

    Parameters match the fields existing CivitAI consumers already expect,
    plus ``browserSource*`` provenance fields.
    """
    return {
        "id": source_id,
        "name": name,
        "type": model_type,
        "description": description or "",
        "creator": creator or {},
        "tags": list(tags or []),
        "baseModel": base_model,
        "nsfw": bool(nsfw),
        "modelVersions": list(versions or []),
        "stats": stats or {},
        "browserSource": source,
        "browserSourceId": source_id,
        "browserSourceUrl": source_url,
        "browserSourceRaw": raw,
    }


def canonical_version(
    *,
    source_version_id: str,
    name: str,
    base_model: Optional[str] = None,
    created_at: Optional[str] = None,
    updated_at: Optional[str] = None,
    description: Optional[str] = None,
    trained_words: Optional[list] = None,
    activation_tags: Optional[list] = None,
    files: Optional[list] = None,
    images: Optional[list] = None,
    download_url: Optional[str] = None,
    stats: Optional[dict] = None,
    raw: Optional[dict] = None,
) -> dict:
    """Build a canonical version dict.

    The shape mirrors CivitAI's ``modelVersions`` items.
    """
    return {
        "id": source_version_id,
        "name": name,
        "baseModel": base_model,
        "createdAt": created_at,
        "updatedAt": updated_at,
        "description": description or "",
        "trainedWords": list(trained_words or []),
        "activationTags": list(activation_tags or []),
        "files": list(files or []),
        "images": list(images or []),
        "downloadUrl": download_url,
        "stats": stats or {},
        "browserSourceVersionId": source_version_id,
        "browserSourceVersionRaw": raw,
    }


def canonical_file(
    *,
    filename: str,
    size_kb: Optional[int] = None,
    size_bytes: Optional[int] = None,
    sha256: Optional[str] = None,
    download_url: Optional[str] = None,
    format: Optional[str] = None,
    primary: bool = False,
    raw: Optional[dict] = None,
) -> dict:
    """Build a canonical file dict.

    Mirrors CivitAI's ``files`` items, where hashes live inside a nested dict.
    """
    raw_metadata = raw.get("metadata") if isinstance(raw, dict) else None
    metadata = dict(raw_metadata) if isinstance(raw_metadata, dict) else {}

    resolved_format = format or metadata.get("format")
    if not resolved_format:
        lower_filename = filename.lower()
        if lower_filename.endswith(".safetensors"):
            resolved_format = "SafeTensor"
        elif lower_filename.endswith((".ckpt", ".pt", ".pth", ".bin")):
            resolved_format = "PickleTensor"
        elif lower_filename.endswith(".onnx"):
            resolved_format = "ONNX"
    if resolved_format:
        metadata["format"] = resolved_format

    file_info = {
        "name": filename,
        "sizeKB": size_kb,
        "sizeBytes": size_bytes,
        "downloadUrl": download_url,
        "format": resolved_format,
        "metadata": metadata,
        "primary": primary,
        "hashes": {},
        "browserSourceFileRaw": raw,
    }
    if sha256:
        file_info["hashes"]["SHA256"] = sha256.upper()
        file_info["sha256"] = sha256.upper()
    return file_info


def canonical_image(
    *,
    url: str,
    width: Optional[int] = None,
    height: Optional[int] = None,
    nsfw: Optional[str] = None,
    hash: Optional[str] = None,
    prompt: Optional[str] = None,
    raw: Optional[dict] = None,
) -> dict:
    """Build a canonical image dict.

    Mirrors CivitAI's ``images`` items used for card previews and galleries.
    """
    return {
        "url": url,
        "width": width,
        "height": height,
        "nsfw": nsfw,
        "hash": hash,
        "prompt": prompt or "",
        "browserSourceImageRaw": raw,
    }


def paginated_result(
    items: list[dict],
    *,
    current_page: int = 1,
    page_size: int = 20,
    total_items: Optional[int] = None,
    total_pages: Optional[int] = None,
    next_page: Optional[str] = None,
    prev_page: Optional[str] = None,
    source: str,
) -> dict:
    """Build a canonical paginated search result.

    This is the envelope expected by ``initial_model_page`` and friends.
    """
    metadata = {
        "currentPage": current_page,
        "pageSize": page_size,
        "totalItems": total_items if total_items is not None else len(items),
        "totalPages": total_pages if total_pages is not None else 1,
        "source": source,
    }
    if next_page:
        metadata["nextPage"] = next_page
    if prev_page:
        metadata["prevPage"] = prev_page
    return {
        "items": items,
        "metadata": metadata,
    }


def get_sha256(file_info: Optional[dict]) -> Optional[str]:
    """Extract SHA256 from a canonical file dict, normalizing case."""
    if not isinstance(file_info, dict):
        return None
    sha = file_info.get("sha256")
    if sha:
        return sha.upper()
    hashes = file_info.get("hashes") or {}
    sha = hashes.get("SHA256") or hashes.get("sha256")
    return sha.upper() if sha else None
