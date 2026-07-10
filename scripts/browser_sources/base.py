"""Base class for all browser model sources.

This module defines the contract every source adapter must implement so that
the rest of the extension (UI, download, organization, update detection) can
consume models from CivitAI, CivArchive, HuggingFace, arcenciel.io,
ModelScope, etc., without knowing platform-specific details.

The canonical model format produced by every adapter intentionally mirrors the
CivitAI API shape so existing code paths keep working with minimal changes.
"""

from __future__ import annotations

import abc
from typing import Any, Optional


class BrowserSource(abc.ABC):
    """Abstract adapter for a remote model repository.

    Each concrete subclass lives in its own module and is registered via
    ``scripts/browser_sources/registry.py``.

    Parameters
    ----------
    name:
        Machine-readable identifier used in settings and sidecars, e.g.
        ``"civitai"``, ``"civarchive"``, ``"huggingface"``.
    display_name:
        Human-readable label shown in the UI dropdown.
    """

    def __init__(self, name: str, display_name: str, visible_in_dropdown: bool = True) -> None:
        self.name = name
        self.display_name = display_name
        self.visible_in_dropdown = visible_in_dropdown

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------
    @abc.abstractmethod
    def supports(self, content_type: Optional[str]) -> bool:
        """Return True if the source can serve the given content type.

        ``content_type`` uses the extension's internal naming (Checkpoint,
        LORA, TextualInversion, etc.). A source may return True for all types
        if it does not distinguish them at search time.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def supported_search_types(self) -> list[str]:
        """Return the search modes this source supports.

        Common values: ``Model name``, ``User name``, ``Tag``, ``SHA256``,
        ``URL``. The UI will enable/disable the Search type radio accordingly.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def supports_pagination(self) -> bool:
        """Return True if search results are paginated natively."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Search / fetch
    # ------------------------------------------------------------------
    @abc.abstractmethod
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
        """Search the source and return a paginated result in canonical format.

        The returned dict must contain:

        - ``items``: list of model dicts in canonical format.
        - ``metadata``: dict with at least ``currentPage``, ``pageSize``,
          ``totalItems``, ``totalPages``. For sources without native counts,
          ``totalItems``/``totalPages`` may be estimated or omitted.
        - ``nextPage`` / ``prevPage`` (optional): opaque tokens/URLs for
          pagination. The caller stores them in ``gl.url_list``.

        The method should raise or return an error string (``'error'``,
        ``'not_found'``, ``'offline'``) on failure to stay compatible with
        existing error handling.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_model(self, source_id: str, **kwargs: Any) -> Optional[dict]:
        """Fetch a single model by its source-specific id.

        Returns the model in canonical format, or ``None`` if not found.
        """
        raise NotImplementedError

    def get_version_by_hash(self, sha256: str) -> Optional[dict]:
        """Try to locate a model version by SHA256.

        Default implementation returns ``None``. Sources that support hash
        lookup (CivitAI, CivArchive) should override this.
        """
        return None

    # ------------------------------------------------------------------
    # Download helpers
    # ------------------------------------------------------------------
    @abc.abstractmethod
    def get_download_url(self, file_info: dict, **kwargs: Any) -> Optional[str]:
        """Return a direct download URL for a canonical file dict.

        The returned URL must be usable by Aria2 / requests without further
        source-specific logic in the download layer.
        """
        raise NotImplementedError

    def get_preview_url(self, image_info: dict, **kwargs: Any) -> Optional[str]:
        """Return a display URL for a canonical image dict.

        Default returns ``image_info.get('url')``.
        """
        return image_info.get("url") if isinstance(image_info, dict) else None

    # ------------------------------------------------------------------
    # Normalization helpers (optional hooks)
    # ------------------------------------------------------------------
    def normalize_base_model(self, raw: Optional[str]) -> Optional[str]:
        """Normalize a source-specific base model name to extension naming.

        Default returns the value unchanged.
        """
        return raw

    def normalize_content_type(self, raw: Optional[str]) -> Optional[str]:
        """Normalize a source-specific content type to extension naming.

        Default returns the value unchanged.
        """
        return raw
