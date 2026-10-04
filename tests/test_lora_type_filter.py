"""The single LORA filter includes LoCon and DoRA without changing model types."""

import json
import os
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from test_civarchive_recovered_html import _RecoveredTestCase


class TestLoraTypeFilter(_RecoveredTestCase):
    def _civitai_url(self, content_type):
        source = self.api._browser_sources.get_browser_source('civitai')
        return source._create_api_url(
            query='', search_type='Model name', content_type=content_type,
            base_filter=['Anima'], sort='Newest', period='Month', nsfw=False,
            exact=True, page_size=20, only_liked=False,
        )

    def test_civitai_lora_filter_includes_all_three_types_without_duplicates(self):
        for selection, expected in (
            ('LORA', ['LORA', 'LoCon', 'DoRA']),
            (['LORA'], ['LORA', 'LoCon', 'DoRA']),
            (['Checkpoint', 'LORA', 'LoCon', 'DoRA'], ['Checkpoint', 'LORA', 'LoCon', 'DoRA']),
        ):
            with self.subTest(selection=selection):
                original = list(selection) if isinstance(selection, list) else selection
                params = parse_qs(urlparse(self._civitai_url(selection)).query)
                self.assertEqual(params['types'], expected)
                self.assertEqual(params['baseModels'], ['Anima'])
                self.assertEqual(params['nsfw'], ['false'])
                self.assertEqual(selection, original)

    def test_legacy_civitai_lora_filter_includes_all_three_types(self):
        url = self.api.create_api_url(content_type=['LORA'], tile_count=20)
        self.assertEqual(parse_qs(urlparse(url).query)['types'], ['LORA', 'LoCon', 'DoRA'])

    def test_unrelated_or_empty_content_filters_are_preserved(self):
        for selection, expected in (
            (['Checkpoint', 'VAE'], ['Checkpoint', 'VAE']),
            (['LoCon'], ['LoCon']),
            (['DoRA'], ['DoRA']),
            ([], None),
            (None, None),
        ):
            with self.subTest(selection=selection):
                params = parse_qs(urlparse(self._civitai_url(selection)).query)
                self.assertEqual(params.get('types'), expected)

    def test_other_source_filters_accept_the_whole_lora_group(self):
        for name in ('arcenciel', 'modelscope', 'huggingface'):
            with self.subTest(source=name):
                source = self.api._browser_sources.get_browser_source(name)
                targets = source._resolve_content_type_filter(['LORA'])
                for model_type in ('LORA', 'LoCon', 'DoRA'):
                    self.assertTrue(source._matches_content_type_filter({'type': model_type}, targets),
                                    f'{name} must include {model_type}')
                self.assertFalse(source._matches_content_type_filter({'type': 'Checkpoint'}, targets))

    def test_civarchive_merges_type_searches_before_deduplicating_and_paginating(self):
        source = self.api._browser_sources.get_browser_source('civarchive')
        rows = {'LORA': [1, 1, 2], 'LoCon': [3, 3], 'DoRA': [4]}
        model_types = {1: 'LORA', 2: 'LORA', 3: 'LoCon', 4: 'DoRA'}

        def serve(path, params=None):
            if path == '/search':
                self.assertEqual(params['base_model'], 'Anima')
                self.assertEqual(params['is_deleted'], 'true')
                return {'results': [{'model_id': mid} for mid in rows[params['type']]]}
            mid = int(path.rsplit('/', 1)[1])
            return {
                'id': mid, 'name': f'Model {mid}', 'type': model_types[mid],
                'version': {'id': mid * 10, 'name': 'v1', 'baseModel': 'Anima',
                            'files': [{'name': f'{mid}.safetensors'}]},
            }

        with patch.object(source, '_request_json', side_effect=serve):
            first = source.search(content_type=['LORA'], base_filter=['Anima'],
                                  deleted_from_civitai=True, page_size=2, page=1)
            second = source.search(content_type=['LORA'], base_filter=['Anima'],
                                   deleted_from_civitai=True, page_size=2, page=2)
        self.assertEqual([item['name'] for item in first['items']], ['Model 1', 'Model 2'])
        self.assertEqual([item['type'] for item in second['items']], ['LoCon', 'DoRA'])
        self.assertEqual(first['metadata']['totalItems'], 4)
        self.assertEqual(first['metadata']['totalPages'], 2)
        self.assertIsNotNone(first['metadata']['nextPage'])
        self.assertIsNone(second['metadata'].get('nextPage'))

    def test_civarchive_does_not_hide_a_failed_group_search(self):
        source = self.api._browser_sources.get_browser_source('civarchive')

        def serve(path, params=None):
            return 'rate_limited' if params['type'] == 'LoCon' else {'results': []}

        with patch.object(source, '_request_json', side_effect=serve):
            self.assertEqual(source.search(content_type=['LORA']), 'rate_limited')

    def test_update_grid_lora_filter_includes_locon_and_dora(self):
        entries = [
            {'model_id': mid, 'model_name': f'{kind} update', 'model_type': kind}
            for mid, kind in enumerate(('LORA', 'LoCon', 'DoRA', 'Checkpoint'), start=1)
        ]
        with patch.object(self.gl, 'update_items', entries):
            html = self.api.update_mode_page_html(['LORA'], None, 20, 1)[0]
        for kind in ('LORA', 'LoCon', 'DoRA'):
            self.assertIn(f'{kind} update', html)
        self.assertNotIn('Checkpoint update', html)

    def _library(self):
        primary = os.path.join(self.tmp, 'primary')
        extra = os.path.join(self.tmp, 'extra')
        os.makedirs(primary)
        os.makedirs(extra)
        listings = []
        paths = {}
        for mid, kind in enumerate(('LORA', 'LoCon', 'DoRA'), start=1):
            folder = extra if kind == 'DoRA' else primary
            stem = os.path.join(folder, kind)
            path = stem + '.safetensors'
            with open(path, 'w', encoding='utf-8'):
                pass
            listing = {
                'id': mid, 'name': kind, 'type': kind, 'tags': ['utility'],
                'description': '', 'creator': {'username': 'test'},
                'modelVersions': [{
                    'id': mid * 10, 'name': 'v1', 'baseModel': 'Anima',
                    'files': [{'name': kind + '.safetensors', 'hashes': {'SHA256': str(mid) * 64}}],
                    'images': [],
                }],
            }
            self._write(stem + '.api_info.json', listing)
            self._write(stem + '.json', {'modelId': mid, 'modelVersionId': mid * 10,
                                         'baseModel': 'Anima', 'lora_category': 'Utility'})
            paths[path] = mid
            listings.append(listing)
        folder_patch = patch.object(self.api, 'contenttype_folder',
                                    lambda kind, *args, **kwargs: primary if kind in ('LORA', 'LoCon', 'DoRA') else None)
        folder_patch.start()
        self.addCleanup(folder_patch.stop)
        for attr, value in (('lora_dir', primary), ('lora_dirs', [extra])):
            patcher = patch.object(self.api.cmd_opts, attr, value, create=True)
            patcher.start()
            self.addCleanup(patcher.stop)
        return paths, listings

    def test_local_lora_browser_keeps_all_three_types_including_extra_directories(self):
        paths, listings = self._library()
        response = self.api.requests.Response()
        response.status_code = 200
        response._content = json.dumps({'items': listings}).encode()
        browser_data = {'items': [{'name': 'Browser state'}]}
        with patch.object(self.gl, 'json_data', browser_data), \
                patch.object(self.fm, 'get_models', side_effect=lambda path, **kwargs: paths[path]), \
                patch.object(self.api.requests, 'get', return_value=response), \
                patch.object(self.api, 'model_list_html', return_value='local cards'):
            self.fm.render_local_browser(['LORA'], None, 'Model name', '', 20, False)
            self.assertEqual({item['type'] for item in self.gl.local_json_data['items']},
                             {'LORA', 'LoCon', 'DoRA'})
            self.assertIs(self.gl.json_data, browser_data)

    def test_loradex_scans_all_three_types_including_extra_directories(self):
        paths, _ = self._library()
        data = self.fm.scan_lora_dex_data()
        self.assertEqual({row['file_path'] for row in data}, set(paths))
        self.assertEqual({row['name'] for row in data}, {'LORA', 'LoCon', 'DoRA'})
