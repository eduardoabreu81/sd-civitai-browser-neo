"""Changing the selected file must not leave {BASEMODEL} etc. in the install path.

update_file_info() used to append the raw default-subfolder setting, while
update_model_info() ran it through convertCustomFolder. Both now resolve the
placeholders the same way via _converted_default_subfolder().
"""

import ast
import io
import os
import types
import unittest

from test_civitai_model_ids import _load_civitai_api_with_stubs


def _load_convert_custom_folder(api):
    """civitai_file_manage needs Forge to import, so load just this function."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with io.open(os.path.join(root, 'scripts', 'civitai_file_manage.py'), encoding='utf-8') as handle:
        source = handle.read()
    node = next(n for n in ast.parse(source).body
                if isinstance(n, ast.FunctionDef) and n.name == 'convertCustomFolder')
    namespace = {'os': os, '_api': api}
    exec(compile(ast.Module(body=[node], type_ignores=[]), 'civitai_file_manage.py', 'exec'), namespace)
    return namespace['convertCustomFolder']


class TestConvertedDefaultSubfolder(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.api = _load_civitai_api_with_stubs()
        cls.api._file.convertCustomFolder = _load_convert_custom_folder(cls.api)

    def setUp(self):
        self.item = {'id': 42, 'name': 'Model', 'type': 'LORA', 'nsfw': False,
                     'creator': {'username': 'alice'}}
        self.version = {'id': 7, 'name': 'v1', 'baseModel': 'SDXL 1.0'}

    def tearDown(self):
        if hasattr(self.api.opts, 'LORA_default_subfolder'):
            del self.api.opts.LORA_default_subfolder

    def resolve(self):
        return self.api._converted_default_subfolder('LORA', None, self.item, self.version)

    def test_placeholders_are_replaced(self):
        self.api.opts.LORA_default_subfolder = '/{BASEMODEL}/{AUTHOR}'
        self.assertEqual(self.resolve(), os.sep + os.path.join('SDXL 1.0', 'alice'))

    def test_none_setting_stays_none(self):
        self.assertEqual(self.resolve(), 'None')

    def test_missing_creator_uses_the_same_fallback_as_update_model_info(self):
        self.api.opts.LORA_default_subfolder = '/{AUTHOR}'
        self.item['creator'] = None
        self.assertEqual(self.resolve(), os.sep + 'User not found')


if __name__ == '__main__':
    unittest.main()
