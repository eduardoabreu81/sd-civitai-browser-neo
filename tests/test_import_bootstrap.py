"""Tests for the `scripts` namespace repair that keeps the extension loadable.

Background (issue #5): A1111/Forge rely on `scripts` being an implicit namespace
package, so Python merges `webui/scripts` with the `scripts/` folder of every
installed extension. That merge is what lets this extension do
`import scripts.civitai_api`.

The merge collapses the moment ANY single extension — or a package in
site-packages — ships a `scripts/__init__.py`. `scripts` then becomes a regular
package bound to that one directory, and every extension importing
`scripts.<module>` fails at once with ModuleNotFoundError, regardless of load
order. The user cannot fix that without hunting down the offending extension.

`ensure_scripts_namespace()` repairs it from our side by putting our own
`scripts/` directory back on `scripts.__path__`.
"""

import importlib
import importlib.util
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


BOOTSTRAP_PATH = Path(__file__).resolve().parents[1] / "scripts" / "civitai_bootstrap.py"


def _load_bootstrap():
    """Load the bootstrap exactly the way the extension does: by absolute path.

    It must never need the `scripts` package itself, since that is the very
    thing that may be broken when it runs.
    """
    spec = importlib.util.spec_from_file_location("civitai_bootstrap", BOOTSTRAP_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestEnsureScriptsNamespace(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bootstrap = _load_bootstrap()

    def _make_extension_scripts_dir(self, module_name, marker_value):
        """Build a throwaway `<ext>/scripts/` holding one importable module.

        Each directory gets a distinctly named module, so a successful import
        proves which directory actually served it.
        """
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        scripts_dir = root / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / f"{module_name}.py").write_text(f"MARKER = {marker_value!r}\n", encoding="utf-8")
        return scripts_dir

    def _isolated_import_state(self, first_on_path):
        """Context manager restoring sys.modules and sys.path around an import test."""
        return patch.dict(sys.modules), patch.object(sys, "path", [str(first_on_path)])

    def test_repairs_a_namespace_closed_by_another_extension(self):
        """The reported failure: someone else's `scripts/__init__.py` wins, and
        `import scripts.civitai_probe` raises ModuleNotFoundError until we repair it."""
        ours = self._make_extension_scripts_dir("civitai_probe", "ours")
        intruder = self._make_extension_scripts_dir("their_module", "theirs")
        (intruder / "__init__.py").write_text("", encoding="utf-8")

        modules_patch, path_patch = self._isolated_import_state(intruder.parent)
        with modules_patch, path_patch:
            sys.modules.pop("scripts", None)
            importlib.invalidate_caches()

            importlib.import_module("scripts")  # binds as a regular, closed package
            with self.assertRaises(ModuleNotFoundError):
                importlib.import_module("scripts.civitai_probe")

            self.bootstrap.ensure_scripts_namespace(str(ours))

            self.assertEqual(importlib.import_module("scripts.civitai_probe").MARKER, "ours")

    def test_keeps_the_directories_the_webui_already_registered(self):
        """Repairing our own imports must not hide anyone else's modules."""
        ours = self._make_extension_scripts_dir("civitai_probe", "ours")
        intruder = self._make_extension_scripts_dir("their_module", "theirs")
        (intruder / "__init__.py").write_text("", encoding="utf-8")

        modules_patch, path_patch = self._isolated_import_state(intruder.parent)
        with modules_patch, path_patch:
            sys.modules.pop("scripts", None)
            importlib.invalidate_caches()
            importlib.import_module("scripts")

            self.bootstrap.ensure_scripts_namespace(str(ours))

            self.assertEqual(importlib.import_module("scripts.their_module").MARKER, "theirs")
            self.assertEqual(importlib.import_module("scripts.civitai_probe").MARKER, "ours")

    def test_creates_the_package_when_scripts_cannot_be_imported_at_all(self):
        """Nothing named `scripts` on the path — the module has to be synthesised."""
        ours = self._make_extension_scripts_dir("civitai_probe", "ours")
        empty = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, empty, True)

        modules_patch, path_patch = self._isolated_import_state(empty)
        with modules_patch, path_patch:
            sys.modules.pop("scripts", None)
            importlib.invalidate_caches()

            self.bootstrap.ensure_scripts_namespace(str(ours))

            self.assertEqual(importlib.import_module("scripts.civitai_probe").MARKER, "ours")

    def test_is_idempotent(self):
        """Every entry-point module calls this on startup; the search path must
        not grow a duplicate entry each time."""
        ours = self._make_extension_scripts_dir("civitai_probe", "ours")

        with patch.dict(sys.modules):
            package = types.ModuleType("scripts")
            package.__path__ = []
            sys.modules["scripts"] = package

            for _ in range(3):
                self.bootstrap.ensure_scripts_namespace(str(ours))

            self.assertEqual(list(package.__path__), [str(ours)])

    def test_tolerates_a_trailing_separator_or_relative_spelling(self):
        """The caller passes `os.path.dirname(__file__)`, whose exact spelling
        depends on how the WebUI loaded the script."""
        ours = self._make_extension_scripts_dir("civitai_probe", "ours")

        with patch.dict(sys.modules):
            package = types.ModuleType("scripts")
            package.__path__ = [str(ours)]
            sys.modules["scripts"] = package

            self.bootstrap.ensure_scripts_namespace(str(ours) + "/")

            self.assertEqual(len(list(package.__path__)), 1)

    def test_defaults_to_its_own_directory(self):
        """Entry-point modules call it with no argument, so the default has to
        point at the extension's real `scripts/` folder."""
        with patch.dict(sys.modules):
            package = types.ModuleType("scripts")
            package.__path__ = []
            sys.modules["scripts"] = package

            self.bootstrap.ensure_scripts_namespace()

            self.assertEqual(list(package.__path__), [str(BOOTSTRAP_PATH.parent)])


if __name__ == "__main__":
    unittest.main()
