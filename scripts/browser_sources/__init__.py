"""Browser source adapters for the Multi-Browser Neo extension.

Importing this module registers the built-in sources so the rest of the
extension can resolve them by name.
"""

from __future__ import annotations

from .base import BrowserSource
from .registry import (
    default_source,
    get_browser_source,
    list_browser_sources,
    register_source,
    source_choices,
    source_display_names,
    source_name_from_display,
)

# Register built-in sources. Keep CivitAI first so it remains the default.
from . import civitai
from . import civarchive
from . import huggingface
from . import arcenciel

__all__ = [
    "BrowserSource",
    "register_source",
    "get_browser_source",
    "list_browser_sources",
    "source_choices",
    "source_display_names",
    "source_name_from_display",
    "default_source",
]
