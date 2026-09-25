"""Integration tests for resolve_metadata_issues against the real shipped code.

Each issue kind must go to the right source:
  - orphaned (removed from CivitAI) → CivArchive, by SHA256.
  - corrupted (still on CivitAI, .api_info.json holds another model) → CivitAI,
    by the sidecar's modelVersionId. by-hash is what produced the mismatch, so
    it must not be used again here.

Both paths cross-check the returned modelId against the sidecar before writing.
Network is stubbed at _api.request_civit_api and at the CivArchive adapter.
"""

import io
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from test_official_tags_integration import _install_stubs  # noqa: E402


class _ResolveTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._saved_modules = dict(sys.modules)
        for name in [n for n in sys.modules if n == 'scripts' or n.startswith('scripts.')]:
            del sys.modules[name]
        _install_stubs()
        import scripts.civitai_file_manage as fm
        import scripts.civitai_api as api
        import scripts.civitai_global as gl
        cls.fm = fm
        cls.api = api
        cls.gl = gl

    @classmethod
    def tearDownClass(cls):
        sys.modules.clear()
        sys.modules.update(cls._saved_modules)

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.gl.cancel_status = False
        self._orig_request = self.api.request_civit_api
        self._orig_source = self.fm._browser_sources.get_browser_source
        self.requested = []
        self.hash_lookups = []
        self.api.request_civit_api = self._fake_request
        self.civitai = {}
        self.archive = {}

        test = self

        class _FakeArchive:
            def get_version_by_hash(self, sha256):
                test.hash_lookups.append(sha256)
                return test.archive.get(sha256)

        self.fm._browser_sources.get_browser_source = lambda name: _FakeArchive()

    def tearDown(self):
        self.api.request_civit_api = self._orig_request
        self.fm._browser_sources.get_browser_source = self._orig_source
        self.gl.cancel_status = False
        shutil.rmtree(self.tmp, ignore_errors=True)

    # -- helpers ---------------------------------------------------------

    def _fake_request(self, api_url=None, skip_error_check=False):
        self.requested.append(api_url)
        return self.civitai.get(api_url, 'not_found')

    def _version_url(self, version_id):
        return f"https://{self.api.get_civitai_domain()}/api/v1/model-versions/{version_id}"

    def _model(self, name, sidecar, api_info=None):
        path = os.path.join(self.tmp, name + '.safetensors')
        with io.open(path, 'w', encoding='utf-8') as handle:
            handle.write('')
        self._write(name + '.json', sidecar)
        if api_info is not None:
            self._write(name + '.api_info.json', api_info)
        return path

    def _write(self, file_name, data):
        with io.open(os.path.join(self.tmp, file_name), 'w', encoding='utf-8') as handle:
            json.dump(data, handle)

    def _read(self, file_name):
        path = os.path.join(self.tmp, file_name)
        if not os.path.exists(path):
            return None
        with io.open(path, encoding='utf-8') as handle:
            return json.load(handle)

    def _run(self, orphaned=(), corrupted=()):
        issues = json.dumps({'orphaned': list(orphaned), 'corrupted': list(corrupted)})
        return list(self.fm.resolve_metadata_issues(issues, progress=None))

    @staticmethod
    def _issue(path, model_id, sha256='AAAA'):
        return {'file_path': path, 'sha256': sha256, 'model_id': model_id,
                'model_name': os.path.basename(path)}


class TestOrphanedGoesToCivArchive(_ResolveTestCase):
    def test_orphan_is_recovered_from_civarchive(self):
        path = self._model('gone', {'modelId': 10, 'modelVersionId': 100, 'sha256': 'AAAA'})
        self.archive['AAAA'] = {'id': '10', 'name': 'Gone', 'browserSourceUrl': 'https://civarchive.com/models/10'}

        self._run(orphaned=[self._issue(path, 10)])

        api_info = self._read('gone.api_info.json')
        self.assertEqual(api_info['source'], 'civarchive')
        self.assertEqual(api_info['archived_url'], 'https://civarchive.com/models/10')
        sidecar = self._read('gone.json')
        self.assertEqual(sidecar['resolved_via'], 'civarchive')
        self.assertEqual(sidecar['modelId'], 10, 'existing sidecar fields must be preserved')
        self.assertEqual(self.requested, [], 'an orphan must not be asked of CivitAI')

    def test_civarchive_hit_for_another_model_is_rejected(self):
        path = self._model('gone', {'modelId': 10, 'sha256': 'AAAA'})
        self.archive['AAAA'] = {'id': '99', 'name': 'Someone else'}

        self._run(orphaned=[self._issue(path, 10)])

        self.assertIsNone(self._read('gone.api_info.json'))
        self.assertNotIn('resolved_via', self._read('gone.json'))

    def test_civarchive_miss_leaves_files_untouched(self):
        original = {'modelId': 10, 'sha256': 'AAAA'}
        path = self._model('gone', original)

        self._run(orphaned=[self._issue(path, 10)])

        self.assertIsNone(self._read('gone.api_info.json'))
        self.assertEqual(self._read('gone.json'), original)


class TestCorruptedGoesToCivitAI(_ResolveTestCase):
    def test_mismatch_is_repaired_from_civitai_by_version_id(self):
        path = self._model('live', {'modelId': 10, 'modelVersionId': 100, 'sd version': 'Wrong'},
                           api_info={'modelId': 99, 'baseModel': 'Wrong'})
        self.civitai[self._version_url(100)] = {'id': 100, 'modelId': 10, 'baseModel': 'Illustrious'}

        self._run(corrupted=[self._issue(path, 10)])

        self.assertEqual(self._read('live.api_info.json')['modelId'], 10)
        self.assertEqual(self._read('live.json')['sd version'], 'Illustrious',
                         'the sidecar baseModel the collision overwrote must be re-patched')
        self.assertEqual(self.requested, [self._version_url(100)])
        self.assertEqual(self.hash_lookups, [], 'a live model must not be sent to CivArchive')

    def test_version_of_another_model_is_rejected(self):
        wrong = {'modelId': 99, 'baseModel': 'Wrong'}
        path = self._model('live', {'modelId': 10, 'modelVersionId': 100}, api_info=wrong)
        self.civitai[self._version_url(100)] = {'id': 100, 'modelId': 55}

        self._run(corrupted=[self._issue(path, 10)])

        self.assertEqual(self._read('live.api_info.json'), wrong)

    def test_missing_version_id_leaves_files_untouched(self):
        wrong = {'modelId': 99}
        path = self._model('live', {'modelId': 10}, api_info=wrong)

        self._run(corrupted=[self._issue(path, 10)])

        self.assertEqual(self._read('live.api_info.json'), wrong)
        self.assertEqual(self.requested, [])

    def test_api_error_leaves_files_untouched(self):
        wrong = {'modelId': 99}
        path = self._model('live', {'modelId': 10, 'modelVersionId': 100}, api_info=wrong)
        self.civitai[self._version_url(100)] = 'timeout'

        self._run(corrupted=[self._issue(path, 10)])

        self.assertEqual(self._read('live.api_info.json'), wrong)


class TestResolveRun(_ResolveTestCase):
    def test_mixed_run_routes_each_kind_and_reports_both(self):
        orphan = self._model('gone', {'modelId': 10, 'sha256': 'AAAA'})
        live = self._model('live', {'modelId': 20, 'modelVersionId': 200}, api_info={'modelId': 99})
        self.archive['AAAA'] = {'id': '10', 'name': 'Gone'}
        self.civitai[self._version_url(200)] = {'id': 200, 'modelId': 20}

        update = self.fm.gr.update
        update.reset_mock()
        self._run(orphaned=[self._issue(orphan, 10)],
                  corrupted=[self._issue(live, 20, sha256='BBBB')])

        # gradio is stubbed, so read the report HTML from the last gr.update(value=...).
        final_html = [c.kwargs['value'] for c in update.call_args_list if 'value' in c.kwargs][-1]
        self.assertEqual(self._read('gone.api_info.json')['source'], 'civarchive')
        self.assertEqual(self._read('live.api_info.json')['modelId'], 20)
        self.assertEqual(self.hash_lookups, ['AAAA'])
        self.assertIn('1 recovered via CivArchive', str(final_html))
        self.assertIn('1 mismatched repaired from CivitAI', str(final_html))

    def test_empty_issues_resolve_nothing(self):
        outputs = self._run()
        self.assertEqual(len(outputs), 1)
        self.assertEqual(self.requested, [])
        self.assertEqual(self.hash_lookups, [])


if __name__ == '__main__':
    unittest.main()
