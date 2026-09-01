"""Tests for fetching and persisting CivitAI's model-level tags.

Tags are the strongest signal the LoraDex heuristic has — weighted above file
names and descriptions — but almost nothing was writing them:

  - the by-hash endpoint that fills .api_info.json returns a model *version*,
    which carries no tags at all. civitai_file_manage already knew this:
    "If the API response no longer carries tags (e.g. by-hash fallback), keep
    the existing stored tags rather than deleting them."
  - save_model_info() does write modelTags, but only when the Browser's
    "Save info after download" checkbox is on. With it off, info_to_json() still
    created the sidecar, carrying just modelId and sha256.

So a library could easily hold thousands of LoRAs with no tags, leaving the
classifier to guess from filenames and prose — the low-confidence sources.

These mirror the two pure helpers (civitai_download._model_tags_from_response
and civitai_file_manage._normalize_tag_list) because both modules import gradio
and modules.shared, which do not exist outside Forge. The test_shipped_* cases
read the shipped source so the mirrors cannot drift unnoticed.
"""

import io
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

_SCRIPTS = os.path.join(os.path.dirname(__file__), '..', 'scripts')


def _normalize_tag_list(tags):
    """Mirror of civitai_file_manage._normalize_tag_list."""
    if isinstance(tags, list):
        return [str(t).strip() for t in tags if str(t).strip()]
    if isinstance(tags, str):
        return [t.strip() for t in tags.split(',') if t.strip()]
    return []


def _model_tags_from_response(model_json):
    """Mirror of civitai_download._model_tags_from_response."""
    if not isinstance(model_json, dict):
        return []
    items = model_json.get('items')
    if not isinstance(items, list) or not items:
        return []
    first = items[0]
    if not isinstance(first, dict):
        return []
    tags = first.get('tags')
    if isinstance(tags, list):
        return [str(t).strip() for t in tags if str(t).strip()]
    if isinstance(tags, str):
        return [t.strip() for t in tags.split(',') if t.strip()]
    return []


class TestTagsFromDownloadResponse(unittest.TestCase):
    """The download already holds the model payload — no extra request needed."""

    def test_tags_are_read_from_the_first_item(self):
        payload = {'items': [{'id': 1, 'name': 'X', 'tags': ['style', 'anime']}]}
        self.assertEqual(_model_tags_from_response(payload), ['style', 'anime'])

    def test_tags_are_on_the_model_not_the_version(self):
        # The shape the by-hash endpoint returns: a version, with no tags.
        version_payload = {'id': 9, 'baseModel': 'Illustrious', 'model': {'name': 'X'}}
        self.assertEqual(_model_tags_from_response(version_payload), [])

    def test_comma_separated_string_is_split(self):
        payload = {'items': [{'tags': 'style, anime , concept'}]}
        self.assertEqual(_model_tags_from_response(payload), ['style', 'anime', 'concept'])

    def test_blank_and_whitespace_tags_are_dropped(self):
        payload = {'items': [{'tags': ['style', '', '   ', 'anime']}]}
        self.assertEqual(_model_tags_from_response(payload), ['style', 'anime'])

    def test_non_string_tags_are_coerced(self):
        payload = {'items': [{'tags': ['style', 123]}]}
        self.assertEqual(_model_tags_from_response(payload), ['style', '123'])

    def test_missing_tags_key(self):
        self.assertEqual(_model_tags_from_response({'items': [{'id': 1}]}), [])

    def test_empty_items_list(self):
        self.assertEqual(_model_tags_from_response({'items': []}), [])

    def test_items_is_not_a_list(self):
        self.assertEqual(_model_tags_from_response({'items': 'nope'}), [])

    def test_first_item_is_not_a_dict(self):
        self.assertEqual(_model_tags_from_response({'items': ['nope']}), [])

    def test_none_and_junk_payloads(self):
        for payload in (None, [], 'string', 42, {}):
            with self.subTest(payload=payload):
                self.assertEqual(_model_tags_from_response(payload), [])


class TestNormalizeTagList(unittest.TestCase):
    def test_list_input(self):
        self.assertEqual(_normalize_tag_list([' style ', 'anime']), ['style', 'anime'])

    def test_string_input(self):
        self.assertEqual(_normalize_tag_list('style, anime'), ['style', 'anime'])

    def test_none_and_junk(self):
        for value in (None, 42, {}, []):
            with self.subTest(value=value):
                self.assertEqual(_normalize_tag_list(value), [])


class TestSidecarTagPersistence(unittest.TestCase):
    """info_to_json's rule: fill the gap, never clobber what is already there."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, name, payload):
        path = os.path.join(self.tmp, name + '.json')
        with io.open(path, 'w', encoding='utf-8') as handle:
            json.dump(payload, handle)
        return path

    def _apply(self, sidecar_path, model_json):
        """The modelTags half of info_to_json."""
        with io.open(sidecar_path, encoding='utf-8') as handle:
            data = json.load(handle)
        if not data.get('modelTags'):
            tags = _model_tags_from_response(model_json)
            if tags:
                data['modelTags'] = tags
        with io.open(sidecar_path, 'w', encoding='utf-8') as handle:
            json.dump(data, handle)
        return data

    def test_tags_are_added_to_a_bare_sidecar(self):
        # The exact gap: "Save info after download" off, so the sidecar holds
        # only what info_to_json wrote.
        path = self._write('a', {'modelId': 1, 'sha256': 'ABC'})
        data = self._apply(path, {'items': [{'tags': ['style']}]})
        self.assertEqual(data['modelTags'], ['style'])

    def test_existing_tags_are_not_overwritten(self):
        path = self._write('b', {'modelId': 1, 'modelTags': ['curated', 'by-user']})
        data = self._apply(path, {'items': [{'tags': ['style']}]})
        self.assertEqual(data['modelTags'], ['curated', 'by-user'])

    def test_empty_existing_tags_are_replaced(self):
        path = self._write('c', {'modelId': 1, 'modelTags': []})
        data = self._apply(path, {'items': [{'tags': ['style']}]})
        self.assertEqual(data['modelTags'], ['style'])

    def test_a_response_with_no_tags_leaves_the_sidecar_alone(self):
        path = self._write('d', {'modelId': 1, 'sha256': 'ABC'})
        data = self._apply(path, {'items': [{'id': 1}]})
        self.assertNotIn('modelTags', data)

    def test_other_sidecar_fields_survive(self):
        path = self._write('e', {'modelId': 7, 'sha256': 'ABC', 'loraCategory': 'Style'})
        data = self._apply(path, {'items': [{'tags': ['anime']}]})
        self.assertEqual(data['modelId'], 7)
        self.assertEqual(data['sha256'], 'ABC')
        self.assertEqual(data['loraCategory'], 'Style')
        self.assertEqual(data['modelTags'], ['anime'])


class TestShippedImplementation(unittest.TestCase):
    """Keep the mirrors above honest."""

    def setUp(self):
        with io.open(os.path.join(_SCRIPTS, 'civitai_download.py'), encoding='utf-8') as h:
            self.download = h.read()
        with io.open(os.path.join(_SCRIPTS, 'civitai_file_manage.py'), encoding='utf-8') as h:
            self.file_manage = h.read()

    def test_info_to_json_accepts_the_model_payload(self):
        self.assertIn('def info_to_json(install_path, model_id, model_sha256, unpackList=None, model_json=None)',
                      self.download)

    def test_info_to_json_does_not_clobber_existing_tags(self):
        start = self.download.index('def info_to_json(')
        end = self.download.index('\ndef ', start + 1)
        body = self.download[start:end]
        self.assertIn("if not data.get('modelTags'):", body,
                      'existing tags must never be overwritten by the download')

    def test_the_caller_passes_the_payload_through(self):
        self.assertIn("model_json=item.get('model_json')", self.download,
                      'the download already holds the model payload; it must be forwarded')

    def test_fetch_groups_requests_by_model_id(self):
        start = self.file_manage.index('def fetch_official_tags(')
        end = self.file_manage.index('\ndef ', start + 1)
        body = self.file_manage[start:end]
        self.assertIn('targets.setdefault(model_id, [])', body,
                      'one request per unique model id, not per file')

    def test_fetch_skips_files_without_a_cached_model_id(self):
        start = self.file_manage.index('def fetch_official_tags(')
        end = self.file_manage.index('\ndef ', start + 1)
        body = self.file_manage[start:end]
        self.assertIn('no_model_id', body)

    def test_civarchive_is_the_fallback_for_delisted_models(self):
        start = self.file_manage.index('def _fetch_tags_for_model_id(')
        end = self.file_manage.index('\ndef ', start + 1)
        body = self.file_manage[start:end]
        self.assertIn("data == 'not_found'", body,
                      'CivArchive should only be tried for a genuinely delisted listing')
        self.assertIn('get_model', body)

    def test_transient_api_errors_do_not_trigger_civarchive(self):
        start = self.file_manage.index('def _fetch_tags_for_model_id(')
        end = self.file_manage.index('\ndef ', start + 1)
        body = self.file_manage[start:end]
        # 'error'/'offline' mean try again later, not "this model is gone".
        self.assertNotIn("data in ('not_found', 'error')", body)

    def test_cancellation_clears_its_own_flag(self):
        start = self.file_manage.index('def fetch_official_tags(')
        end = self.file_manage.index('\ndef ', start + 1)
        body = self.file_manage[start:end]
        self.assertIn('gl.cancel_status = False', body,
                      'a cancelled run must not leave the flag set for the next one')


if __name__ == '__main__':
    unittest.main()
