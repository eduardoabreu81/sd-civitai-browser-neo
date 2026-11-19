"""Isolated tests for the CivitAI CDN URL used for video previews."""

import ast
from pathlib import Path
import unittest


SOURCE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "civitai_file_manage.py"
BASE = "https://image.civitai.com/xG1nkqKTMzGDvpLrqFT7WA/64f47e69-34d6-4962-8967-3c5d13d12572"


def _load_url_builder():
    tree = ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_video_preview_url"
    )
    namespace = {}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(SOURCE_PATH), "exec"), namespace)
    return namespace["_video_preview_url"]


class TestVideoPreviewUrl(unittest.TestCase):
    def setUp(self):
        self.build = _load_url_builder()

    def test_landscape_scales_by_width(self):
        self.assertEqual(
            self.build(f"{BASE}/original=true/111841900.mp4", 1280, 720, 512),
            f"{BASE}/width=512/111841900.mp4",
        )

    def test_portrait_keeps_longer_side_at_target(self):
        self.assertEqual(
            self.build(f"{BASE}/original=true/1.mp4", 720, 1280, 512),
            f"{BASE}/width=288/1.mp4",
        )

    def test_existing_width_segment_is_replaced(self):
        self.assertEqual(
            self.build(f"{BASE}/width=450/1.mp4", 1280, 720, 512),
            f"{BASE}/width=512/1.mp4",
        )

    def test_small_video_is_not_upscaled(self):
        self.assertEqual(
            self.build(f"{BASE}/width=450/1.mp4", 320, 240, 512),
            f"{BASE}/original=true/1.mp4",
        )

    def test_no_resize_keeps_url(self):
        url = f"{BASE}/original=true/1.mp4"
        self.assertEqual(self.build(url, 1280, 720, None), url)

    def test_unknown_layout_keeps_url(self):
        url = "https://example.com/videos/1.mp4"
        self.assertEqual(self.build(url, 1280, 720, 512), url)

    def test_missing_dimensions_use_target_as_width(self):
        self.assertEqual(
            self.build(f"{BASE}/original=true/1.mp4", None, None, 512),
            f"{BASE}/width=512/1.mp4",
        )


if __name__ == "__main__":
    unittest.main()
