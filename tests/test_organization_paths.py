"""Tests for the Organization tab's model-root resolution.

Regression cover for the report by CivitAI user ODSP1994:

    "I find it works better if the loras aren't in different folders outside the
     categories in the loradex [...] the organization tab didn't really liked
     that until I put them in the main directory"

The old code found a file's model root by walking up until a folder was
*literally* named 'Lora' / 'Stable-diffusion' / 'embeddings' / 'VAE' /
'ControlNet'::

    root_folder = current_dir
    while os.path.basename(root_folder) not in [...]:
        parent = os.path.dirname(root_folder)
        if parent == root_folder:
            root_folder = current_dir   # <-- silent, damaging fallback
            break
        root_folder = parent
    is_lora = os.path.basename(root_folder) == 'Lora'

Two failures fell out of that for anyone whose --lora-dir points somewhere with
a different name:

1. the walk reached the filesystem root, fell back to the file's OWN directory,
   and the organizer then created its Base/Category folders *inside* the user's
   existing subfolders instead of at the library root;
2. ``is_lora`` was an exact, case-sensitive basename compare, so
   "organize LoRAs by category" was silently ignored altogether.

scripts/organization_paths has no gradio/WebUI imports, so it is imported here
directly rather than through the module stubs the other suites need.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.organization_paths import (  # noqa: E402
    CATEGORY_FOLDER_NAMES,
    LORA_CONTENT_TYPES,
    category_from_current_folder,
    resolve_model_root,
)


def _p(*parts):
    """Build an absolute path that is real enough for normcase/normpath."""
    return os.path.abspath(os.path.join(*parts))


class TestResolveModelRoot(unittest.TestCase):
    """resolve_model_root() — which configured root does this file belong to?"""

    def test_file_directly_in_the_root(self):
        root = _p('D:/AI/loras')
        roots = [(root, 'LORA')]
        found, ctype = resolve_model_root(_p(root, 'x.safetensors'), roots)
        self.assertEqual(found, root)
        self.assertEqual(ctype, 'LORA')

    def test_root_not_named_lora_is_still_resolved(self):
        # The whole point: --lora-dir D:/AI/loras used to resolve to nothing.
        root = _p('D:/AI/my-loras-collection')
        roots = [(root, 'LORA')]
        found, ctype = resolve_model_root(_p(root, 'A', 'x.safetensors'), roots)
        self.assertEqual(found, root)
        self.assertEqual(ctype, 'LORA')

    def test_deeply_nested_subfolders_resolve_to_the_root(self):
        # ODSP1994's layout: alphabetical folders inside another folder.
        root = _p('D:/AI/loras')
        roots = [(root, 'LORA')]
        deep = _p(root, 'ill_loras', 'A', 'artist', 'x.safetensors')
        found, _ = resolve_model_root(deep, roots)
        self.assertEqual(
            found, root,
            "nested subfolders must resolve to the library root, "
            "not to the file's own directory")

    def test_longest_match_wins_for_nested_roots(self):
        outer = _p('D:/AI/loras')
        inner = _p('D:/AI/loras/extra')
        roots = [(outer, 'LORA'), (inner, 'LORA')]
        found, _ = resolve_model_root(_p(inner, 'x.safetensors'), roots)
        self.assertEqual(found, inner, 'the most specific configured root wins')

    def test_longest_match_wins_regardless_of_listing_order(self):
        outer = _p('D:/AI/loras')
        inner = _p('D:/AI/loras/extra')
        found, _ = resolve_model_root(_p(inner, 'x.safetensors'),
                                      [(inner, 'LORA'), (outer, 'LORA')])
        self.assertEqual(found, inner)

    def test_sibling_root_with_a_shared_prefix_does_not_match(self):
        # 'D:/AI/loras-old' must not swallow a file under 'D:/AI/loras'.
        roots = [(_p('D:/AI/loras-old'), 'LORA')]
        found, ctype = resolve_model_root(_p('D:/AI/loras/x.safetensors'), roots)
        self.assertIsNone(found)
        self.assertIsNone(ctype)

    def test_file_outside_every_root_returns_none(self):
        roots = [(_p('D:/AI/loras'), 'LORA')]
        found, ctype = resolve_model_root(_p('E:/elsewhere/x.safetensors'), roots)
        self.assertIsNone(found)
        self.assertIsNone(ctype)

    def test_content_type_comes_from_the_root_not_the_folder_name(self):
        # is_lora used to be `basename(root) == 'Lora'`; a correctly configured
        # library called anything else lost category organization entirely.
        roots = [(_p('D:/AI/my-loras'), 'LORA'),
                 (_p('D:/AI/checkpoints'), 'Checkpoint')]
        _, ctype = resolve_model_root(_p('D:/AI/my-loras/x.safetensors'), roots)
        self.assertIn(ctype, LORA_CONTENT_TYPES)
        _, ctype = resolve_model_root(_p('D:/AI/checkpoints/x.safetensors'), roots)
        self.assertNotIn(ctype, LORA_CONTENT_TYPES)

    def test_locon_and_dora_count_as_lora(self):
        self.assertIn('LoCon', LORA_CONTENT_TYPES)
        self.assertIn('DoRA', LORA_CONTENT_TYPES)

    def test_multiple_roots_of_different_types(self):
        lora_root = _p('G:/LORAS')
        ckpt_root = _p('D:/checkpoints')
        roots = [(lora_root, 'LORA'), (ckpt_root, 'Checkpoint')]
        found, ctype = resolve_model_root(_p(ckpt_root, 'SDXL', 'm.safetensors'), roots)
        self.assertEqual(found, ckpt_root)
        self.assertEqual(ctype, 'Checkpoint')

    def test_case_insensitive_match_on_windows(self):
        root = _p('D:/AI/Loras')
        roots = [(root, 'LORA')]
        found, _ = resolve_model_root(_p('D:/AI/loras/x.safetensors'), roots)
        if os.path.normcase('A') == os.path.normcase('a'):
            self.assertEqual(found, root)
        else:
            self.assertIsNone(found, 'case-sensitive filesystems must not match')

    def test_empty_roots_returns_none(self):
        self.assertEqual(resolve_model_root(_p('D:/x.safetensors'), []), (None, None))
        self.assertEqual(resolve_model_root(_p('D:/x.safetensors'), None), (None, None))

    def test_empty_file_path_returns_none(self):
        self.assertEqual(resolve_model_root(None, [(_p('D:/l'), 'LORA')]), (None, None))
        self.assertEqual(resolve_model_root('', [(_p('D:/l'), 'LORA')]), (None, None))

    def test_falsy_root_entries_are_skipped(self):
        root = _p('D:/AI/loras')
        roots = [(None, 'LORA'), ('', 'LORA'), (root, 'LORA')]
        found, _ = resolve_model_root(_p(root, 'x.safetensors'), roots)
        self.assertEqual(found, root)

    def test_returned_root_is_the_caller_supplied_object(self):
        # The caller joins target paths onto this; it must come back unmangled,
        # not as the internal normcase/realpath form used for comparison.
        root = _p('D:/AI/Loras')
        found, _ = resolve_model_root(_p(root, 'x.safetensors'), [(root, 'LORA')])
        self.assertEqual(found, root)


class TestCategoryFromCurrentFolder(unittest.TestCase):
    """category_from_current_folder() — the already-organized safety net.

    The organizer re-runs its heuristic on every scan and stores the result
    nowhere but the folder itself, so a heuristic change would otherwise propose
    moving an already-sorted library back out.
    """

    def test_category_folder_is_recognized(self):
        path = _p('D:/AI/loras/Anima/Slider/x.safetensors')
        self.assertEqual(category_from_current_folder(path), 'Slider')

    def test_base_model_folder_is_not_a_category(self):
        path = _p('D:/AI/loras/Anima/x.safetensors')
        self.assertIsNone(category_from_current_folder(path))

    def test_arbitrary_user_folder_is_not_a_category(self):
        path = _p('D:/AI/loras/ill_loras/A/x.safetensors')
        self.assertIsNone(category_from_current_folder(path))

    def test_library_root_is_not_a_category(self):
        self.assertIsNone(category_from_current_folder(_p('D:/AI/loras/x.safetensors')))

    def test_every_real_category_round_trips(self):
        for category in CATEGORY_FOLDER_NAMES:
            path = _p('D:/AI/loras/Anima', category, 'x.safetensors')
            self.assertEqual(category_from_current_folder(path), category)

    def test_auto_and_none_are_dropdown_states_not_folders(self):
        # LORA_DEX_CATEGORIES includes them; the folder set must not.
        self.assertNotIn('Auto', CATEGORY_FOLDER_NAMES)
        self.assertNotIn('None', CATEGORY_FOLDER_NAMES)

    def test_case_must_match_exactly(self):
        # The organizer only ever creates capitalized folders; a user folder
        # called 'style' is theirs, not ours to reinterpret.
        path = _p('D:/AI/loras/Anima/style/x.safetensors')
        self.assertIsNone(category_from_current_folder(path))


if __name__ == '__main__':
    unittest.main()
