"""Regression tests for Browser callback positional contracts."""

import ast
from pathlib import Path
import unittest


API_PATH = Path(__file__).resolve().parents[1] / "scripts" / "civitai_api.py"
PAGE_INPUT_ARGUMENTS = [
    "content_type",
    "sort_type",
    "period_type",
    "use_search_term",
    "search_term",
    "current_page",
    "base_filter",
    "only_liked",
    "nsfw",
    "exact_search",
    "tile_count",
    "source",
]


def _function_node(name):
    tree = ast.parse(API_PATH.read_text(encoding="utf-8"))
    return next(
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    )


class TestBrowserCallbackContract(unittest.TestCase):
    def test_initial_page_matches_gradio_page_inputs(self):
        node = _function_node("initial_model_page")
        positional = [argument.arg for argument in node.args.args]
        keyword_only = [argument.arg for argument in node.args.kwonlyargs]

        self.assertEqual(positional[:12], PAGE_INPUT_ARGUMENTS)
        self.assertEqual(keyword_only, ["from_update_tab", "target"])

    def test_pagination_callbacks_share_page_input_order(self):
        for function_name in ("next_model_page", "prev_model_page"):
            with self.subTest(function=function_name):
                node = _function_node(function_name)
                positional = [argument.arg for argument in node.args.args]
                self.assertEqual(positional[:12], PAGE_INPUT_ARGUMENTS)


if __name__ == "__main__":
    unittest.main()
