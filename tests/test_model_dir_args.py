"""Tests for Forge Neo's multi-directory model arguments.

Forge Neo declares its directory overrides with argparse ``action="append"``
(``modules/cmd_args.py``)::

    parser.add_argument("--ckpt-dirs", type=normalized_filepath, action="append", default=[])
    parser.add_argument("--lora-dirs", ...)
    parser.add_argument("--vae-dirs",  ...)

so ``cmd_opts.lora_dirs`` is a **list**, not a string. Two consequences the code
has to handle:

1. ``Path(['G:/LORAS'])`` raises ``TypeError`` — passing the list straight through
   made ``--ckpt-dirs`` crash folder resolution outright.
2. ``--lora-dir`` (singular) is declared by Neo's built-in ``sd_forge_lora`` with a
   non-empty default of ``models/Lora``, so it is *always* truthy and would always
   win the lookup, silently ignoring ``--lora-dirs``.

And because Forge scans ``[lora_dir, *lora_dirs]`` rather than just one of them,
anything that reads the library has to see every configured folder, or models in
the extra directories look uninstalled.
"""

import unittest
from pathlib import Path

from test_civitai_model_ids import _load_civitai_api_with_stubs


class _DirArgsTestCase(unittest.TestCase):
    """Loads civitai_api with stubbed Forge modules and a controllable cmd_opts."""

    @classmethod
    def setUpClass(cls):
        cls.api = _load_civitai_api_with_stubs()

    def setUp(self):
        # Reset to a bare Forge Neo launch: append-lists empty, singular lora_dir
        # present with its built-in default, no ckpt_dir / vae_dir attributes at all
        # (Neo does not declare those).
        for attr in ('ckpt_dir', 'vae_dir'):
            if hasattr(self.api.cmd_opts, attr):
                delattr(self.api.cmd_opts, attr)
        self.api.cmd_opts.lora_dir = 'models/Lora'
        self.api.cmd_opts.lora_dirs = []
        self.api.cmd_opts.ckpt_dirs = []
        self.api.cmd_opts.vae_dirs = []


class TestContentTypeFolder(_DirArgsTestCase):
    """contenttype_folder() — the single download destination."""

    def test_ckpt_dirs_list_does_not_raise(self):
        self.api.cmd_opts.ckpt_dirs = ['D:/checkpoints']
        folder = self.api.contenttype_folder('Checkpoint')
        self.assertEqual(folder, Path('D:/checkpoints'))

    def test_lora_dirs_beats_the_defaulted_singular_flag(self):
        self.api.cmd_opts.lora_dirs = ['G:/LORAS']
        self.assertEqual(self.api.contenttype_folder('LORA'), Path('G:/LORAS'))

    def test_vae_dirs_is_honoured(self):
        self.api.cmd_opts.vae_dirs = ['E:/vaes']
        self.assertEqual(self.api.contenttype_folder('VAE'), Path('E:/vaes'))

    def test_locon_and_dora_follow_lora_dirs(self):
        self.api.cmd_opts.lora_dirs = ['G:/LORAS']
        self.assertEqual(self.api.contenttype_folder('LoCon'), Path('G:/LORAS'))
        self.assertEqual(self.api.contenttype_folder('DoRA'), Path('G:/LORAS'))

    def test_empty_append_lists_fall_through_to_the_default(self):
        # argparse default is [], which is falsy — unset flags must not change anything.
        self.assertEqual(self.api.contenttype_folder('LORA'), Path('models/Lora'))

    def test_first_entry_wins_as_the_download_destination(self):
        self.api.cmd_opts.lora_dirs = ['G:/LORAS', 'H:/more-loras']
        self.assertEqual(self.api.contenttype_folder('LORA'), Path('G:/LORAS'))

    def test_plain_string_attribute_still_works(self):
        # A1111 / Forge Classic pass strings, not lists.
        self.api.cmd_opts.ckpt_dir = 'C:/a1111/models/Stable-diffusion'
        self.assertEqual(self.api.contenttype_folder('Checkpoint'),
                         Path('C:/a1111/models/Stable-diffusion'))


class TestContentTypeFolders(_DirArgsTestCase):
    """contenttype_folders() — every folder to READ from."""

    def test_returns_a_single_folder_when_no_extra_dirs(self):
        self.assertEqual(self.api.contenttype_folders('LORA'), [Path('models/Lora')])

    def test_includes_both_the_extra_dir_and_the_default(self):
        self.api.cmd_opts.lora_dirs = ['G:/LORAS']
        folders = self.api.contenttype_folders('LORA')
        self.assertEqual(folders[0], Path('G:/LORAS'), 'download destination comes first')
        self.assertIn(Path('models/Lora'), folders,
                      'the default folder must stay visible to scans')

    def test_every_appended_dir_is_returned(self):
        self.api.cmd_opts.lora_dirs = ['G:/LORAS', 'H:/more-loras']
        folders = self.api.contenttype_folders('LORA')
        self.assertIn(Path('G:/LORAS'), folders)
        self.assertIn(Path('H:/more-loras'), folders)
        self.assertIn(Path('models/Lora'), folders)

    def test_checkpoint_dirs_are_all_returned(self):
        self.api.cmd_opts.ckpt_dirs = ['D:/ckpt-a', 'E:/ckpt-b']
        folders = self.api.contenttype_folders('Checkpoint')
        self.assertIn(Path('D:/ckpt-a'), folders)
        self.assertIn(Path('E:/ckpt-b'), folders)

    def test_vae_dirs_are_all_returned(self):
        self.api.cmd_opts.vae_dirs = ['E:/vaes']
        folders = self.api.contenttype_folders('VAE')
        self.assertIn(Path('E:/vaes'), folders)

    def test_no_duplicates_when_the_flag_repeats_the_default(self):
        self.api.cmd_opts.lora_dirs = ['models/Lora']
        self.assertEqual(self.api.contenttype_folders('LORA'), [Path('models/Lora')])

    def test_content_type_without_multi_dir_support_returns_one_folder(self):
        folders = self.api.contenttype_folders('Workflows')
        self.assertEqual(len(folders), 1)

    def test_custom_folder_is_not_widened(self):
        # An explicit custom folder is a deliberate override — cmd_opts must not
        # add anything to it.
        self.api.cmd_opts.lora_dirs = ['G:/LORAS']
        folders = self.api.contenttype_folders('LORA', custom_folder='X:/custom')
        self.assertEqual(len(folders), 1)
        self.assertNotIn(Path('G:/LORAS'), folders)

    def test_unknown_content_type_returns_empty(self):
        self.assertEqual(self.api.contenttype_folders('NotAThing'), [])


if __name__ == '__main__':
    unittest.main()
