"""Keep ``import scripts.<module>`` working when another extension closes the namespace.

A1111/Forge rely on ``scripts`` being an implicit *namespace package*: Python
merges ``webui/scripts`` with the ``scripts/`` folder of every installed
extension, which is what lets this extension do ``import scripts.civitai_api``.

That merge collapses the moment a single other extension — or a package sitting
in ``site-packages`` — ships a ``scripts/__init__.py``. ``scripts`` then becomes
a regular package bound to that one directory, and *every* extension importing
``scripts.<module>`` fails at once with ``ModuleNotFoundError``, whatever the
load order. Reported in issue #5 as five stacked "Error loading script" blocks.

This module is deliberately dependency-free and is loaded by absolute path, not
through ``scripts.civitai_bootstrap``, because that import is exactly what may
be broken when it runs.
"""

import os
import sys
import types


def ensure_scripts_namespace(scripts_dir=None):
    """Guarantee ``scripts_dir`` is reachable as the ``scripts`` package.

    Defaults to the directory this file lives in, which is the extension's own
    ``scripts/`` folder — callers never have to spell the path out.

    Repairs rather than replaces: directories the WebUI already registered stay
    on the search path, so other extensions keep resolving as before. Safe to
    call repeatedly — every entry-point module calls it on startup.
    """
    if scripts_dir is None:
        scripts_dir = os.path.dirname(os.path.abspath(__file__))
    scripts_dir = os.path.abspath(scripts_dir)
    package = _resolve_scripts_package()

    if package is None:
        package = types.ModuleType('scripts')
        package.__path__ = [scripts_dir]
        sys.modules['scripts'] = package
        return

    search_path = getattr(package, '__path__', None)
    if search_path is None:
        # ``scripts`` resolved to a plain module rather than a package.
        package.__path__ = [scripts_dir]
        return

    if any(os.path.abspath(entry) == scripts_dir for entry in search_path):
        return

    try:
        search_path.append(scripts_dir)
    except AttributeError:
        # Both list and importlib's _NamespacePath support append; rebuild the
        # search path by hand for any exotic loader that does not.
        package.__path__ = list(search_path) + [scripts_dir]


def _resolve_scripts_package():
    """Return the live ``scripts`` module, or None when nothing provides it."""
    package = sys.modules.get('scripts')
    if package is not None:
        return package

    try:
        import scripts
    except ImportError:
        return None

    return scripts
