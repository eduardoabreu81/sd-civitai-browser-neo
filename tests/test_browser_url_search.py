"""Direct links must remain visible; search failures must be diagnosable."""

import copy
import json
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from test_civarchive_recovered_html import _RecoveredTestCase, _archived_listing


class TestBrowserUrlSearch(_RecoveredTestCase):
    def setUp(self):
        super().setUp()
        self.gl.previous_inputs = None
        self.gl.update_mode = False
        self.gl.from_update_tab = False
        self.gl.sortNewest = False
        self.gl.isDownloading = False
        self.data = {'items': [_archived_listing()], 'metadata': {'currentPage': 1}}
        self.messages = []
        self.requested = []
        self.patches = [
            patch.object(self.api, 'print', self.messages.append),
            patch.object(self.api, 'debug_print', lambda *_: None),
            patch.object(self.api.gr, 'update', lambda **kwargs: kwargs),
            patch.object(self.api.opts, 'hide_early_access', True, create=True),
            patch.object(self.api.opts, 'hide_paid_models', True, create=True),
        ]
        for patcher in self.patches:
            patcher.start()
        self.addCleanup(lambda: [patcher.stop() for patcher in reversed(self.patches)])

    def serve(self, url, skip_error_check=False):
        self.requested.append(url)
        if not url:
            return 'error'
        params = parse_qs(urlparse(url).query)
        if params.get('baseModels') == ['FLUX.1 D'] or params.get('nsfw') == ['false']:
            return {'items': [], 'metadata': {'currentPage': 1}}
        if '/api/v1/models/' in urlparse(url).path:
            return copy.deepcopy(self.data['items'][0])
        return copy.deepcopy(self.data)

    def search(self, term, search_type='Model name', page=1):
        self.api.request_civit_api = self.serve
        return self.api.initial_model_page(
            content_type=['Checkpoint'], base_filter=['FLUX.1 D'],
            only_liked=True, nsfw=False, exact_search=True, sort_type='Newest',
            period_type='Month', tile_count=20, search_term=term,
            use_search_term=search_type, current_page=page,
        )[2]['value']

    def test_pasted_link_ignores_listing_filters_and_stale_page(self):
        for host in ('civitai.com', 'civitai.red'):
            with self.subTest(host=host):
                self.gl.previous_inputs = None
                html = self.search(f'https://{host}/models/2646164/model', page=3)
                self.assertIn('Stepping On Face', html)
                self.assertIn('data-direct-url="true"', html)
                self.assertEqual(parse_qs(urlparse(self.requested[-1]).query), {})

    def test_direct_url_keeps_paid_version_visible_without_changing_settings(self):
        for version in self.data['items'][0]['modelVersions']:
            version['paidAccess'] = {'permanent': True}
        html = self.search('https://civitai.red/models/2646164/model', 'URL')
        self.assertIn('Stepping On Face', html)
        self.assertTrue(self.api.opts.hide_paid_models)

    def test_name_search_still_uses_listing_filters(self):
        html = self.search('anima')
        params = parse_qs(urlparse(self.requested[-1]).query)
        self.assertEqual(params['baseModels'], ['FLUX.1 D'])
        self.assertEqual(params['nsfw'], ['false'])
        self.assertNotIn('data-direct-url="true"', html)

    def test_empty_search_explains_outcome_without_debug(self):
        html = self.search('anima')
        self.assertIn('No models', html)
        self.assertTrue(any('0' in message and 'search' in message for message in self.messages))

    def test_adapter_exception_is_logged_without_debug(self):
        def fail(**kwargs):
            raise RuntimeError('controlled failure')
        source = SimpleNamespace(name='civitai', search=fail)
        result = self.api._call_browser_source(source, 'search')
        self.assertEqual(result, 'error')
        self.assertTrue(any('RuntimeError' in message for message in self.messages))

    def test_direct_url_timeout_is_not_reported_as_missing_model(self):
        self.api.request_civit_api = lambda *args, **kwargs: 'timeout'
        result = self.api._browser_sources.parse_model_url('https://civitai.red/models/2646164')
        self.assertEqual(result, 'timeout')

    def test_http_429_is_reported_even_when_error_check_is_skipped(self):
        response = self.api.requests.Response()
        response.status_code = 429
        response._content = json.dumps({'error': 'Too many requests'}).encode()
        response.headers['Retry-After'] = '30'
        with patch.object(self.api.requests, 'get', return_value=response):
            result = self.api.request_civit_api(
                'https://civitai.red/api/v1/model-versions/1?token=private',
                skip_error_check=True,
            )
        self.assertEqual(result, 'rate_limited')
        self.assertTrue(any('429' in message and '30' in message for message in self.messages))
        self.assertNotIn('private', '\n'.join(self.messages))

    def test_http_404_is_not_decoded_as_a_success(self):
        response = self.api.requests.Response()
        response.status_code = 404
        response._content = b'{"error": "not found"}'
        with patch.object(self.api.requests, 'get', return_value=response):
            result = self.api.request_civit_api('https://civitai.red/api/v1/model-versions/1', skip_error_check=True)
        self.assertEqual(result, 'not_found')

    def test_sfw_setting_still_controls_the_api_domain(self):
        with patch.object(self.api.opts, 'civitai_sfw_only', True, create=True):
            self.search('https://civitai.red/models/2646164')
        self.assertEqual(urlparse(self.requested[-1]).hostname, 'civitai.com')

    def test_link_without_scheme_and_with_other_search_type_is_direct(self):
        html = self.search('civitai.red/models/2646164', 'SHA256')
        self.assertIn('Stepping On Face', html)
        self.assertIn('data-direct-url="true"', html)

    def test_download_link_preserves_rate_limit_error(self):
        self.api.request_civit_api = lambda *args, **kwargs: 'rate_limited'
        result = self.api._browser_sources.parse_model_url('https://civitai.red/api/download/models/2971246')
        self.assertEqual(result, 'rate_limited')

    def test_direct_url_ignores_selected_source(self):
        self.api.request_civit_api = self.serve
        html = self.api.initial_model_page(
            search_term='https://civitai.red/models/2646164', use_search_term='Model name',
            source='CivArchive', content_type=['Checkpoint'], tile_count=20,
        )[2]['value']
        self.assertIn('Stepping On Face', html)
        self.assertIn('/api/v1/models/2646164', self.requested[-1])

    def test_server_error_retries_and_reports_http_status(self):
        response = self.api.requests.Response()
        response.status_code = 503
        response._content = b'{"error": "busy"}'
        with patch.object(self.api.requests, 'get', return_value=response) as get, \
                patch.object(self.api.time, 'sleep'):
            result = self.api.request_civit_api('https://civitai.red/api/v1/models/1', skip_error_check=True)
        self.assertEqual(result, 'error')
        self.assertEqual(get.call_count, 3)
        self.assertTrue(any('503' in message for message in self.messages))
