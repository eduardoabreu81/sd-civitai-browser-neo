"""Tests for the three-state loraCategory sidecar contract.

Choosing "None" for a LoRA in LoraDex writes ``loraCategory: null``::

    elif cat.lower() == 'none':
        data['loraCategory'] = None

but the reader collapsed that into the same Python ``None`` as a missing key::

    category = content.get('loraCategory')
    if category is None:
        return None

so an explicit opt-out was indistinguishable from "never set". LoraDex showed
the row as 'Auto' again and re-suggested a category on the next load, while
analyze_organization_plan read the very same file as "do not categorize" — the
two halves of the feature disagreed about one file on disk.

civitai_file_manage imports gradio and modules.shared, neither of which exists
outside Forge, so the reader is mirrored here against a real temp tree and
test_shipped_reader_distinguishes_missing_from_null reads the shipped source to
make sure this local mirror cannot drift away from it unnoticed.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

_SCRIPTS = os.path.join(os.path.dirname(__file__), '..', 'scripts')


def _safe_json_load(file_path):
    """Mirror of civitai_api.safe_json_load, guarded the same way."""
    try:
        with open(file_path, 'r', encoding='utf-8') as handle:
            return json.load(handle)
    except Exception:
        return None


def get_lora_category_from_sidecar(file_path):
    """Mirror of civitai_file_manage.get_lora_category_from_sidecar."""
    json_file = os.path.splitext(file_path)[0] + '.json'
    if not os.path.exists(json_file):
        return None
    try:
        content = _safe_json_load(json_file) or {}
        if 'loraCategory' not in content:
            return None
        category = content.get('loraCategory')
        if category is None:
            return 'None'
        return str(category).strip()
    except Exception:
        return None


class TestLoraCategorySidecar(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _model(self, name, sidecar=None):
        """Create a fake model file, optionally with a .json sidecar."""
        model_path = os.path.join(self.tmp, name + '.safetensors')
        with open(model_path, 'w', encoding='utf-8') as handle:
            handle.write('')
        if sidecar is not None:
            with open(os.path.join(self.tmp, name + '.json'), 'w', encoding='utf-8') as handle:
                json.dump(sidecar, handle)
        return model_path

    def test_no_sidecar_at_all(self):
        self.assertIsNone(get_lora_category_from_sidecar(self._model('a')))

    def test_sidecar_without_the_key(self):
        path = self._model('b', {'sha256': 'ABC', 'modelId': 1})
        self.assertIsNone(get_lora_category_from_sidecar(path))

    def test_explicit_null_reads_back_as_the_string_none(self):
        # The regression: this used to be indistinguishable from "unset".
        path = self._model('c', {'loraCategory': None})
        self.assertEqual(get_lora_category_from_sidecar(path), 'None')

    def test_a_real_category_round_trips(self):
        path = self._model('d', {'loraCategory': 'Style'})
        self.assertEqual(get_lora_category_from_sidecar(path), 'Style')

    def test_auto_round_trips(self):
        path = self._model('e', {'loraCategory': 'Auto'})
        self.assertEqual(get_lora_category_from_sidecar(path), 'Auto')

    def test_surrounding_whitespace_is_stripped(self):
        path = self._model('f', {'loraCategory': '  Style  '})
        self.assertEqual(get_lora_category_from_sidecar(path), 'Style')

    def test_malformed_sidecar_is_not_fatal(self):
        model_path = os.path.join(self.tmp, 'g.safetensors')
        with open(model_path, 'w', encoding='utf-8') as handle:
            handle.write('')
        with open(os.path.join(self.tmp, 'g.json'), 'w', encoding='utf-8') as handle:
            handle.write('{not json')
        self.assertIsNone(get_lora_category_from_sidecar(model_path))

    def test_non_dict_sidecar_is_not_fatal(self):
        # Wildcard lists and other extensions' data files live under the model
        # roots too — see test_sidecar_walk_safety.
        model_path = os.path.join(self.tmp, 'h.safetensors')
        with open(model_path, 'w', encoding='utf-8') as handle:
            handle.write('')
        with open(os.path.join(self.tmp, 'h.json'), 'w', encoding='utf-8') as handle:
            json.dump(['a', 'b'], handle)
        self.assertIsNone(get_lora_category_from_sidecar(model_path))

    def test_the_opt_out_survives_a_round_trip_through_the_writer(self):
        # _save_lora_category's rules, applied for real: 'None' -> null.
        path = self._model('i', {'loraCategory': 'Style'})
        sidecar = os.path.join(self.tmp, 'i.json')
        data = _safe_json_load(sidecar)
        data['loraCategory'] = None            # what choosing 'None' writes
        with open(sidecar, 'w', encoding='utf-8') as handle:
            json.dump(data, handle)
        self.assertEqual(get_lora_category_from_sidecar(path), 'None')

    def test_auto_removes_the_key_and_reads_back_as_unset(self):
        path = self._model('j', {'loraCategory': 'Style'})
        sidecar = os.path.join(self.tmp, 'j.json')
        data = _safe_json_load(sidecar)
        data.pop('loraCategory', None)         # what choosing 'Auto' writes
        with open(sidecar, 'w', encoding='utf-8') as handle:
            json.dump(data, handle)
        self.assertIsNone(get_lora_category_from_sidecar(path))

    def test_shipped_reader_distinguishes_missing_from_null(self):
        """The mirror above must not drift from the shipped implementation."""
        source_path = os.path.join(_SCRIPTS, 'civitai_file_manage.py')
        with open(source_path, 'r', encoding='utf-8') as handle:
            source = handle.read()

        start = source.index('def get_lora_category_from_sidecar(')
        end = source.index('\ndef ', start + 1)
        body = source[start:end]

        self.assertIn("if 'loraCategory' not in content:", body,
                      'the shipped reader must test for the key, not just its value')
        self.assertIn("return 'None'", body,
                      'an explicit null must read back as the string None')

    def test_shipped_consumers_treat_none_as_a_state_not_a_category(self):
        """'None' must never be rendered as a category badge."""
        source_path = os.path.join(_SCRIPTS, 'civitai_file_manage.py')
        with open(source_path, 'r', encoding='utf-8') as handle:
            source = handle.read()
        self.assertIn("not in ('auto', 'none')", source,
                      'build_native_card_badge_map must filter out the opt-out state')


if __name__ == '__main__':
    unittest.main()
