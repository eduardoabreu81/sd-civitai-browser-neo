"""Picking another file must keep the auto-organize base-model subfolder.

update_model_info() routed not-yet-installed models into <type>/<Family>/ when
civitai_neo_auto_organize was on, but update_file_info() only knew the
default-subfolder setting, so changing the selected file moved the install path
back to the type root. Both now share _auto_organize_subfolder().
"""

import os
import tempfile
import unittest
from unittest import mock

from test_civitai_model_ids import _load_civitai_api_with_stubs


_OPTS = ('civitai_neo_auto_organize', 'civitai_neo_wildcard_organize_by_base', 'LORA_default_subfolder')


class _AutoOrganizeCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.api = _load_civitai_api_with_stubs()
        cls.api._file.normalize_base_model = lambda base: {'SDXL 1.0': 'SDXL'}.get(base)

    def tearDown(self):
        for attr in _OPTS:
            if hasattr(self.api.opts, attr):
                delattr(self.api.opts, attr)


class TestAutoOrganizeSubfolder(_AutoOrganizeCase):

    def test_off_returns_none(self):
        self.assertIsNone(self.api._auto_organize_subfolder('LORA', '/m/Lora', 'SDXL 1.0'))

    def test_known_base_model_gets_its_family_folder(self):
        self.api.opts.civitai_neo_auto_organize = True
        self.assertEqual(self.api._auto_organize_subfolder('LORA', '/m/Lora', 'SDXL 1.0'), os.sep + 'SDXL')

    def test_unrecognized_base_model_without_other_folder_stays_in_root(self):
        self.api.opts.civitai_neo_auto_organize = True
        self.assertEqual(self.api._auto_organize_subfolder('LORA', '/m/Lora', 'Mystery'), 'None')

    def test_missing_base_model_falls_back_to_setting(self):
        self.api.opts.civitai_neo_auto_organize = True
        self.assertIsNone(self.api._auto_organize_subfolder('LORA', '/m/Lora', ''))

    def test_wildcards_only_when_their_own_option_is_on(self):
        self.api.opts.civitai_neo_auto_organize = True
        self.assertIsNone(self.api._auto_organize_subfolder('Wildcards', '/m/wildcards', 'SDXL 1.0'))
        self.api.opts.civitai_neo_wildcard_organize_by_base = True
        self.assertEqual(self.api._auto_organize_subfolder('Wildcards', '/m/wildcards', 'SDXL 1.0'), os.sep + 'SDXL')


class TestUpdateFileInfoAutoOrganize(_AutoOrganizeCase):

    def setUp(self):
        self.model_folder = tempfile.mkdtemp()
        self.addCleanup(os.rmdir, self.model_folder)
        file_info = {'name': 'cool.safetensors', 'sizeKB': 1024, 'downloadUrl': 'https://example/dl',
                     'hashes': {'SHA256': 'ab' * 32},
                     'metadata': {'size': 'Full', 'format': 'SafeTensor', 'fp': 'fp16'}}
        version = {'id': 7, 'name': 'v1', 'baseModel': 'SDXL 1.0', 'files': [file_info]}
        self.api_data = {'items': [{'id': 42, 'name': 'Cool', 'type': 'LORA', 'description': '',
                                    'nsfw': False, 'creator': {'username': 'alice'},
                                    'modelVersions': [version]}]}
        self.api.gl.download_queue = []
        self.api._download.convert_size = lambda size: '1 MB'
        self.api._file.convertCustomFolder = lambda folder, *args: folder
        self.api._file._load_sidecar_dict = lambda path: None

    def install_path_and_subfolder(self):
        with mock.patch.object(self.api, 'contenttype_folder', return_value=self.model_folder):
            result = self.api.update_file_info('Cool (42)', 'v1', 'Full SafeTensor fp16 (1 MB)', self.api_data)
        return result[6]['value'], result[7]['value']

    def test_auto_organize_keeps_the_base_model_subfolder(self):
        self.api.opts.civitai_neo_auto_organize = True
        self.api.opts.LORA_default_subfolder = '/ignored'
        path, sub = self.install_path_and_subfolder()
        self.assertEqual(sub, os.sep + 'SDXL')
        self.assertEqual(path, self.model_folder + os.sep + 'SDXL')

    def test_without_auto_organize_the_setting_still_applies(self):
        self.api.opts.LORA_default_subfolder = '/custom'
        path, sub = self.install_path_and_subfolder()
        self.assertEqual(sub, '/custom')
        self.assertEqual(path, self.model_folder + '/custom')


if __name__ == '__main__':
    unittest.main()
