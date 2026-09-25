"""A model delisted from CivitAI but recovered via CivArchive must render its real
page everywhere the model detail HTML is built or shown:

  - Local Models card + detail panel (_build_local_fallback_browser_item)
  - native card popup (model_from_sent → _delisted_model_body)
  - "send to Browser" (send_to_browser)
  - bulk .html generation (render_civarchive_model_html)

Runs the real update_model_info against stubbed WebUI modules.
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

SHA = '1CFF84EED48E013E3A3A2B02FB014D73C2C53E1632ACEBBCC49DE2369AE87BAD'
MIRROR = 'https://huggingface.co/mirror/2646164/2971246/lora.safetensors'
IMAGE = 'https://img.genur.art/preview.png'


def _archived_listing(sha=SHA):
    """A .api_info.json as _recover_orphan_via_civarchive() writes it."""
    return {
        'id': '2646164',
        'name': 'Stepping On Face',
        'type': 'LORA',
        'description': '<p>Archived description</p>',
        'creator': {'username': 'archived_author'},
        'tags': ['concept', 'pose'],
        'nsfw': True,
        'stats': {'downloadCount': 1234},
        'modelVersions': [
            {
                'id': '1111', 'name': 'v0.9', 'baseModel': 'Illustrious',
                'files': [{'name': 'old.safetensors', 'hashes': {'SHA256': 'F' * 64}}],
                'images': [], 'trainedWords': ['oldword'],
            },
            {
                'id': '2971246', 'name': 'v1.0', 'baseModel': 'Anima',
                'createdAt': '2026-05-01T10:00:00.000Z',
                'trainedWords': ['stepping on face'],
                'images': [{'url': IMAGE, 'type': 'image', 'width': 512}],
                'files': [{
                    'name': 'archived-name.safetensors',
                    'hashes': {'SHA256': sha},
                    'browserSourceFileRaw': {'mirrors': [{'url': MIRROR, 'deletedAt': None}]},
                }],
            },
        ],
        'browserSource': 'civarchive',
        'browserSourceId': '2646164',
        'browserSourceUrl': 'https://civarchive.com/models/2646164',
        'source': 'civarchive',
        'archived_url': 'https://civarchive.com/models/2646164',
    }


class _RecoveredTestCase(unittest.TestCase):
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
        # The shared stub leaves scripts.civitai_download bare; update_model_info
        # formats file sizes through it.
        api._download.convert_size = lambda size_bytes: f'{size_bytes} B'

    @classmethod
    def tearDownClass(cls):
        sys.modules.clear()
        sys.modules.update(cls._saved_modules)

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._orig = {
            'request': self.api.request_civit_api,
            'folder': self.api.contenttype_folder,
            'list_html': self.api.model_list_html,
            'get_models': self.fm.get_models,
            'send2trash': self.fm.send2trash,
        }
        self.api.contenttype_folder = lambda ct, desc=None, custom_folder=None: self.tmp
        # Recycle bin: record what was sent there and move it out of the folder.
        self.trashed = []

        def fake_send2trash(path):
            self.trashed.append(os.path.basename(path))
            os.remove(path)

        self.fm.send2trash = fake_send2trash
        self.fm.opts.save_html_on_save = False

    def tearDown(self):
        self.api.request_civit_api = self._orig['request']
        self.api.contenttype_folder = self._orig['folder']
        self.api.model_list_html = self._orig['list_html']
        self.fm.get_models = self._orig['get_models']
        self.fm.send2trash = self._orig['send2trash']
        if hasattr(self.fm.opts, 'save_html_on_save'):
            del self.fm.opts.save_html_on_save
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _html(self, name='54ATE3J7NW08978JEZMTJ20WA0'):
        path = os.path.join(self.tmp, name + '.html')
        if not os.path.exists(path):
            return None
        with io.open(path, encoding='utf-8') as handle:
            return handle.read()

    def _model(self, name='54ATE3J7NW08978JEZMTJ20WA0', api_info=None, html=None):
        path = os.path.join(self.tmp, name + '.safetensors')
        with io.open(path, 'w', encoding='utf-8') as handle:
            handle.write('')
        self._write(name + '.json', {'modelId': 2646164, 'sha256': SHA})
        if api_info is not None:
            self._write(name + '.api_info.json', api_info)
        if html is not None:
            with io.open(os.path.join(self.tmp, name + '.html'), 'w', encoding='utf-8') as handle:
                handle.write(html)
        return path

    def _write(self, file_name, data):
        with io.open(os.path.join(self.tmp, file_name), 'w', encoding='utf-8') as handle:
            json.dump(data, handle)


class TestRecoveredLocalItem(_RecoveredTestCase):
    def test_item_carries_the_real_listing(self):
        item = self.fm._build_local_fallback_browser_item(self._model(api_info=_archived_listing()))

        self.assertEqual(item['name'], 'Stepping On Face')
        self.assertEqual(item['creator']['username'], 'archived_author')
        self.assertEqual(item['tags'], ['concept', 'pose'])
        self.assertEqual(item['browserSource'], 'civarchive')
        self.assertEqual(item['civarchive_url'], 'https://civarchive.com/models/2646164')

    def test_installed_version_is_picked_by_hash(self):
        item = self.fm._build_local_fallback_browser_item(self._model(api_info=_archived_listing()))

        version = item['modelVersions'][0]
        self.assertEqual(len(item['modelVersions']), 1, 'only the installed version is carried over')
        self.assertEqual(version['name'], 'v1.0')
        self.assertEqual(version['baseModel'], 'Anima')
        self.assertEqual(version['trainedWords'], ['stepping on face'])
        self.assertEqual(version['images'][0]['url'], IMAGE)
        self.assertEqual(version['publishedAt'], '2026-05-01T10:00:00.000Z')
        self.assertEqual(version['files'][0]['browserSourceFileRaw']['mirrors'][0]['url'], MIRROR)

    def test_local_identity_is_kept(self):
        item = self.fm._build_local_fallback_browser_item(self._model(api_info=_archived_listing()))

        self.assertLess(item['id'], 0, 'Local treats id < 0 as local-only (no update/download)')
        self.assertTrue(item['local_only'])
        local_file = item['modelVersions'][0]['files'][0]
        self.assertEqual(local_file['name'], '54ATE3J7NW08978JEZMTJ20WA0.safetensors')
        self.assertEqual(local_file['hashes']['SHA256'], SHA)

    def test_without_recovery_the_stub_is_unchanged(self):
        item = self.fm._build_local_fallback_browser_item(self._model())

        self.assertEqual(item['name'], '54ATE3J7NW08978JEZMTJ20WA0')
        self.assertEqual(item['modelVersions'][0]['name'], 'Local file')
        self.assertNotIn('browserSource', item)

    def test_civitai_api_info_is_not_treated_as_a_recovery(self):
        item = self.fm._build_local_fallback_browser_item(
            self._model(api_info={'modelId': 2646164, 'name': 'v1', 'baseModel': 'SDXL'}))
        self.assertEqual(item['modelVersions'][0]['name'], 'Local file')


class TestRecoveredHtml(_RecoveredTestCase):
    def test_page_has_data_links_images_and_mirrors(self):
        html = self.fm.render_civarchive_model_html(self._model(api_info=_archived_listing()))

        self.assertIn('Stepping On Face', html)
        self.assertIn('https://civarchive.com/models/2646164', html)
        self.assertIn('recovered via CivArchive', html)
        self.assertIn(IMAGE, html)
        self.assertIn(MIRROR, html)
        self.assertIn('Archived description', html)
        self.assertIn('stepping on face', html)
        self.assertIn('Anima', html)

    def test_no_recovery_renders_nothing(self):
        self.assertIsNone(self.fm.render_civarchive_model_html(self._model()))


OLD_PAGE = '<head></head><div class="info-section">Old CivitAI page civitai.red/models/2646164</div>'


class TestPopup(_RecoveredTestCase):
    """model_from_sent — the popup from a native card's CivitAI button."""

    def _popup_html(self, name='54ATE3J7NW08978JEZMTJ20WA0'):
        update = self.fm.gr.update
        update.reset_mock()
        self.fm.model_from_sent(name, 'lora')
        return [c.kwargs['value'] for c in update.call_args_list if 'value' in c.kwargs][-1]

    def test_recovery_wins_over_the_cached_civitai_page(self):
        self._model(api_info=_archived_listing(), html=OLD_PAGE)
        self.fm.opts.use_local_html = True
        try:
            html = self._popup_html()
        finally:
            del self.fm.opts.use_local_html
        self.assertIn('Stepping On Face', html)
        self.assertIn(MIRROR, html)
        self.assertNotIn('Old CivitAI page', html)

    def test_recovery_does_not_ask_civitai(self):
        self._model(api_info=_archived_listing())
        asked = []
        self.fm.get_models = lambda *a, **k: asked.append(a) or 2646164
        self._popup_html()
        self.assertEqual(asked, [])

    def test_unrecovered_delisted_model_keeps_its_cached_page(self):
        self._model(html=OLD_PAGE)
        self.assertIn('Old CivitAI page', self.fm._delisted_model_body(
            os.path.join(self.tmp, '54ATE3J7NW08978JEZMTJ20WA0.safetensors'), 'removed'))

    def test_nothing_recovered_or_cached_shows_the_error(self):
        body = self.fm._delisted_model_body(self._model(), 'removed')
        self.assertIn('No local cached data was found', body)


class TestRecoveredHtmlSidecar(_RecoveredTestCase):
    """_write_recovered_html — the .html file on disk after a recovery."""

    def test_old_civitai_page_is_trashed_and_rebuilt(self):
        path = self._model(api_info=_archived_listing(), html=OLD_PAGE)

        self.assertTrue(self.fm._write_recovered_html(path))

        self.assertEqual(self.trashed, ['54ATE3J7NW08978JEZMTJ20WA0.html'])
        page = self._html()
        self.assertIn('recovered via CivArchive', page)
        self.assertIn(MIRROR, page)
        self.assertIn('<meta charset="UTF-8">', page)

    def test_a_page_already_rebuilt_is_overwritten_not_trashed(self):
        path = self._model(api_info=_archived_listing(), html=OLD_PAGE)
        self.fm._write_recovered_html(path)
        self.trashed.clear()

        self.fm._write_recovered_html(path)

        self.assertEqual(self.trashed, [], 're-running Resolve must not fill the recycle bin')
        self.assertIn('recovered via CivArchive', self._html())

    def test_no_page_is_created_when_saving_html_is_off(self):
        path = self._model(api_info=_archived_listing())
        self.assertFalse(self.fm._write_recovered_html(path))
        self.assertIsNone(self._html())

    def test_page_is_created_when_saving_html_is_on(self):
        path = self._model(api_info=_archived_listing())
        self.fm.opts.save_html_on_save = True
        self.assertTrue(self.fm._write_recovered_html(path))
        self.assertIn('Stepping On Face', self._html())

    def test_unrecovered_model_page_is_left_alone(self):
        path = self._model(html=OLD_PAGE)
        self.assertFalse(self.fm._write_recovered_html(path))
        self.assertEqual(self._html(), OLD_PAGE)
        self.assertEqual(self.trashed, [])

    def test_resolve_rebuilds_the_page(self):
        path = self._model(html=OLD_PAGE)
        listing = _archived_listing()
        listing.pop('source'); listing.pop('archived_url')

        class _Archive:
            def get_version_by_hash(self, sha256):
                return listing

        issue = {'file_path': path, 'sha256': SHA, 'model_id': 2646164,
                 'model_name': os.path.basename(path)}
        self.assertTrue(self.fm._recover_orphan_via_civarchive(_Archive(), issue))

        self.assertEqual(self.trashed, ['54ATE3J7NW08978JEZMTJ20WA0.html'])
        self.assertIn('recovered via CivArchive', self._html())


class TestSendToBrowser(_RecoveredTestCase):
    def test_delisted_model_is_sent_as_its_civarchive_listing(self):
        self._model(api_info=_archived_listing())
        self.fm.get_models = lambda file_path, gen_hash=None: 2646164
        self.api.request_civit_api = lambda api_url=None, skip_error_check=False: {'items': [], 'metadata': {}}
        rendered = []
        self.api.model_list_html = lambda data, *a, **k: rendered.append(data) or 'cards'

        self.fm.send_to_browser('54ATE3J7NW08978JEZMTJ20WA0', 'lora', 0)

        self.assertEqual(rendered[0]['items'][0]['name'], 'Stepping On Face')
        self.assertEqual(rendered[0]['items'][0]['browserSource'], 'civarchive')

    def test_listed_model_is_untouched(self):
        self._model(api_info=_archived_listing())
        self.fm.get_models = lambda file_path, gen_hash=None: 2646164
        live = {'items': [{'id': 2646164, 'name': 'Live'}], 'metadata': {}}
        self.api.request_civit_api = lambda api_url=None, skip_error_check=False: live
        rendered = []
        self.api.model_list_html = lambda data, *a, **k: rendered.append(data) or 'cards'

        self.fm.send_to_browser('54ATE3J7NW08978JEZMTJ20WA0', 'lora', 0)

        self.assertEqual(rendered[0]['items'][0]['name'], 'Live')


if __name__ == '__main__':
    unittest.main()
