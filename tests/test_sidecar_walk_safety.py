"""Regression tests for issue #4 — "Download all selected" aborted with
`AttributeError: 'list' object has no attribute 'get'`.

The model-folder walks in civitai_file_manage visit EVERY .json under the model
roots, not just the sidecars this extension writes. Dynamic Prompts wildcard
lists, other extensions' data files and hand-written notes live there too, and a
JSON file is allowed to hold an array, a string or a number at its top level.

`safe_json_load` returns whatever the file holds, and the old guard (`if not
data`) only filtered None / [] / {}. A single non-empty, non-dict .json anywhere
under the model tree therefore crashed the whole batch download.

Both civitai_file_manage and civitai_api import gradio, which is not installed
outside Forge, so these tests exercise the loader's contract against a real temp
tree instead of importing the modules. test_shipped_walkers_use_the_guarded_loader
reads the shipped source directly, so this local mirror cannot drift unnoticed.
"""

import json
import os
import sys
import tempfile
import shutil
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def safe_json_load(file_path):
    """Mirror of civitai_api.safe_json_load (which cannot be imported without gradio)."""
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def _load_sidecar_dict(json_path):
    """Mirror of civitai_file_manage._load_sidecar_dict."""
    data = safe_json_load(json_path)
    return data if isinstance(data, dict) else None


class TestSidecarWalkSafety(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, name, payload):
        path = os.path.join(self.tmp, name)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(payload, f)
        return path

    # --- the shapes that used to crash -------------------------------------

    def test_top_level_array_is_skipped_not_crashed(self):
        # A Dynamic Prompts wildcard file living under models/ or the wildcards folder.
        path = self._write('hair_colors.json', ['red hair', 'blue hair'])
        self.assertIsNone(_load_sidecar_dict(path))

    def test_top_level_string_is_skipped(self):
        path = self._write('note.json', 'just a note')
        self.assertIsNone(_load_sidecar_dict(path))

    def test_top_level_number_is_skipped(self):
        path = self._write('count.json', 42)
        self.assertIsNone(_load_sidecar_dict(path))

    def test_top_level_bool_is_skipped(self):
        path = self._write('flag.json', True)
        self.assertIsNone(_load_sidecar_dict(path))

    # --- shapes that were already handled, and must stay handled -----------

    def test_empty_array_is_skipped(self):
        self.assertIsNone(_load_sidecar_dict(self._write('empty.json', [])))

    def test_null_is_skipped(self):
        self.assertIsNone(_load_sidecar_dict(self._write('null.json', None)))

    def test_missing_file_is_skipped(self):
        self.assertIsNone(_load_sidecar_dict(os.path.join(self.tmp, 'nope.json')))

    def test_malformed_json_is_skipped(self):
        path = os.path.join(self.tmp, 'broken.json')
        with open(path, 'w', encoding='utf-8') as f:
            f.write('{"sha256": ')
        self.assertIsNone(_load_sidecar_dict(path))

    # --- real sidecars still load ------------------------------------------

    def test_real_sidecar_is_returned(self):
        payload = {'sha256': 'ABC123', 'modelId': 42, 'modelVersionId': 99}
        path = self._write('model.json', payload)
        self.assertEqual(_load_sidecar_dict(path), payload)

    def test_empty_dict_is_falsy_but_not_an_error(self):
        # `if not data: continue` in the walkers still skips it; the point is that
        # it must not raise.
        self.assertEqual(_load_sidecar_dict(self._write('empty_obj.json', {})), {})

    def test_api_info_blob_is_returned(self):
        payload = {'id': 7, 'model': {'id': 42}, 'files': [{'hashes': {'SHA256': 'DEF'}}]}
        path = self._write('model.api_info.json', payload)
        self.assertEqual(_load_sidecar_dict(path), payload)

    # --- the walkers' consumption pattern must survive a mixed folder ------

    def test_mixed_folder_yields_only_real_sidecars(self):
        """What build_installed_index does: read every .json, keep the sidecars."""
        self._write('wildcards.json', ['a', 'b'])
        self._write('notes.json', 'text')
        self._write('lora_a.json', {'sha256': 'aaa', 'modelId': 1})
        self._write('lora_b.json', {'sha256': 'bbb', 'modelId': 2})

        hashes = set()
        for name in sorted(os.listdir(self.tmp)):
            if not name.endswith('.json'):
                continue
            data = _load_sidecar_dict(os.path.join(self.tmp, name))
            if not data:
                continue
            sha = data.get('sha256') or ''      # the line that used to raise
            if sha:
                hashes.add(sha.upper())

        self.assertEqual(hashes, {'AAA', 'BBB'})

    # --- guard against the shipped implementation drifting ------------------

    def test_shipped_walkers_use_the_guarded_loader(self):
        """The three model-tree walkers must not call safe_json_load directly.

        _find_model_by_sha256, build_installed_index and find_installed_file_by_model_id
        all walk arbitrary .json files; each one that bypasses _load_sidecar_dict is a
        reintroduction of issue #4.
        """
        src_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'civitai_file_manage.py')
        with open(src_path, encoding='utf-8') as f:
            src = f.read()

        self.assertIn('def _load_sidecar_dict(', src,
                      'the guarded sidecar loader is gone')
        self.assertIn('data = _load_sidecar_dict(os.path.join(root, file))', src,
                      'a model-tree walk stopped using _load_sidecar_dict')
        self.assertEqual(
            src.count('data = _load_sidecar_dict(os.path.join(root, file))'), 2,
            'expected both build_installed_index and find_installed_file_by_model_id '
            'to load sidecars through the guarded helper')
        self.assertIn('if not isinstance(data, dict):', src,
                      '_sidecar_matches lost its dict guard')


if __name__ == '__main__':
    unittest.main()
