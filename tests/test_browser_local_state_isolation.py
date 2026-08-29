"""Regression coverage for Browser/Local Models state isolation."""

import ast
from pathlib import Path
from types import SimpleNamespace
import unittest


ROOT = Path(__file__).resolve().parents[1]
DOWNLOAD_PATH = ROOT / "scripts" / "civitai_download.py"
GUI_PATH = ROOT / "scripts" / "civitai_gui.py"
JS_PATH = ROOT / "javascript" / "civitai-html.js"


def _load_all_known_items():
    tree = ast.parse(DOWNLOAD_PATH.read_text(encoding="utf-8"))
    node = next(
        item
        for item in tree.body
        if isinstance(item, ast.FunctionDef) and item.name == "_all_known_items"
    )
    module = ast.Module(body=[node], type_ignores=[])
    namespace = {
        "gl": SimpleNamespace(
            json_data={"items": [{"id": "browser"}]},
            local_json_data={"items": [{"id": "local"}]},
        )
    }
    exec(compile(module, str(DOWNLOAD_PATH), "exec"), namespace)
    return namespace["_all_known_items"]


def _load_version_resolver():
    tree = ast.parse(DOWNLOAD_PATH.read_text(encoding="utf-8"))
    nodes = [
        item
        for item in tree.body
        if isinstance(item, ast.FunctionDef)
        and item.name in {"_pick_filtered_or_first", "_resolve_versions_to_download"}
    ]
    module = ast.Module(body=nodes, type_ignores=[])
    namespace = {}
    exec(compile(module, str(DOWNLOAD_PATH), "exec"), namespace)
    return namespace["_resolve_versions_to_download"]


class TestBrowserLocalStateIsolation(unittest.TestCase):
    def test_batch_click_snapshots_the_live_javascript_selection(self):
        js_source = JS_PATH.read_text(encoding="utf-8")
        gui_source = GUI_PATH.read_text(encoding="utf-8")
        gui_tree = ast.parse(gui_source)

        self.assertIn("function prepareSelectedBrowserDownload(", js_source)
        self.assertIn("const selectionSnapshot = JSON.stringify(selectedModels);", js_source)
        click_calls = [
            node
            for node in ast.walk(gui_tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "click"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "download_selected"
        ]
        self.assertEqual(len(click_calls), 1)
        js_keyword = next(
            keyword for keyword in click_calls[0].keywords if keyword.arg == "_js"
        )
        self.assertIsInstance(js_keyword.value, ast.Constant)
        self.assertIn("prepareSelectedBrowserDownload", js_keyword.value.value)

    def test_browser_base_filter_wins_over_another_installed_family(self):
        resolve = _load_version_resolver()
        pony = {
            "id": 20,
            "baseModel": "Pony",
            "files": [{"hashes": {"SHA256": "PONY"}}],
        }
        sdxl = {
            "id": 10,
            "baseModel": "SDXL 1.0",
            "files": [{"hashes": {"SHA256": "SDXL"}}],
        }

        result = resolve(
            [pony, sdxl],
            model_folder=None,
            base_filter=["Pony"],
            installed_scan=({"SDXL"}, {10}),
        )

        self.assertEqual(result, [pony])

    def test_filtered_version_already_installed_is_not_downloaded_again(self):
        resolve = _load_version_resolver()
        pony = {
            "id": 20,
            "baseModel": "Pony",
            "files": [{"hashes": {"SHA256": "PONY"}}],
        }

        result = resolve(
            [pony],
            model_folder=None,
            base_filter=["Pony"],
            installed_scan=({"PONY"}, {20}),
        )

        self.assertEqual(result, [])

    def test_browser_download_never_falls_back_to_local_filtered_data(self):
        all_known_items = _load_all_known_items()
        self.assertEqual(all_known_items("browser"), [{"id": "browser"}])

        source = DOWNLOAD_PATH.read_text(encoding="utf-8")
        self.assertIn("known_items = _all_known_items(origin)", source)

    def test_local_actions_prefer_local_but_keep_legacy_browser_fallback(self):
        all_known_items = _load_all_known_items()
        self.assertEqual(
            all_known_items("local"),
            [{"id": "local"}, {"id": "browser"}],
        )

    def test_browser_selection_reset_syncs_hidden_gradio_inputs(self):
        source = JS_PATH.read_text(encoding="utf-8")
        self.assertIn("clearModelSelection('browser');", source)
        self.assertIn("selectedModelList.value = JSON.stringify(selectedModels);", source)
        self.assertIn("selectedTypeList.value = JSON.stringify(selectedTypes);", source)
        self.assertIn("updateInput(selectedModelList);", source)
        self.assertIn("updateInput(selectedTypeList);", source)

    def test_browser_dom_filters_exclude_local_grid(self):
        source = JS_PATH.read_text(encoding="utf-8")
        self.assertIn(".filter((card) => !card.closest('#local_list_html'))", source)
        self.assertIn(
            "_browserCardElements('.civmodelcard')",
            source,
        )
        self.assertIn("_applyBrowserCardFilters();", source)


if __name__ == "__main__":
    unittest.main()
