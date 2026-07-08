"""Unit tests for the browser source adapter layer.

These tests isolate ``scripts/browser_sources/civitai.py`` from the rest of the
extension by mocking the small surface of ``scripts.civitai_api`` and
``scripts.civitai_global`` that the adapter depends on.  They run without
Forge Neo or a network connection.
"""
import sys
import types
import unittest
from unittest.mock import patch

# We patch sys.modules so these isolated tests don't replace the real extension
# modules globally and break other test files that import them.
_FAKE_API = types.ModuleType('scripts.civitai_api')
_FAKE_API.get_civitai_domain = lambda: 'civitai.red'
_FAKE_API.normalize_sha256 = lambda h: (h or '').strip().upper() if h else None
_FAKE_API.get_headers = lambda referer=None, no_api=None: {}
_FAKE_API.get_proxies = lambda: ({}, False)
_FAKE_API.api_error_msg = lambda x: f'<p>ERROR: {x}</p>'
_FAKE_API.safe_json_load = lambda p: None
_FAKE_API.safe_json_save = lambda p, d: True
_FAKE_API.request_civit_api = lambda url, skip_error_check=False: {'items': [], 'metadata': {}}

_FAKE_GL = types.ModuleType('scripts.civitai_global')
_FAKE_GL.print = print
_FAKE_GL.debug_print = lambda *a, **k: None

_SCRIPTS_PKG = types.ModuleType('scripts')
_SCRIPTS_PKG.__path__ = ['scripts']

_MODULE_OVERRIDES = {
    'scripts': _SCRIPTS_PKG,
    'scripts.civitai_api': _FAKE_API,
    'scripts.civitai_global': _FAKE_GL,
}


class TestCivitaiAdapter(unittest.TestCase):
    def setUp(self):
        self._patch = patch.dict(sys.modules, _MODULE_OVERRIDES, clear=False)
        self._patch.start()
        sys.path.insert(0, '.')

        # Import inside the patched context so the adapter sees the fakes.
        from scripts.browser_sources.civitai import CivitAISource
        import scripts.browser_sources as bs
        self.src = CivitAISource()
        self.bs = bs

    def tearDown(self):
        self._patch.stop()
        if '.' in sys.path:
            sys.path.remove('.')

    def test_source_registered(self):
        self.assertEqual(self.bs.source_choices(), ['CivitAI', 'CivArchive'])
        self.assertEqual(self.bs.get_browser_source('civitai').display_name, 'CivitAI')

    def test_create_api_url_matches_original_shape(self):
        url = self.src._create_api_url(
            query='anima',
            search_type='Model name',
            content_type=['Checkpoint'],
            base_filter=['Anima'],
            sort='Highest Rated',
            period='Month',
            nsfw=False,
            exact=True,
            page_size=20,
            only_liked=False,
            page=1,
        )
        self.assertIn('civitai.', url)
        self.assertIn('query=anima', url)
        self.assertIn('types=Checkpoint', url)
        self.assertIn('baseModels=Anima', url)
        self.assertIn('limit=20', url)
        self.assertIn('sort=Highest%20Rated', url)
        self.assertIn('page=1', url)

    def test_create_api_url_rebuilds_for_mismatched_page(self):
        url = self.src._create_api_url(
            query='anima',
            search_type='Model name',
            content_type=['Checkpoint'],
            base_filter=None,
            sort='Highest Rated',
            period='Month',
            nsfw=False,
            exact=True,
            page_size=20,
            only_liked=False,
            page_url='https://civitai.red/api/v1/models?limit=20&page=1',
            page=2,
        )
        self.assertIn('page=2', url)

    def test_create_api_url_uses_next_prev_url_when_page_matches(self):
        real_url = 'https://civitai.red/api/v1/models?limit=20&page=3&query=anima'
        url = self.src._create_api_url(
            query='anima',
            search_type='Model name',
            content_type=None,
            base_filter=None,
            sort='Highest Rated',
            period='Month',
            nsfw=False,
            exact=True,
            page_size=20,
            only_liked=False,
            page_url=real_url,
            page=3,
        )
        self.assertEqual(url, real_url)

    def test_create_api_url_ignores_browser_source_token(self):
        url = self.src._create_api_url(
            query='anima',
            search_type='Model name',
            content_type=None,
            base_filter=None,
            sort='Highest Rated',
            period='Month',
            nsfw=False,
            exact=True,
            page_size=20,
            only_liked=False,
            page_url='browser_source://civitai/page/1',
            page=1,
        )
        self.assertFalse(url.startswith('browser_source://'))
        self.assertIn('query=anima', url)

    def test_normalize_model_tags_browser_source(self):
        item = {
            'id': 123,
            'name': 'Test Model',
            'type': 'LORA',
            'modelVersions': [{
                'id': 456,
                'name': 'v1',
                'files': [{'name': 'x.safetensors', 'hashes': {'SHA256': 'abc'}}],
                'images': [{'url': 'http://example.com/i.png'}],
            }],
        }
        norm = self.src._normalize_model(item)
        self.assertEqual(norm['browserSource'], 'civitai')
        self.assertEqual(norm['browserSourceId'], '123')
        self.assertEqual(norm['modelVersions'][0]['files'][0]['sha256'], 'ABC')

    def test_supported_search_types(self):
        self.assertEqual(self.src.supported_search_types(), ['Model name', 'User name', 'Tag', 'SHA256'])

    def test_supports_pagination(self):
        self.assertTrue(self.src.supports_pagination())


class TestCivArchiveAdapter(unittest.TestCase):
    def setUp(self):
        self._patch = patch.dict(sys.modules, _MODULE_OVERRIDES, clear=False)
        self._patch.start()
        sys.path.insert(0, '.')

        from scripts.browser_sources.civarchive import CivArchiveSource
        self.src = CivArchiveSource()

    def tearDown(self):
        self._patch.stop()
        if '.' in sys.path:
            sys.path.remove('.')

    def test_supported_search_types(self):
        self.assertEqual(self.src.supported_search_types(), ['Model name', 'SHA256'])

    def test_get_download_url_prefers_active_mirror(self):
        file_info = {
            'name': 'model.safetensors',
            'browserSourceFileRaw': {
                'mirrors': [
                    {'url': 'https://deleted.example/dl', 'deletedAt': '2025-01-01'},
                    {'url': 'https://active.example/dl', 'deletedAt': None},
                ],
            },
        }
        self.assertEqual(self.src.get_download_url(file_info), 'https://active.example/dl')

    def test_get_download_url_falls_back_to_first_mirror(self):
        file_info = {
            'name': 'model.safetensors',
            'browserSourceFileRaw': {
                'mirrors': [
                    {'url': 'https://only.example/dl', 'deletedAt': '2025-01-01'},
                ],
            },
        }
        self.assertEqual(self.src.get_download_url(file_info), 'https://only.example/dl')

    def test_normalize_model_from_civarchive_payload(self):
        payload = {
            'id': 1746460,
            'name': 'Mixplin Style [Illustrious]',
            'type': 'LORA',
            'description': 'desc',
            'is_nsfw': True,
            'nsfw_level': 31,
            'tags': ['art', 'style'],
            'creator_username': 'Ty_Lee',
            'creator_name': 'Ty_Lee',
            'creator_url': '/users/Ty_Lee',
            'version': {
                'id': 1976567,
                'modelId': 1746460,
                'name': 'v1.0',
                'baseModel': 'Illustrious',
                'downloadCount': 437,
                'ratingCount': 0,
                'rating': 0,
                'nsfw_level': 31,
                'trigger': ['mxpln'],
                'files': [{
                    'id': 1874043,
                    'name': 'mxpln-illustrious-ty_lee.safetensors',
                    'type': 'Model',
                    'sizeKB': 223124.37109375,
                    'downloadUrl': 'https://civitai.com/api/download/models/1976567',
                    'sha256': 'e2b7a280d6539556f23f380b3f71e4e22bc4524445c4c96526e117c6005c6ad3',
                    'is_primary': False,
                    'mirrors': [{
                        'filename': 'mxpln-illustrious-ty_lee.safetensors',
                        'url': 'https://civitai.com/api/download/models/1976567',
                        'deletedAt': None,
                    }],
                }],
                'images': [{'id': 86403595, 'url': 'https://img.genur.art/example.png', 'nsfwLevel': 1}],
            },
            'versions': [{'id': 1976567, 'name': 'v1.0'}],
        }
        model = self.src._normalize_model(payload)
        self.assertEqual(model['browserSource'], 'civarchive')
        self.assertEqual(model['browserSourceId'], '1746460')
        self.assertEqual(model['type'], 'LORA')
        self.assertEqual(model['name'], 'Mixplin Style [Illustrious]')
        self.assertEqual(model['creator']['username'], 'Ty_Lee')
        self.assertEqual(model['nsfw'], True)
        version = model['modelVersions'][0]
        self.assertEqual(version['id'], '1976567')
        self.assertEqual(version['baseModel'], 'Illustrious')
        self.assertEqual(version['trainedWords'], ['mxpln'])
        self.assertEqual(version['files'][0]['hashes']['SHA256'], 'E2B7A280D6539556F23F380B3F71E4E22BC4524445C4C96526E117C6005C6AD3')


if __name__ == '__main__':
    unittest.main()
