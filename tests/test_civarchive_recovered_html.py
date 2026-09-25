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
        }
        self.api.contenttype_folder = lambda ct, desc=None, custom_folder=None: self.tmp

    def tearDown(self):
        self.api.request_civit_api = self._orig['request']
        self.api.contenttype_folder = self._orig['folder']
        self.api.model_list_html = self._orig['list_html']
        self.fm.get_models = self._orig['get_models']
        shutil.rmtree(self.tmp, ignore_errors=True)

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


class TestDelistedPopupBody(_RecoveredTestCase):
    def test_recovery_is_used_when_there_is_no_cached_page(self):
        body = self.fm._delisted_model_body(self._model(api_info=_archived_listing()), 'removed')
        self.assertIn('Stepping On Face', body)
        self.assertIn(MIRROR, body)

    def test_cached_original_page_wins_over_the_recovery(self):
        path = self._model(api_info=_archived_listing(),
                           html='<head></head><div class="info-section">Original CivitAI page</div>')
        body = self.fm._delisted_model_body(path, 'removed')
        self.assertIn('Original CivitAI page', body)
        self.assertIn('removed by its owner', body)
        self.assertNotIn(MIRROR, body)

    def test_recovery_wins_over_a_cached_page_with_a_broken_gallery(self):
        path = self._model(api_info=_archived_listing(),
                           html='<head></head><div>Unable to load preview images</div>')
        body = self.fm._delisted_model_body(path, 'removed')
        self.assertIn(IMAGE, body)

    def test_nothing_recovered_or_cached_shows_the_error(self):
        body = self.fm._delisted_model_body(self._model(), 'removed')
        self.assertIn('No local cached data was found', body)


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
