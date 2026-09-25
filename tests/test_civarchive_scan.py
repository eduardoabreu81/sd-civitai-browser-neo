"""The "Also update models missing from CivitAI using CivArchive" scan option.

"Update info & tags" and "Update previews" first run against CivitAI as always;
with the option on, the files CivitAI could not serve (delisted listings, and
files its by-hash lookup answered 404) get a second pass fed by CivArchive.
"""

import io
import json
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(__file__))

from test_civarchive_recovered_html import SHA, _archived_listing, _RecoveredTestCase  # noqa: E402

LIVE_SHA = 'A' * 64


def _response(payload, status=200):
    class _Resp:
        status_code = status
        text = json.dumps(payload)

        def json(self):
            return payload
    return _Resp()


class _ScanTestCase(_RecoveredTestCase):
    def setUp(self):
        super().setUp()
        self._orig_scan = {
            'folders': self.api.contenttype_folders,
            'bulk': self.fm._bulk_fetch_models_by_ids,
            'save_preview': self.fm.save_preview,
            'source': self.fm._browser_sources.get_browser_source,
            'clean': self.fm.clean_description,
        }
        # clean_description() formats HTML through bs4, which the shared stubs replace
        # with a MagicMock; it is not what these tests are about.
        self.fm.clean_description = lambda desc: desc
        self.api.contenttype_folders = lambda ct, desc=None, custom_folder=None: [self.tmp] if ct == 'LORA' else []
        self.hash_lookups = []
        self.archive = {}
        test = self

        class _Archive:
            def get_version_by_hash(self, sha256):
                test.hash_lookups.append(sha256)
                return test.archive.get(sha256)

        self.fm._browser_sources.get_browser_source = lambda name: _Archive()
        self.previews = []
        self.fm.save_preview = lambda fp, resp, overwrite=False, sha256=None: self.previews.append((os.path.basename(fp), resp))
        self.gl.cancel_status = False

    def tearDown(self):
        self.api.contenttype_folders = self._orig_scan['folders']
        self.fm._bulk_fetch_models_by_ids = self._orig_scan['bulk']
        self.fm.save_preview = self._orig_scan['save_preview']
        self.fm._browser_sources.get_browser_source = self._orig_scan['source']
        self.fm.clean_description = self._orig_scan['clean']
        self.fm.from_tag = self.fm.from_preview = False
        super().tearDown()

    def _sidecar(self, name):
        with io.open(os.path.join(self.tmp, name + '.json'), encoding='utf-8') as handle:
            return json.load(handle)

    def _write_model(self, name, sidecar):
        path = os.path.join(self.tmp, name + '.safetensors')
        with io.open(path, 'w', encoding='utf-8') as handle:
            handle.write('')
        self._write(name + '.json', sidecar)
        return path

    def _archive_for(self, sha=SHA):
        listing = _archived_listing(sha)
        listing.pop('source')
        listing.pop('archived_url')
        self.archive[sha] = listing

    def _scan(self, mode, civitai_items, use_civarchive=True, overwrite=False, create_html=False):
        """Run the real file_scan with CivitAI's /models answering civitai_items."""
        self.fm.from_tag = mode == 'tag'
        self.fm.from_preview = mode == 'preview'

        def fake_get(url, *args, **kwargs):
            return _response({'items': civitai_items, 'metadata': {}})

        with patch.object(self.fm.requests, 'get', side_effect=fake_get), \
                patch.object(self.fm.time, 'sleep', lambda s: None):
            return self.fm.file_scan(['LORA'], 0, 0, 0, 0, 0, overwrite, 60, False, create_html,
                                     use_civarchive, progress=None)


class TestOutsideCivitaiFiles(_ScanTestCase):
    def test_missing_ids_are_confirmed_before_counting_as_delisted(self):
        gone = os.path.join(self.tmp, 'gone.safetensors')
        flaky = os.path.join(self.tmp, 'flaky.safetensors')
        live = os.path.join(self.tmp, 'live.safetensors')
        self.fm._bulk_fetch_models_by_ids = lambda ids, **k: ({30: {'id': 30}}, {20})

        outside = self.fm._outside_civitai_files(
            [gone, flaky, live], [10, 20, 30], [], [])

        self.assertEqual(outside, [gone], 'a failed request or a late answer is not a delisting')

    def test_returned_ids_and_404_files(self):
        live = os.path.join(self.tmp, 'live.safetensors')
        never = os.path.join(self.tmp, 'never.safetensors')
        self.fm._bulk_fetch_models_by_ids = lambda ids, **k: self.fail('nothing to re-check')

        outside = self.fm._outside_civitai_files([live], ['30'], [{'id': 30}], [never])

        self.assertEqual(outside, [never])


class TestSidecarFromCivArchive(_ScanTestCase):
    def test_fills_info_and_keeps_civitai_ids(self):
        path = self._write_model('gone', {
            'modelId': 2646164, 'modelVersionId': 2971246, 'sha256': SHA,
            'modelPageURL': 'https://civitai.com/models/2646164?modelVersionId=2971246',
        })

        self.assertTrue(self.fm._save_sidecar_from_civarchive(path, _archived_listing(), True))

        sidecar = self._sidecar('gone')
        self.assertEqual(sidecar['activation text'], 'stepping on face')
        self.assertEqual(sidecar['sd version'], 'Anima')
        self.assertEqual(sidecar['modelTags'], ['concept', 'pose'])
        self.assertIn('Archived description', sidecar['description'])
        self.assertEqual(sidecar['modelId'], 2646164, 'must stay the CivitAI int, not the archive string')
        self.assertEqual(sidecar['modelVersionId'], 2971246)
        self.assertEqual(sidecar['modelPageURL'], 'https://civitai.com/models/2646164?modelVersionId=2971246')
        self.assertEqual(sidecar['resolved_via'], 'civarchive')

    def test_without_overwrite_existing_info_is_kept(self):
        path = self._write_model('gone', {'modelId': 2646164, 'sha256': SHA, 'activation text': 'mine'})
        self.fm._save_sidecar_from_civarchive(path, _archived_listing(), False)
        self.assertEqual(self._sidecar('gone')['activation text'], 'mine')

    def test_no_id_fields_are_invented(self):
        path = self._write_model('never', {'sha256': SHA})
        self.fm._save_sidecar_from_civarchive(path, _archived_listing(), True)
        sidecar = self._sidecar('never')
        for key in ('modelId', 'modelVersionId', 'modelPageURL'):
            self.assertNotIn(key, sidecar)


class TestFileScanTags(_ScanTestCase):
    def _library(self):
        self._write_model('live', {'modelId': 30, 'modelVersionId': 300, 'sha256': LIVE_SHA})
        self._write_model('gone', {'modelId': 2646164, 'modelVersionId': 2971246, 'sha256': SHA})
        self._archive_for()
        self.fm._bulk_fetch_models_by_ids = lambda ids, **k: ({}, set())
        return [{
            'id': 30, 'name': 'Live', 'type': 'LORA', 'description': 'live desc', 'tags': ['style'],
            'modelVersions': [{'id': 300, 'name': 'v1', 'baseModel': 'SDXL 1.0', 'trainedWords': ['livetag'],
                               'files': [{'name': 'live.safetensors', 'hashes': {'SHA256': LIVE_SHA},
                                          'downloadUrl': 'https://civitai.com/api/download/models/300'}]}],
        }]

    def test_delisted_model_gets_the_civarchive_pass(self):
        self._scan('tag', self._library(), overwrite=True)

        self.assertEqual(self._sidecar('gone')['activation text'], 'stepping on face')
        self.assertEqual(self._sidecar('gone')['resolved_via'], 'civarchive')
        self.assertEqual(self._sidecar('live')['activation text'], 'livetag')
        self.assertEqual(self.hash_lookups, [SHA], 'only the file outside CivitAI goes to CivArchive')

    def test_option_off_leaves_delisted_models_alone(self):
        self._scan('tag', self._library(), use_civarchive=False, overwrite=True)

        self.assertNotIn('activation text', self._sidecar('gone'))
        self.assertEqual(self.hash_lookups, [])

    def test_html_is_built_from_the_archive_when_asked(self):
        self._scan('tag', self._library(), overwrite=True, create_html=True)
        self.assertIn('recovered via CivArchive', self._html('gone'))

    def test_all_delisted_selection_no_longer_aborts(self):
        self._write_model('gone', {'modelId': 2646164, 'modelVersionId': 2971246, 'sha256': SHA})
        self._archive_for()
        self.fm._bulk_fetch_models_by_ids = lambda ids, **k: ({}, set())

        self._scan('tag', [], overwrite=True)

        self.assertEqual(self._sidecar('gone')['activation text'], 'stepping on face')

    def test_404_file_is_looked_up_too(self):
        self._write_model('never', {'modelId': 'Model not found', 'modelVersionId': 'Model not found', 'sha256': SHA})
        self._archive_for()

        self._scan('tag', [], overwrite=True)

        sidecar = self._sidecar('never')
        self.assertEqual(sidecar['activation text'], 'stepping on face')
        self.assertEqual(sidecar['modelId'], 'Model not found')

    def test_summary_reports_the_pass(self):
        update = self.fm.gr.update
        update.reset_mock()
        self._write_model('nothing', {'modelId': 55, 'modelVersionId': 550, 'sha256': 'B' * 64})
        library = self._library()

        self._scan('tag', library, overwrite=True)

        values = [c.kwargs['value'] for c in update.call_args_list if 'value' in c.kwargs]
        summary = next(v for v in values if 'outside CivitAI' in str(v))
        self.assertIn('1 updated from CivArchive', summary)
        self.assertIn('1 not found on CivArchive', summary)


class TestFileScanPreviews(_ScanTestCase):
    def test_delisted_preview_comes_from_the_archive(self):
        self._write_model('gone', {'modelId': 2646164, 'modelVersionId': 2971246, 'sha256': SHA})
        self._archive_for()
        self.fm._bulk_fetch_models_by_ids = lambda ids, **k: ({}, set())

        self._scan('preview', [])

        self.assertEqual(len(self.previews), 1)
        name, response = self.previews[0]
        self.assertEqual(name, 'gone.safetensors')
        self.assertEqual(response['items'][0]['browserSource'], 'civarchive')


if __name__ == '__main__':
    unittest.main()
