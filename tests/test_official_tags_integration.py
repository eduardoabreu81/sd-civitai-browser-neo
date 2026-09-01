"""Integration tests for fetch_official_tags against the real shipped code.

Unlike the other civitai_file_manage suites, this one imports the actual module
by stubbing gradio, the WebUI `modules` package and the optional third-party
imports. scripts.civitai_download is stubbed too — importing it for real starts
an aria2 RPC process, which a test run has no business doing.

Network is stubbed at _api.request_civit_api and at the CivArchive adapter, so
these exercise the real grouping, skipping, fallback and persistence logic
without touching CivitAI.

sys.modules is saved and restored around the class so these stubs cannot leak
into the other test files (see the same precaution in test_browser_sources).
"""

import io
import json
import os
import shutil
import sys
import tempfile
import types
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def _install_stubs():
    gr = types.ModuleType('gradio')
    for name in ('Progress', 'update', 'Textbox', 'Button', 'HTML', 'Checkbox',
                 'Dropdown', 'State', 'Row', 'Column', 'Tab', 'Blocks', 'Markdown',
                 'CheckboxGroup', 'Gallery', 'Image', 'Slider', 'Number',
                 'Accordion', 'Group', 'Dataframe', 'File', 'Radio', 'Label', 'JSON'):
        setattr(gr, name, MagicMock())
    sys.modules['gradio'] = gr

    for name in ('bs4', 'send2trash'):
        module = types.ModuleType(name)
        module.BeautifulSoup = MagicMock()
        module.send2trash = MagicMock()
        sys.modules[name] = module

    sys.modules['modules'] = types.ModuleType('modules')

    paths = types.ModuleType('modules.paths')
    paths.models_path = ''
    paths.extensions_dir = ''
    paths.data_path = ''
    sys.modules['modules.paths'] = paths

    shared = types.ModuleType('modules.shared')
    shared.cmd_opts = types.SimpleNamespace(
        ckpt_dirs=[], lora_dirs=[], vae_dirs=[],
        lora_dir='models/Lora', disable_queue=True)
    shared.opts = types.SimpleNamespace()
    sys.modules['modules.shared'] = shared

    images = types.ModuleType('modules.images')
    images.read_info_from_image = lambda image: (None, None)
    sys.modules['modules.images'] = images

    scripts_mod = types.ModuleType('modules.scripts')
    scripts_mod.basedir = lambda: '.'
    sys.modules['modules.scripts'] = scripts_mod

    # Importing the real download module starts an aria2 RPC process.
    download = types.ModuleType('scripts.civitai_download')
    for name in ('download_file', 'download_create_thread', 'random_number',
                 'download_start', 'download_cancel', 'info_to_json'):
        setattr(download, name, MagicMock())
    sys.modules['scripts.civitai_download'] = download


class _FetchTagsTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._saved_modules = dict(sys.modules)
        # Other suites replace 'scripts' and its submodules with bare stubs that
        # have no __path__, which makes a real import of scripts.civitai_*
        # fail outright. Drop them so this class always imports the shipped
        # code; tearDownClass puts the caller's sys.modules back verbatim.
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
        self._orig_folders = self.api.contenttype_folders
        self._orig_source = self.fm._browser_sources.get_browser_source
        self.api.contenttype_folders = lambda ct, desc=None, custom_folder=None: (
            [self.tmp] if ct == 'LORA' else [])
        self.requested = []

    def tearDown(self):
        self.api.request_civit_api = self._orig_request
        self.api.contenttype_folders = self._orig_folders
        self.fm._browser_sources.get_browser_source = self._orig_source
        self.gl.cancel_status = False
        shutil.rmtree(self.tmp, ignore_errors=True)

    # -- helpers ---------------------------------------------------------

    def _lora(self, name, sidecar=None):
        path = os.path.join(self.tmp, name + '.safetensors')
        with io.open(path, 'w', encoding='utf-8') as handle:
            handle.write('')
        if sidecar is not None:
            with io.open(os.path.join(self.tmp, name + '.json'), 'w', encoding='utf-8') as handle:
                json.dump(sidecar, handle)
        return path

    def _sidecar(self, name):
        with io.open(os.path.join(self.tmp, name + '.json'), encoding='utf-8') as handle:
            return json.load(handle)

    def _serve(self, by_model_id):
        """Stub CivitAI: map model id -> payload, 'not_found', 'error', ..."""
        def fake_request(api_url=None, skip_error_check=False):
            model_id = int(str(api_url).rstrip('/').split('/')[-1])
            self.requested.append(model_id)
            return by_model_id.get(model_id, 'not_found')
        self.api.request_civit_api = fake_request

    def _run(self, refresh_existing=False, use_civarchive=True):
        return list(self.fm.fetch_official_tags(
            ['LORA'], refresh_existing=refresh_existing,
            use_civarchive=use_civarchive, progress=None))


class TestFetchOfficialTags(_FetchTagsTestCase):
    def test_tags_are_written_to_the_sidecar(self):
        self._lora('a', {'modelId': 10, 'sha256': 'A'})
        self._serve({10: {'tags': ['style', 'anime']}})
        self._run()
        self.assertEqual(self._sidecar('a')['modelTags'], ['style', 'anime'])

    def test_one_request_per_unique_model_id(self):
        # Two files from the same listing: different versions, or the same LoRA
        # at two precisions. One request must serve both.
        self._lora('v1', {'modelId': 10})
        self._lora('v2', {'modelId': 10})
        self._lora('other', {'modelId': 11})
        self._serve({10: {'tags': ['style']}, 11: {'tags': ['character']}})
        self._run()
        self.assertEqual(sorted(self.requested), [10, 11])
        self.assertEqual(self._sidecar('v1')['modelTags'], ['style'])
        self.assertEqual(self._sidecar('v2')['modelTags'], ['style'])

    def test_files_with_existing_tags_are_skipped(self):
        self._lora('has', {'modelId': 10, 'modelTags': ['kept']})
        self._serve({10: {'tags': ['fresh']}})
        self._run()
        self.assertEqual(self.requested, [], 'no request should be made at all')
        self.assertEqual(self._sidecar('has')['modelTags'], ['kept'])

    def test_refresh_existing_overwrites(self):
        self._lora('has', {'modelId': 10, 'modelTags': ['stale']})
        self._serve({10: {'tags': ['fresh']}})
        self._run(refresh_existing=True)
        self.assertEqual(self._sidecar('has')['modelTags'], ['fresh'])

    def test_file_without_a_model_id_is_skipped_not_crashed(self):
        self._lora('orphan', {'sha256': 'A'})
        self._lora('ok', {'modelId': 10})
        self._serve({10: {'tags': ['style']}})
        self._run()
        self.assertEqual(self.requested, [10])
        self.assertNotIn('modelTags', self._sidecar('orphan'))

    def test_file_without_any_sidecar_is_skipped(self):
        self._lora('bare')
        self._run()
        self.assertEqual(self.requested, [])

    def test_non_dict_sidecar_is_skipped(self):
        # Wildcard lists and other extensions' files live under model roots too.
        path = os.path.join(self.tmp, 'junk.safetensors')
        with io.open(path, 'w', encoding='utf-8') as handle:
            handle.write('')
        with io.open(os.path.join(self.tmp, 'junk.json'), 'w', encoding='utf-8') as handle:
            json.dump(['not', 'a', 'dict'], handle)
        self._run()
        self.assertEqual(self.requested, [])

    def test_other_sidecar_fields_are_preserved(self):
        self._lora('keep', {'modelId': 10, 'sha256': 'A', 'loraCategory': 'Style',
                            'activation text': 'trigger'})
        self._serve({10: {'tags': ['anime']}})
        self._run()
        data = self._sidecar('keep')
        self.assertEqual(data['sha256'], 'A')
        self.assertEqual(data['loraCategory'], 'Style')
        self.assertEqual(data['activation text'], 'trigger')
        self.assertEqual(data['modelTags'], ['anime'])

    def test_a_listing_with_no_tags_writes_nothing(self):
        self._lora('untagged', {'modelId': 10})
        self._serve({10: {'tags': []}})
        self._run()
        self.assertNotIn('modelTags', self._sidecar('untagged'))

    def test_comma_separated_tags_are_normalized(self):
        self._lora('a', {'modelId': 10})
        self._serve({10: {'tags': 'style, anime'}})
        self._run()
        self.assertEqual(self._sidecar('a')['modelTags'], ['style', 'anime'])


class TestCivArchiveFallback(_FetchTagsTestCase):
    def _adapter(self, tags_by_id):
        adapter = MagicMock()
        adapter.get_model.side_effect = lambda source_id, **kw: (
            {'tags': tags_by_id[int(source_id)]} if int(source_id) in tags_by_id else None)
        self.fm._browser_sources.get_browser_source = lambda name: adapter
        return adapter

    def test_delisted_model_recovers_tags_from_civarchive(self):
        self._lora('gone', {'modelId': 10})
        self._serve({})                      # 404 on CivitAI
        self._adapter({10: ['style']})
        self._run()
        data = self._sidecar('gone')
        self.assertEqual(data['modelTags'], ['style'])
        self.assertEqual(data['modelTagsSource'], 'civarchive',
                         'the provenance of recovered tags must be recorded')

    def test_civarchive_is_not_consulted_when_civitai_answers(self):
        self._lora('live', {'modelId': 10})
        self._serve({10: {'tags': ['style']}})
        adapter = self._adapter({10: ['wrong']})
        self._run()
        adapter.get_model.assert_not_called()
        self.assertNotIn('modelTagsSource', self._sidecar('live'))

    def test_civarchive_is_skipped_when_disabled(self):
        self._lora('gone', {'modelId': 10})
        self._serve({})
        adapter = self._adapter({10: ['style']})
        self._run(use_civarchive=False)
        adapter.get_model.assert_not_called()
        self.assertNotIn('modelTags', self._sidecar('gone'))

    def test_transient_api_error_does_not_hit_civarchive(self):
        # 'error' means try again later, not "this listing is gone" — asking
        # CivArchive would just spend a second request on a temporary blip.
        self._lora('flaky', {'modelId': 10})
        self.api.request_civit_api = lambda api_url=None, skip_error_check=False: 'error'
        adapter = self._adapter({10: ['style']})
        self._run()
        adapter.get_model.assert_not_called()

    def test_civarchive_failure_is_not_fatal(self):
        self._lora('gone', {'modelId': 10})
        self._lora('fine', {'modelId': 11})
        self._serve({11: {'tags': ['ok']}})
        adapter = MagicMock()
        adapter.get_model.side_effect = RuntimeError('archive down')
        self.fm._browser_sources.get_browser_source = lambda name: adapter
        self._run()
        self.assertEqual(self._sidecar('fine')['modelTags'], ['ok'],
                         'one failed lookup must not abort the run')


class TestCancellation(_FetchTagsTestCase):
    def test_cancel_stops_the_run_and_clears_the_flag(self):
        for i in range(5):
            self._lora(f'm{i}', {'modelId': 10 + i})

        served = {10 + i: {'tags': ['style']} for i in range(5)}

        def fake_request(api_url=None, skip_error_check=False):
            model_id = int(str(api_url).rstrip('/').split('/')[-1])
            self.requested.append(model_id)
            self.gl.cancel_status = True     # cancel after the first model
            return served[model_id]
        self.api.request_civit_api = fake_request

        self._run()
        self.assertEqual(len(self.requested), 1, 'the loop must stop at the next boundary')
        self.assertFalse(self.gl.cancel_status,
                         'a cancelled run must not leave the flag set for the next one')

    def test_cancel_tag_fetch_sets_the_flag(self):
        self.gl.cancel_status = False
        self.fm.cancel_tag_fetch()
        self.assertTrue(self.gl.cancel_status)
        self.gl.cancel_status = False


class TestEmptyCases(_FetchTagsTestCase):
    def test_no_folders_selected(self):
        result = list(self.fm.fetch_official_tags([], progress=None))
        self.assertTrue(result, 'must yield a message rather than silently doing nothing')

    def test_nothing_to_fetch_reports_cleanly(self):
        self._lora('done', {'modelId': 10, 'modelTags': ['style']})
        result = self._run()
        self.assertEqual(self.requested, [])
        self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()
