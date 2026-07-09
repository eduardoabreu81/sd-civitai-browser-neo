"""Regression tests for model-id parsing across browser sources."""

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


API_PATH = Path(__file__).resolve().parents[1] / "scripts" / "civitai_api.py"


def _load_civitai_api_with_stubs():
    modules_pkg = types.ModuleType("modules")
    paths_mod = types.ModuleType("modules.paths")
    paths_mod.models_path = ""
    paths_mod.extensions_dir = ""
    paths_mod.data_path = ""

    images_mod = types.ModuleType("modules.images")
    images_mod.read_info_from_image = lambda image: (None, None)

    shared_mod = types.ModuleType("modules.shared")
    shared_mod.cmd_opts = types.SimpleNamespace(ckpt_dirs=[])
    shared_mod.opts = types.SimpleNamespace()

    download_mod = types.ModuleType("scripts.civitai_download")
    file_manage_mod = types.ModuleType("scripts.civitai_file_manage")

    global_mod = types.ModuleType("scripts.civitai_global")
    global_mod.init = lambda: None
    global_mod.print = print
    global_mod.debug_print = lambda *args, **kwargs: None

    browser_sources_mod = types.ModuleType("scripts.browser_sources")
    browser_sources_mod.get_browser_source = lambda name: None
    browser_sources_mod.default_source = lambda: None

    gradio_mod = types.ModuleType("gradio")
    gradio_mod.update = lambda **kwargs: kwargs

    overrides = {
        "gradio": gradio_mod,
        "modules": modules_pkg,
        "modules.paths": paths_mod,
        "modules.images": images_mod,
        "modules.shared": shared_mod,
        "scripts.civitai_download": download_mod,
        "scripts.civitai_file_manage": file_manage_mod,
        "scripts.civitai_global": global_mod,
        "scripts.browser_sources": browser_sources_mod,
    }

    with patch.dict(sys.modules, overrides, clear=False):
        spec = importlib.util.spec_from_file_location("civitai_api_under_test", API_PATH)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module


class TestModelIdParsing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api = _load_civitai_api_with_stubs()

    def test_extract_model_info_keeps_civitai_ids_numeric(self):
        name, model_id = self.api.extract_model_info("Cool Model (12345)")

        self.assertEqual(name, "Cool Model")
        self.assertEqual(model_id, 12345)

    def test_extract_model_info_allows_external_string_ids(self):
        name, model_id = self.api.extract_model_info("Animagine XL (cagliostrolab/animagine-xl-3.1)")

        self.assertEqual(name, "Animagine XL")
        self.assertEqual(model_id, "cagliostrolab/animagine-xl-3.1")

    def test_model_id_matches_supports_numeric_and_external_ids(self):
        self.assertTrue(self.api.model_id_matches("123", 123))
        self.assertTrue(self.api.model_id_matches("cagliostrolab/animagine-xl-3.1", "cagliostrolab/animagine-xl-3.1"))
        self.assertFalse(self.api.model_id_matches("owner/repo-a", "owner/repo-b"))


if __name__ == "__main__":
    unittest.main()
