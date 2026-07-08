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
        self.assertEqual(self.bs.source_choices(), ['CivitAI'])
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


if __name__ == '__main__':
    unittest.main()
