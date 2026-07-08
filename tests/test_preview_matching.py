"""Isolated tests for preview file matching without importing Forge Neo."""

import ast
from pathlib import Path
import unittest


SOURCE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "civitai_file_manage.py"


def _load_preview_matcher():
    tree = ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_preview_file_matches"
    )
    namespace = {"Path": Path}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(SOURCE_PATH), "exec"), namespace)
    return namespace["_preview_file_matches"]


class TestPreviewFileMatching(unittest.TestCase):
    def setUp(self):
        self.matches = _load_preview_matcher()

    def test_matches_normalized_sha256(self):
        matched, reason = self.matches(
            {"name": "remote.safetensors", "hashes": {"SHA256": "aabbcc"}},
            Path("local.safetensors"),
            " AABBCC ",
        )
        self.assertTrue(matched)
        self.assertEqual(reason, "sha256")

    def test_falls_back_to_exact_filename(self):
        matched, reason = self.matches(
            {"name": "Model.SAFETENSORS", "hashes": {}},
            Path("C:/models/model.safetensors"),
            None,
        )
        self.assertTrue(matched)
        self.assertEqual(reason, "filename")

    def test_rejects_unrelated_file(self):
        self.assertEqual(
            self.matches(
                {"name": "other.safetensors", "hashes": {"SHA256": "deadbeef"}},
                Path("model.safetensors"),
                "aabbcc",
            ),
            (False, None),
        )


if __name__ == "__main__":
    unittest.main()
