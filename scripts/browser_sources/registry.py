"""Registry for browser source adapters.

Adapters are loaded lazily so importing this module does not trigger heavy
imports or network setup. Call ``register_source()`` at module load time and
``get_browser_source()`` at runtime.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .base import BrowserSource


# Maps source name -> adapter class or instance.
_REGISTRY: dict[str, BrowserSource] = {}


def register_source(source: "BrowserSource") -> "BrowserSource":
    """Register a BrowserSource instance.

    Returns the instance so it can be used as a decorator or standalone.
    """
    _REGISTRY[source.name] = source
    return source


def get_browser_source(name: str) -> Optional["BrowserSource"]:
    """Return the registered source for ``name``, or ``None``."""
    return _REGISTRY.get(name)


def list_browser_sources() -> list["BrowserSource"]:
    """Return all registered sources."""
    return list(_REGISTRY.values())


def source_display_names() -> dict[str, str]:
    """Return mapping ``name -> display_name`` for all registered sources."""
    return {name: source.display_name for name, source in _REGISTRY.items()}


def source_choices() -> list[str]:
    """Return display names in registration order for Gradio dropdowns."""
    return [source.display_name for source in _REGISTRY.values()]


def source_name_from_display(display_name: str) -> Optional[str]:
    """Reverse lookup a source machine name from its display label."""
    for name, source in _REGISTRY.items():
        if source.display_name == display_name:
            return name
    return None


def default_source() -> "BrowserSource":
    """Return the default source (CivitAI if available, otherwise first)."""
    if "civitai" in _REGISTRY:
        return _REGISTRY["civitai"]
    if _REGISTRY:
        return next(iter(_REGISTRY.values()))
    raise RuntimeError("No browser sources registered")
