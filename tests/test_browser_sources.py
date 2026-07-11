"""Unit tests for the browser source adapter layer.

These tests isolate ``scripts/browser_sources/civitai.py`` from the rest of the
extension by mocking the small surface of ``scripts.civitai_api`` and
``scripts.civitai_global`` that the adapter depends on.  They run without
Forge Neo or a network connection.
"""
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

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
        from scripts.browser_sources.normalizer import canonical_file, canonical_image
        import scripts.browser_sources as bs
        self.src = CivitAISource()
        self.bs = bs
        self.canonical_file = canonical_file
        self.canonical_image = canonical_image

    def tearDown(self):
        self._patch.stop()
        if '.' in sys.path:
            sys.path.remove('.')

    def test_source_registered(self):
        # Hugging Face is hidden from the dropdown but remains registered for direct URLs.
        self.assertEqual(self.bs.source_choices(), ['CivitAI', 'CivArchive', 'Arc en Ciel', 'ModelScope'])
        self.assertEqual(self.bs.get_browser_source('civitai').display_name, 'CivitAI')
        self.assertEqual(self.bs.get_browser_source('huggingface').display_name, 'Hugging Face')
        self.assertFalse(self.bs.get_browser_source('huggingface').visible_in_dropdown)
        self.assertEqual(self.bs.get_browser_source('arcenciel').display_name, 'Arc en Ciel')
        self.assertEqual(self.bs.get_browser_source('modelscope').display_name, 'ModelScope')
        self.assertTrue(self.bs.get_browser_source('modelscope').visible_in_dropdown)

    def test_canonical_file_includes_legacy_metadata(self):
        file_info = self.canonical_file(
            filename='model.safetensors',
            raw={'metadata': {'size': 'full', 'fp': 'fp16'}},
        )

        self.assertEqual(file_info['format'], 'SafeTensor')
        self.assertEqual(file_info['metadata'], {
            'size': 'full',
            'fp': 'fp16',
            'format': 'SafeTensor',
        })

    def test_canonical_image_includes_legacy_shape(self):
        image = self.canonical_image(
            url='https://example.com/preview.png',
            width=1024,
            height=768,
            nsfw=4,
            prompt='test prompt',
            raw={'meta': {'negativePrompt': 'bad quality'}},
        )
        video = self.canonical_image(url='https://example.com/sample.mp4')

        self.assertEqual(image['type'], 'image')
        self.assertEqual(image['nsfwLevel'], 4)
        self.assertEqual(image['meta']['prompt'], 'test prompt')
        self.assertEqual(image['meta']['negativePrompt'], 'bad quality')
        self.assertEqual(video['type'], 'video')
        self.assertEqual(video['nsfwLevel'], 0)

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

    def test_empty_search_builds_browse_url_without_query_param(self):
        url = self.src._create_api_url(
            query='',
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

        self.assertNotIn('query=', url)
        self.assertIn('types=Checkpoint', url)
        self.assertIn('baseModels=Anima', url)
        self.assertIn('limit=20', url)
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

    def _make_response(self, json_data, status_code=200):
        response = unittest.mock.MagicMock()
        response.status_code = status_code
        response.json.return_value = json_data
        return response

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

    def test_search_fetches_details_and_returns_canonical_items(self):
        search_response = {
            'results': [
                {'kind': 'file', 'id': 'f456'},
                {'kind': 'version', 'model_id': '123', 'version_id': '456'},
            ],
            'total_hits': 2,
        }
        detail_response = {
            'id': 123,
            'name': 'Archived Model',
            'type': 'LORA',
            'version': {
                'id': 456,
                'name': 'v1',
                'baseModel': 'SDXL 1.0',
                'files': [{
                    'name': 'archived-model.safetensors',
                    'sha256': 'abc123',
                    'downloadUrl': 'https://example.com/model',
                }],
                'images': [{'url': 'https://example.com/preview.png'}],
            },
            'versions': [{'id': 456, 'name': 'v1'}],
        }

        def side_effect(url, **kwargs):
            if url.endswith('/search?q=archived&limit=10&offset=0'):
                return self._make_response(search_response)
            return self._make_response(detail_response)

        with patch('scripts.browser_sources.civarchive.requests.get') as mock_get:
            mock_get.side_effect = side_effect
            result = self.src.search(query='archived', page=1.0, page_size=10.0)

        self.assertEqual(result['metadata']['source'], 'civarchive')
        self.assertEqual(result['metadata']['totalItems'], 1)
        self.assertEqual(len(result['items']), 1)
        self.assertEqual(result['items'][0]['name'], 'Archived Model')
        self.assertEqual(result['items'][0]['modelVersions'][0]['files'][0]['name'], 'archived-model.safetensors')

    def test_empty_search_browses_default_results(self):
        search_response = {
            'results': [{'kind': 'version', 'model_id': '123', 'version_id': '456'}],
            'total_hits': 1,
        }
        detail_response = {
            'id': 123,
            'name': 'Default Browse Model',
            'type': 'Checkpoint',
            'version': {
                'id': 456,
                'name': 'v1',
                'baseModel': 'SDXL 1.0',
                'files': [{
                    'name': 'default-model.safetensors',
                    'downloadUrl': 'https://example.com/default-model',
                }],
            },
            'versions': [{'id': 456, 'name': 'v1'}],
        }

        with patch.object(
            self.src,
            '_request_json',
            side_effect=[search_response, detail_response],
        ) as mock_request:
            result = self.src.search(query='', page_size=10)

        mock_request.assert_any_call('/search', params={'limit': 10, 'offset': 0})
        self.assertEqual(result['metadata']['totalItems'], 1)
        self.assertEqual(len(result['items']), 1)
        self.assertEqual(result['items'][0]['name'], 'Default Browse Model')

    def test_deleted_filter_uses_civarchive_api_flag(self):
        search_response = {'results': [], 'total_hits': 0}

        with patch.object(self.src, '_request_json', return_value=search_response) as mock_request:
            result = self.src.search(
                query='',
                page_size=10,
                deleted_from_civitai=True,
            )

        mock_request.assert_called_once_with(
            '/search',
            params={'limit': 10, 'offset': 0, 'is_deleted': 'true'},
        )
        self.assertEqual(result['items'], [])

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



class TestHuggingFaceAdapter(unittest.TestCase):
    def setUp(self):
        self._patch = patch.dict(sys.modules, _MODULE_OVERRIDES, clear=False)
        self._patch.start()
        sys.path.insert(0, '.')

        from scripts.browser_sources.huggingface import HuggingFaceSource
        self.src = HuggingFaceSource()

    def tearDown(self):
        self._patch.stop()
        if '.' in sys.path:
            sys.path.remove('.')

    def _make_response(self, json_data, status_code=200):
        resp = unittest.mock.MagicMock()
        resp.status_code = status_code
        resp.json.return_value = json_data
        return resp

    def test_supported_search_types(self):
        self.assertEqual(self.src.supported_search_types(), ['Model name'])

    def test_supports_pagination(self):
        self.assertTrue(self.src.supports_pagination())

    def test_search_normalizes_repo_summary(self):
        search_response = [{
            'id': 'owner/cool-lora',
            'modelId': 'owner/cool-lora',
            'tags': ['lora', 'text-to-image', 'base_model:runwayml/stable-diffusion-v1-5'],
            'siblings': [
                {'rfilename': 'README.md'},
                {'rfilename': 'cool-lora.safetensors'},
                {'rfilename': 'preview.png'},
            ],
        }]
        with patch('scripts.browser_sources.huggingface.requests.get') as mock_get:
            mock_get.return_value = self._make_response(search_response)
            result = self.src.search(query='cool lora', page_size=10)

        self.assertEqual(result['metadata']['source'], 'huggingface')
        self.assertEqual(len(result['items']), 1)
        model = result['items'][0]
        self.assertEqual(model['browserSource'], 'huggingface')
        self.assertEqual(model['browserSourceId'], 'owner/cool-lora')
        self.assertEqual(model['type'], 'LORA')
        self.assertEqual(model['baseModel'], 'SD 1.5')
        version = model['modelVersions'][0]
        self.assertEqual(version['files'][0]['name'], 'cool-lora.safetensors')
        self.assertTrue(version['files'][0]['primary'])
        self.assertIn('resolve/main/cool-lora.safetensors', version['files'][0]['downloadUrl'])
        self.assertEqual(len(version['images']), 1)
        self.assertIn('resolve/main/preview.png', version['images'][0]['url'])

    def test_empty_search_browses_huggingface(self):
        search_response = [{
            'id': 'owner/browsable-checkpoint',
            'modelId': 'owner/browsable-checkpoint',
            'tags': ['stable-diffusion', 'text-to-image'],
            'siblings': [
                {'rfilename': 'browsable-checkpoint.safetensors'},
            ],
        }]
        with patch('scripts.browser_sources.huggingface.requests.get') as mock_get:
            mock_get.return_value = self._make_response(search_response)
            result = self.src.search(query='', content_type='Checkpoint', page_size=10)

        requested_url = mock_get.call_args_list[0].args[0]
        self.assertNotIn('search=', requested_url)
        self.assertIn('filter=text-to-image', requested_url)
        self.assertIn('sort=downloads', requested_url)
        self.assertEqual(len(result['items']), 1)
        self.assertEqual(result['items'][0]['name'], 'owner/browsable-checkpoint')

    def test_search_discards_repos_without_downloadable_files(self):
        search_response = [
            {
                'id': 'owner/readme-only',
                'modelId': 'owner/readme-only',
                'tags': ['stable-diffusion'],
                'siblings': [{'rfilename': 'README.md'}],
            },
            {
                'id': 'owner/has-model-file',
                'modelId': 'owner/has-model-file',
                'tags': ['stable-diffusion'],
                'siblings': [{'rfilename': 'model.safetensors'}],
            },
        ]
        with patch('scripts.browser_sources.huggingface.requests.get') as mock_get:
            mock_get.return_value = self._make_response(search_response)
            result = self.src.search(query='model', content_type='Checkpoint', page_size=10)

        self.assertEqual(len(result['items']), 1)
        self.assertEqual(result['items'][0]['browserSourceId'], 'owner/has-model-file')

    def test_checkpoint_filter_excludes_lora_results_from_text_to_image(self):
        search_response = [
            {
                'id': 'owner/anima-checkpoint',
                'modelId': 'owner/anima-checkpoint',
                'tags': ['text-to-image', 'base_model:circlestone-labs/Anima'],
                'siblings': [{'rfilename': 'anima-checkpoint.safetensors'}],
            },
            {
                'id': 'owner/anima-lora',
                'modelId': 'owner/anima-lora',
                'tags': ['text-to-image', 'lora', 'base_model:circlestone-labs/Anima'],
                'siblings': [{'rfilename': 'anima-lora.safetensors'}],
            },
        ]
        with patch('scripts.browser_sources.huggingface.requests.get') as mock_get:
            mock_get.return_value = self._make_response(search_response)
            result = self.src.search(query='anima', content_type='Checkpoint', page_size=10)

        self.assertEqual(len(result['items']), 1)
        self.assertEqual(result['items'][0]['browserSourceId'], 'owner/anima-checkpoint')
        self.assertEqual(result['items'][0]['type'], 'Checkpoint')

    def test_video_base_model_search_uses_video_pipeline_filters(self):
        text_to_video_response = [{
            'id': 'Wan-AI/Wan2.2-T2V-A14B-Diffusers',
            'modelId': 'Wan-AI/Wan2.2-T2V-A14B-Diffusers',
            'tags': ['text-to-video'],
            'pipeline_tag': 'text-to-video',
            'siblings': [{'rfilename': 'transformer/diffusion_pytorch_model.safetensors'}],
        }]
        image_to_video_response = [{
            'id': 'Wan-AI/Wan2.2-I2V-A14B-Diffusers',
            'modelId': 'Wan-AI/Wan2.2-I2V-A14B-Diffusers',
            'tags': ['image-to-video'],
            'pipeline_tag': 'image-to-video',
            'siblings': [{'rfilename': 'transformer/diffusion_pytorch_model.safetensors'}],
        }]

        with patch('scripts.browser_sources.huggingface.requests.get') as mock_get:
            mock_get.side_effect = [
                self._make_response(text_to_video_response),
                self._make_response(image_to_video_response),
            ]
            result = self.src.search(query='wan', content_type='Checkpoint', page_size=10)

        requested_urls = [call.args[0] for call in mock_get.call_args_list]
        self.assertIn('filter=text-to-video', requested_urls[0])
        self.assertIn('filter=image-to-video', requested_urls[1])
        self.assertEqual([item['browserSourceId'] for item in result['items']], [
            'Wan-AI/Wan2.2-T2V-A14B-Diffusers',
            'Wan-AI/Wan2.2-I2V-A14B-Diffusers',
        ])
        self.assertTrue(all(item['baseModel'] == 'Wan' for item in result['items']))

    def test_exact_base_model_query_filters_huggingface_results(self):
        search_response = [
            {
                'id': 'owner/real-anima',
                'modelId': 'owner/real-anima',
                'tags': ['stable-diffusion', 'base_model:anima'],
                'siblings': [{'rfilename': 'real-anima.safetensors'}],
            },
            {
                'id': 'owner/animation-helper',
                'modelId': 'owner/animation-helper',
                'tags': ['stable-diffusion', 'base_model:runwayml/stable-diffusion-v1-5'],
                'siblings': [{'rfilename': 'animation-helper.safetensors'}],
            },
            {
                'id': 'ByteDance/AnimateDiff-Lightning',
                'modelId': 'ByteDance/AnimateDiff-Lightning',
                'tags': ['stable-diffusion'],
                'siblings': [{'rfilename': 'animatediff.safetensors'}],
            },
        ]
        with patch('scripts.browser_sources.huggingface.requests.get') as mock_get:
            mock_get.return_value = self._make_response(search_response)
            result = self.src.search(query='anima', content_type='Checkpoint', page_size=10)

        self.assertEqual(len(result['items']), 1)
        self.assertEqual(result['items'][0]['browserSourceId'], 'owner/real-anima')
        self.assertEqual(result['items'][0]['baseModel'], 'Anima')

    def test_non_base_model_query_keeps_text_search_results(self):
        search_response = [{
            'id': 'owner/anime-style',
            'modelId': 'owner/anime-style',
            'tags': ['stable-diffusion', 'base_model:runwayml/stable-diffusion-v1-5'],
            'siblings': [{'rfilename': 'anime-style.safetensors'}],
        }]
        with patch('scripts.browser_sources.huggingface.requests.get') as mock_get:
            mock_get.return_value = self._make_response(search_response)
            result = self.src.search(query='anime', content_type='Checkpoint', page_size=10)

        self.assertEqual(len(result['items']), 1)
        self.assertEqual(result['items'][0]['browserSourceId'], 'owner/anime-style')

    def test_search_fetches_enough_rows_for_client_side_pagination(self):
        search_response = []
        for index in range(4):
            search_response.append({
                'id': f'owner/model-{index}',
                'modelId': f'owner/model-{index}',
                'tags': ['stable-diffusion'],
                'siblings': [{'rfilename': f'model-{index}.safetensors'}],
            })

        with patch('scripts.browser_sources.huggingface.requests.get') as mock_get:
            mock_get.return_value = self._make_response(search_response)
            result = self.src.search(query='model', content_type='Checkpoint', page=2, page_size=2)

        requested_url = mock_get.call_args_list[0].args[0]
        self.assertIn('limit=4', requested_url)
        self.assertEqual([item['browserSourceId'] for item in result['items']], [
            'owner/model-2',
            'owner/model-3',
        ])

    def test_diffusers_repo_prefers_root_checkpoint_over_components(self):
        search_response = [{
            'id': 'owner/diffusers-checkpoint',
            'modelId': 'owner/diffusers-checkpoint',
            'tags': ['stable-diffusion'],
            'siblings': [
                {'rfilename': 'safety_checker/model.safetensors'},
                {'rfilename': 'text_encoder/model.safetensors'},
                {'rfilename': 'unet/diffusion_pytorch_model.safetensors'},
                {'rfilename': 'v1-5-pruned-emaonly.safetensors'},
            ],
        }]
        with patch('scripts.browser_sources.huggingface.requests.get') as mock_get:
            mock_get.return_value = self._make_response(search_response)
            result = self.src.search(query='diffusers', content_type='Checkpoint', page_size=10)

        files = result['items'][0]['modelVersions'][0]['files']
        self.assertEqual(files[0]['name'], 'v1-5-pruned-emaonly.safetensors')
        self.assertTrue(files[0]['primary'])
        self.assertIn(
            'resolve/main/v1-5-pruned-emaonly.safetensors',
            files[0]['downloadUrl'],
        )

    def test_checkpoint_search_discards_auxiliary_component_only_repos(self):
        search_response = [{
            'id': 'owner/gguf-with-vae-only',
            'modelId': 'owner/gguf-with-vae-only',
            'tags': ['text-to-video', 'base_model:Wan-AI/Wan2.2-T2V-A14B'],
            'pipeline_tag': 'text-to-video',
            'siblings': [
                {'rfilename': 'HighNoise/model.Q4_K_M.gguf'},
                {'rfilename': 'VAE/Wan2.1_VAE.safetensors'},
                {'rfilename': 'clip_vision_h_fp16.safetensors'},
                {'rfilename': 'umt5xxl_fp8_e4m3fn_scaled.safetensors'},
                {'rfilename': 'wan2.2_i2v_lite_lora_high_noise.safetensors'},
            ],
        }]
        with patch('scripts.browser_sources.huggingface.requests.get') as mock_get:
            mock_get.return_value = self._make_response(search_response)
            result = self.src.search(query='wan', content_type='Checkpoint', page_size=10)

        self.assertEqual(result['items'], [])

    def test_get_model_fetches_repo_detail_and_files(self):
        repo_detail = {
            'id': 'owner/cool-lora',
            'modelId': 'owner/cool-lora',
            'tags': ['lora'],
        }
        tree = [
            {'path': 'cool-lora.safetensors', 'size': 1024000},
            {'path': 'preview.jpg', 'size': 51200},
        ]

        def side_effect(url, **kwargs):
            if '/tree/main' in url:
                return self._make_response(tree)
            return self._make_response(repo_detail)

        with patch('scripts.browser_sources.huggingface.requests.get') as mock_get:
            mock_get.side_effect = side_effect
            model = self.src.get_model('owner/cool-lora')

        self.assertEqual(model['browserSource'], 'huggingface')
        self.assertEqual(model['browserSourceId'], 'owner/cool-lora')
        self.assertEqual(model['type'], 'LORA')
        version = model['modelVersions'][0]
        self.assertEqual(len(version['files']), 1)
        self.assertEqual(version['files'][0]['sizeBytes'], 1024000)

    def test_get_download_url_builds_resolve_url(self):
        file_info = {
            'name': 'cool-lora.safetensors',
            'browserSourceFileRaw': {
                'repo_id': 'owner/cool-lora',
                'path': 'cool-lora.safetensors',
            },
        }
        url = self.src.get_download_url(file_info)
        self.assertEqual(url, 'https://huggingface.co/owner/cool-lora/resolve/main/cool-lora.safetensors')

    def test_checkpoint_only_lists_safetensors(self):
        search_response = [{
            'id': 'owner/cool-checkpoint',
            'modelId': 'owner/cool-checkpoint',
            'tags': ['stable-diffusion'],
            'siblings': [
                {'rfilename': 'model.safetensors'},
                {'rfilename': 'model.ckpt'},
                {'rfilename': 'model.pt'},
            ],
        }]
        with patch('scripts.browser_sources.huggingface.requests.get') as mock_get:
            mock_get.return_value = self._make_response(search_response)
            result = self.src.search(query='cool checkpoint', content_type='Checkpoint', page_size=10)

        files = result['items'][0]['modelVersions'][0]['files']
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0]['name'], 'model.safetensors')

    def test_readme_enriches_base_model_and_triggers(self):
        repo_detail = {
            'id': 'owner/lora-with-readme',
            'modelId': 'owner/lora-with-readme',
            'tags': ['lora'],
        }
        tree = [{'path': 'lora.safetensors', 'size': 1024000}]
        readme = (
            "# My LoRA\n\n"
            "Base model: SDXL\n\n"
            "Trigger words: style_of_mylora, mylora\n\n"
            "Enjoy!"
        )

        def side_effect(url, **kwargs):
            if url.endswith('/README.md'):
                resp = self._make_response({})
                resp.status_code = 200
                resp.text = readme
                resp.json.side_effect = Exception('not json')
                return resp
            if '/tree/main' in url:
                return self._make_response(tree)
            return self._make_response(repo_detail)

        with patch('scripts.browser_sources.huggingface.requests.get') as mock_get:
            mock_get.side_effect = side_effect
            model = self.src.get_model('owner/lora-with-readme')

        version = model['modelVersions'][0]
        self.assertEqual(model['baseModel'], 'SDXL')
        self.assertEqual(set(version['trainedWords']), {'style_of_mylora', 'mylora'})



class TestArcencielAdapter(unittest.TestCase):
    def setUp(self):
        self._patch = patch.dict(sys.modules, _MODULE_OVERRIDES, clear=False)
        self._patch.start()
        sys.path.insert(0, '.')

        from scripts.browser_sources.arcenciel import ArcencielSource
        self.src = ArcencielSource()

    def tearDown(self):
        self._patch.stop()
        if '.' in sys.path:
            sys.path.remove('.')

    def _make_response(self, json_data, status_code=200):
        resp = unittest.mock.MagicMock()
        resp.status_code = status_code
        resp.json.return_value = json_data
        return resp

    def test_supported_search_types(self):
        self.assertEqual(self.src.supported_search_types(), ['Model name'])

    def test_supports_pagination(self):
        self.assertTrue(self.src.supports_pagination())

    def test_search_normalizes_model(self):
        search_response = {
            'page': 1,
            'limit': 20,
            'totalCount': 1,
            'totalPages': 1,
            'data': [{
                'id': 123,
                'title': 'Cool Arcenciel LoRA',
                'description': 'A cool LoRA',
                'type': 'LORA',
                'tags': [{'id': 1, 'name': 'character'}],
                'uploader': {'id': 1, 'username': 'artist'},
                'versionOrder': [456],
                'versions': [{
                    'id': 456,
                    'versionName': 'v1',
                    'fileName': 'cool.safetensors',
                    'filePath': 'models/Lora/cool.safetensors',
                    'fileSizeKb': 10240,
                    'sha256': 'a' * 64,
                    'baseModel': 'Anima',
                    'activationTags': ['cooltag'],
                    'downloadCount': 42,
                }],
            }],
        }
        with patch('scripts.browser_sources.arcenciel.requests.get') as mock_get:
            mock_get.return_value = self._make_response(search_response)
            result = self.src.search(query='cool', page_size=20)

        self.assertEqual(result['metadata']['source'], 'arcenciel')
        self.assertEqual(result['metadata']['totalItems'], 1)
        self.assertEqual(result['metadata']['totalPages'], 1)
        self.assertEqual(len(result['items']), 1)
        model = result['items'][0]
        self.assertEqual(model['browserSource'], 'arcenciel')
        self.assertEqual(model['browserSourceId'], '123')
        self.assertEqual(model['type'], 'LORA')
        self.assertEqual(model['creator']['username'], 'artist')
        version = model['modelVersions'][0]
        self.assertEqual(version['baseModel'], 'Anima')
        self.assertEqual(version['trainedWords'], ['cooltag'])
        self.assertEqual(version['files'][0]['name'], 'cool.safetensors')
        self.assertIn('uploads.arcenciel.io/api/models/123/versions/456/download', version['files'][0]['downloadUrl'])

    def test_empty_search_browses_arcenciel(self):
        search_response = {
            'page': 1,
            'limit': 10,
            'totalCount': 342,
            'totalPages': 35,
            'data': [{
                'id': 14686,
                'title': 'AdAstra [Anima]',
                'description': 'desc',
                'type': 'CHECKPOINT',
                'uploader': {'id': 132, 'username': 'Garbo'},
                'versionOrder': [16445],
                'versions': [{
                    'id': 16445,
                    'versionName': 'v10',
                    'fileName': 'Adastra_Anima_V10.safetensors',
                    'fileSizeKb': 4084210,
                    'sha256': 'b' * 64,
                    'baseModel': 'Anima',
                    'activationTags': 'masterpiece, best quality\nadastra',
                    'downloadCount': 18,
                }],
            }],
        }
        with patch('scripts.browser_sources.arcenciel.requests.get') as mock_get:
            mock_get.return_value = self._make_response(search_response)
            result = self.src.search(query='', page_size=10)

        requested_url = mock_get.call_args_list[0].args[0]
        self.assertNotIn('q=', requested_url)
        self.assertIn('limit=10', requested_url)
        self.assertEqual(result['metadata']['source'], 'arcenciel')
        self.assertEqual(result['metadata']['totalItems'], 342)
        self.assertEqual(result['metadata']['totalPages'], 35)
        self.assertEqual(len(result['items']), 1)
        version = result['items'][0]['modelVersions'][0]
        self.assertEqual(version['trainedWords'], ['masterpiece', 'best quality', 'adastra'])

    def test_search_filters_arcenciel_content_type_and_base_model_locally(self):
        search_response = {
            'page': 1,
            'limit': 40,
            'totalCount': 3,
            'totalPages': 1,
            'data': [
                {
                    'id': 1,
                    'title': 'Anima LoRA',
                    'type': 'LORA',
                    'versions': [{
                        'id': 11,
                        'versionName': 'v1',
                        'fileName': 'anima-lora.safetensors',
                        'baseModel': 'Anima',
                    }],
                },
                {
                    'id': 2,
                    'title': 'Mixed Checkpoint',
                    'type': 'CHECKPOINT',
                    'versionOrder': [22, 21],
                    'versions': [
                        {
                            'id': 21,
                            'versionName': 'Illustrious',
                            'fileName': 'mixed-illustrious.safetensors',
                            'baseModel': 'Illustrious',
                        },
                        {
                            'id': 22,
                            'versionName': 'Anima',
                            'fileName': 'mixed-anima.safetensors',
                            'baseModel': 'Anima',
                        },
                    ],
                },
                {
                    'id': 3,
                    'title': 'Illustrious Checkpoint',
                    'type': 'CHECKPOINT',
                    'versions': [{
                        'id': 31,
                        'versionName': 'v1',
                        'fileName': 'illustrious.safetensors',
                        'baseModel': 'Illustrious',
                    }],
                },
            ],
        }
        with patch('scripts.browser_sources.arcenciel.requests.get') as mock_get:
            mock_get.return_value = self._make_response(search_response)
            result = self.src.search(query='', content_type='Checkpoint', base_filter=['Anima'], page_size=10)

        requested_url = mock_get.call_args_list[0].args[0]
        self.assertIn('limit=40', requested_url)
        self.assertNotIn('type=', requested_url)
        self.assertEqual(result['metadata']['source'], 'arcenciel')
        self.assertEqual(result['metadata']['totalItems'], 1)
        self.assertEqual(len(result['items']), 1)
        model = result['items'][0]
        self.assertEqual(model['name'], 'Mixed Checkpoint')
        self.assertEqual(model['type'], 'Checkpoint')
        self.assertEqual(model['baseModel'], 'Anima')
        self.assertEqual([version['baseModel'] for version in model['modelVersions']], ['Anima'])

    def test_get_download_url_builds_direct_url(self):
        file_info = {
            'name': 'cool.safetensors',
            'browserSourceFileRaw': {'model_id': 123, 'version_id': 456},
        }
        url = self.src.get_download_url(file_info)
        self.assertEqual(url, 'https://uploads.arcenciel.io/api/models/123/versions/456/download')


class TestModelScopeAdapter(unittest.TestCase):
    def setUp(self):
        self._patch = patch.dict(sys.modules, _MODULE_OVERRIDES, clear=False)
        self._patch.start()
        sys.path.insert(0, '.')

        from scripts.browser_sources.modelscope import ModelScopeSource
        self.src = ModelScopeSource()

    def tearDown(self):
        self._patch.stop()
        if '.' in sys.path:
            sys.path.remove('.')

    def _make_response(self, json_data, status_code=200):
        resp = unittest.mock.MagicMock()
        resp.status_code = status_code
        resp.json.return_value = json_data
        return resp

    def test_supported_search_types(self):
        self.assertEqual(self.src.supported_search_types(), ['Model name'])

    def test_supports_pagination(self):
        self.assertTrue(self.src.supports_pagination())

    def test_search_normalizes_muse_model(self):
        search_response = {
            'Code': 200,
            'Data': {
                'Model': {
                    'TotalCount': 1,
                    'Models': [{
                        'Id': 143351,
                        'Name': 'Qwen-Image-Edit-2511-Multiple-Angles-LoRA',
                        'Path': 'fal',
                        'Tags': ['text-to-image'],
                        'Libraries': ['safetensors', 'pytorch'],
                        'Downloads': 109,
                        'Stars': 5,
                        'Description': 'A LoRA for Qwen Image',
                        'MuseInfo': {
                            'model': {
                                'modelType': 'LoRA',
                                'stableDiffusionVersion': 'QWEN_IMAGE_20_B',
                            },
                            'versions': [{
                                'id': 843075,
                                'coverImages': [
                                    {'url': 'https://resources.modelscope.cn/cover-images/preview.png'},
                                ],
                                'modelVersion': {
                                    'id': 843075,
                                    'versionName': '20260617081836',
                                    'triggerWords': ['qwen image edit'],
                                },
                                'stats': {
                                    'fileList': ['qwen-image-edit-2511-multiple-angles-lora.safetensors'],
                                    'fileSizes': [134],
                                    'totalSize': 134,
                                },
                            }],
                        },
                    }],
                },
            },
        }
        with patch('scripts.browser_sources.modelscope.requests.put') as mock_put:
            mock_put.return_value = self._make_response(search_response)
            result = self.src.search(query='qwen lora', page_size=10)

        self.assertEqual(result['metadata']['source'], 'modelscope')
        self.assertEqual(len(result['items']), 1)
        model = result['items'][0]
        self.assertEqual(model['browserSource'], 'modelscope')
        self.assertEqual(model['browserSourceId'], 'fal/Qwen-Image-Edit-2511-Multiple-Angles-LoRA')
        self.assertEqual(model['type'], 'LORA')
        self.assertEqual(model['baseModel'], 'Qwen Image')
        version = model['modelVersions'][0]
        self.assertEqual(version['name'], '20260617081836')
        self.assertEqual(version['trainedWords'], ['qwen image edit'])
        self.assertEqual(version['files'][0]['name'], 'qwen-image-edit-2511-multiple-angles-lora.safetensors')
        self.assertTrue(version['files'][0]['primary'])
        self.assertIn('resolve/master/qwen-image-edit-2511-multiple-angles-lora.safetensors', version['files'][0]['downloadUrl'])
        self.assertEqual(len(version['images']), 1)
        self.assertEqual(version['images'][0]['url'], 'https://resources.modelscope.cn/cover-images/preview.png')

    def test_search_filters_modelscope_content_type_and_base_model(self):
        search_response = {
            'Code': 200,
            'Data': {
                'Model': {
                    'Models': [
                        {
                            'Id': 1,
                            'Name': 'Anima-LoRA',
                            'Path': 'silverlong',
                            'Tags': [],
                            'Libraries': ['safetensors'],
                            'MuseInfo': {
                                'model': {'modelType': 'LoRA', 'stableDiffusionVersion': 'ANIMA'},
                                'versions': [{
                                    'modelVersion': {'versionName': 'v1'},
                                    'stats': {'fileList': ['anima-lora.safetensors']},
                                }],
                            },
                        },
                        {
                            'Id': 2,
                            'Name': 'Flux-Checkpoint',
                            'Path': 'owner',
                            'Tags': [],
                            'Libraries': ['safetensors'],
                            'MuseInfo': {
                                'model': {'modelType': 'Checkpoint', 'stableDiffusionVersion': 'FLUX_1_D'},
                                'versions': [{
                                    'modelVersion': {'versionName': 'v1'},
                                    'stats': {'fileList': ['flux.safetensors']},
                                }],
                            },
                        },
                    ],
                },
            },
        }
        with patch('scripts.browser_sources.modelscope.requests.put') as mock_put:
            mock_put.return_value = self._make_response(search_response)
            result = self.src.search(query='', content_type='Checkpoint', base_filter=['FLUX.1'], page_size=10)

        self.assertEqual(len(result['items']), 1)
        self.assertEqual(result['items'][0]['browserSourceId'], 'owner/Flux-Checkpoint')
        self.assertEqual(result['items'][0]['type'], 'Checkpoint')
        self.assertEqual(result['items'][0]['baseModel'], 'FLUX.1')

    def test_search_uses_model_infos_when_muse_missing(self):
        search_response = {
            'Code': 200,
            'Data': {
                'Model': {
                    'Models': [{
                        'Id': 653643,
                        'Name': 'Anima',
                        'Path': 'circlestone-labs',
                        'Tags': ['diffusion-single-file'],
                        'Libraries': ['safetensors', 'pytorch'],
                        'BaseModel': ['circlestone-labs/Anima'],
                        'ModelInfos': {
                            'safetensor': {
                                'files': [
                                    {'name': 'split_files/diffusion_models/anima-aesthetic-v1.0.safetensors', 'size': 4182230656, 'sha256': 'abc'},
                                ],
                            },
                        },
                    }],
                },
            },
        }
        with patch('scripts.browser_sources.modelscope.requests.put') as mock_put:
            mock_put.return_value = self._make_response(search_response)
            result = self.src.search(query='anima', page_size=10)

        self.assertEqual(len(result['items']), 1)
        version = result['items'][0]['modelVersions'][0]
        self.assertEqual(version['files'][0]['name'], 'anima-aesthetic-v1.0.safetensors')
        self.assertEqual(version['files'][0]['sizeBytes'], 4182230656)
        self.assertEqual(version['files'][0]['sha256'], 'ABC')

    def test_get_model_fetches_repo_detail(self):
        repo_detail = {
            'Code': 200,
            'Data': {
                'Id': 653643,
                'Name': 'Anima',
                'Path': 'circlestone-labs',
                'Tags': ['diffusion-single-file'],
                'Libraries': ['safetensors', 'pytorch'],
                'BaseModel': ['Anima'],
                'ModelInfos': {
                    'safetensor': {
                        'files': [
                            {'name': 'anima.safetensors', 'size': 1024000},
                        ],
                    },
                },
            },
        }
        with patch('scripts.browser_sources.modelscope.requests.get') as mock_get:
            mock_get.return_value = self._make_response(repo_detail)
            model = self.src.get_model('circlestone-labs/Anima')

        self.assertEqual(model['browserSource'], 'modelscope')
        self.assertEqual(model['browserSourceId'], 'circlestone-labs/Anima')
        self.assertEqual(model['type'], 'Checkpoint')
        version = model['modelVersions'][0]
        self.assertEqual(len(version['files']), 1)
        self.assertEqual(version['files'][0]['sizeBytes'], 1024000)

    def test_get_download_url_builds_resolve_url(self):
        file_info = {
            'name': 'anima.safetensors',
            'browserSourceFileRaw': {
                'repo_id': 'circlestone-labs/Anima',
                'path': 'anima.safetensors',
                'revision': 'master',
            },
        }
        url = self.src.get_download_url(file_info)
        self.assertEqual(url, 'https://www.modelscope.cn/models/circlestone-labs/Anima/resolve/master/anima.safetensors')


class TestUrlParser(unittest.TestCase):
    """Tests for the direct-URL parser used by the Browser's URL search mode."""

    def setUp(self):
        self._patch = patch.dict(sys.modules, _MODULE_OVERRIDES, clear=False)
        self._patch.start()
        sys.path.insert(0, '.')

        from scripts.browser_sources.url_parser import parse_model_url
        self.parse_model_url = parse_model_url

    def tearDown(self):
        self._patch.stop()
        if '.' in sys.path:
            sys.path.remove('.')

    def _make_mock_adapter(self, model_name, source_name):
        adapter = MagicMock()
        adapter.name = source_name
        adapter.get_model.return_value = {
            'id': 'parsed-id',
            'name': model_name,
            'type': 'LORA',
            'browserSource': source_name,
            'browserSourceId': 'parsed-id',
            'modelVersions': [],
        }
        return adapter

    def test_invalid_url_returns_error(self):
        self.assertEqual(self.parse_model_url(''), 'invalid_url')
        self.assertEqual(self.parse_model_url('not-a-url'), 'invalid_url')
        self.assertEqual(self.parse_model_url('https://example.com/models/123'), 'invalid_url')

    def test_huggingface_url_parses_repo_id(self):
        
        with patch('scripts.browser_sources.url_parser.get_browser_source') as mock_get:
            mock_get.return_value = self._make_mock_adapter('HF Model', 'huggingface')
            result = self.parse_model_url('https://huggingface.co/owner/cool-lora')

        self.assertIsInstance(result, dict)
        self.assertEqual(result['metadata']['totalItems'], 1)
        mock_get.assert_called_once_with('huggingface')
        mock_get.return_value.get_model.assert_called_once_with('owner/cool-lora')

    def test_huggingface_url_strips_branch_and_trailing_slash(self):
        
        with patch('scripts.browser_sources.url_parser.get_browser_source') as mock_get:
            mock_get.return_value = self._make_mock_adapter('HF Model', 'huggingface')
            self.parse_model_url('https://huggingface.co/owner/cool-lora/tree/main/')
            mock_get.return_value.get_model.assert_called_once_with('owner/cool-lora')

    def test_civitai_model_url_extracts_id(self):
        
        with patch('scripts.browser_sources.url_parser.get_browser_source') as mock_get:
            mock_get.return_value = self._make_mock_adapter('CivitAI Model', 'civitai')
            self.parse_model_url('https://civitai.com/models/12345-model-name')
            mock_get.return_value.get_model.assert_called_once_with('12345')

    def test_civitai_download_url_resolves_version_to_model(self):
        
        with patch('scripts.browser_sources.url_parser.get_browser_source') as mock_get, \
             patch('scripts.browser_sources.url_parser._api.request_civit_api') as mock_api:
            mock_api.return_value = {'modelId': 99999}
            mock_get.return_value = self._make_mock_adapter('CivitAI Model', 'civitai')
            self.parse_model_url('https://civitai.com/api/download/models/67890')
            mock_get.return_value.get_model.assert_called_once_with('99999')

    def test_civarchive_url_extracts_id(self):
        
        with patch('scripts.browser_sources.url_parser.get_browser_source') as mock_get:
            mock_get.return_value = self._make_mock_adapter('CivArchive Model', 'civarchive')
            self.parse_model_url('https://civarchive.com/models/12345')
            mock_get.return_value.get_model.assert_called_once_with('12345')

    def test_arcenciel_url_extracts_id(self):
        
        with patch('scripts.browser_sources.url_parser.get_browser_source') as mock_get:
            mock_get.return_value = self._make_mock_adapter('Arc Model', 'arcenciel')
            self.parse_model_url('https://arcenciel.io/models/12345')
            mock_get.return_value.get_model.assert_called_once_with('12345')

    def test_modelscope_url_extracts_repo_id(self):
        
        with patch('scripts.browser_sources.url_parser.get_browser_source') as mock_get:
            mock_get.return_value = self._make_mock_adapter('MS Model', 'modelscope')
            self.parse_model_url('https://www.modelscope.cn/models/owner/cool-lora')
            mock_get.return_value.get_model.assert_called_once_with('owner/cool-lora')

    def test_modelscope_url_strips_summary_and_files(self):
        
        with patch('scripts.browser_sources.url_parser.get_browser_source') as mock_get:
            mock_get.return_value = self._make_mock_adapter('MS Model', 'modelscope')
            self.parse_model_url('https://www.modelscope.cn/models/owner/cool-lora/summary')
            mock_get.return_value.get_model.assert_called_once_with('owner/cool-lora')

    def test_not_found_adapter_returns_error(self):
        
        with patch('scripts.browser_sources.url_parser.get_browser_source') as mock_get:
            mock_get.return_value = None
            self.assertEqual(self.parse_model_url('https://huggingface.co/owner/cool-lora'), 'error')

    def test_model_not_found_returns_not_found(self):
        
        with patch('scripts.browser_sources.url_parser.get_browser_source') as mock_get:
            adapter = MagicMock()
            adapter.name = 'huggingface'
            adapter.get_model.return_value = None
            mock_get.return_value = adapter
            self.assertEqual(self.parse_model_url('https://huggingface.co/owner/cool-lora'), 'not_found')


if __name__ == '__main__':
    unittest.main()
