"""Qwen 2.1 and MiniMax H3 remain distinct through discovery and organization."""

import ast
import json
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from test_civarchive_recovered_html import _RecoveredTestCase


class TestNewBaseModels(_RecoveredTestCase):
    def _choices(self, response):
        # Load the shipped function without registering Forge's Gradio UI.
        path = Path(__file__).resolve().parents[1] / 'scripts' / 'civitai_gui.py'
        tree = ast.parse(path.read_text(encoding='utf-8'))
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                    and n.name == 'get_base_models')
        namespace = {'_api': self.api, 'json': json, 'print': lambda *args: None}
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), namespace)
        with patch.object(self.api, 'request_civit_api', return_value=response):
            return namespace['get_base_models']()

    def test_filters_include_new_models_when_api_cannot_supply_choices(self):
        for response in ('timeout', {'items': [], 'metadata': {}},
                         {'error': {'message': 'invalid json'}}):
            with self.subTest(response=response):
                choices = self._choices(response)
                self.assertIn('Qwen 2.1', choices)
                self.assertIn('MiniMax H3', choices)
                self.assertIn('Qwen', choices)

    def test_older_remote_choices_do_not_remove_new_models(self):
        response = {'error': {'message': json.dumps([
            {'errors': [[{'values': ['Qwen', 'Future model', 'Qwen']}]]}
        ])}}
        choices = self._choices(response)
        self.assertIn('Qwen 2.1', choices)
        self.assertIn('MiniMax H3', choices)
        self.assertIn('Future model', choices)
        self.assertEqual(choices.count('Qwen'), 1)

    def test_versioned_badges_do_not_fall_back_to_generic_qwen(self):
        for base, badge in (('Qwen', 'Qwen'), ('Qwen 2.1', 'Q2.1'),
                            ('Qwen 2.1 variant', 'Q2.1'),
                            ('MiniMax H3', 'H3'), ('minimax h3 turbo', 'H3')):
            with self.subTest(base=base):
                self.assertEqual(self.api.get_base_model_short(base), badge)

    def test_organization_keeps_new_architectures_in_separate_folders(self):
        with patch.object(self.fm.opts, 'civitai_neo_model_categories', None, create=True):
            for base in ('Qwen', 'Qwen 2.1', 'MiniMax H3'):
                with self.subTest(base=base):
                    self.assertEqual(self.fm.normalize_base_model(base), base)

    def test_sources_send_canonical_base_names_without_renaming(self):
        civitai = self.api._browser_sources.get_browser_source('civitai')
        archive = self.api._browser_sources.get_browser_source('civarchive')
        for base in ('Qwen 2.1', 'MiniMax H3'):
            with self.subTest(base=base):
                url = civitai._create_api_url(
                    query='', search_type='Model name', content_type=['Checkpoint'],
                    base_filter=[base], sort='Newest', period='AllTime', nsfw=False,
                    exact=True, page_size=20, only_liked=False,
                )
                self.assertEqual(parse_qs(urlparse(url).query)['baseModels'], [base])
                with patch.object(archive, '_request_json', return_value={'results': []}) as request:
                    archive.search(base_filter=[base], content_type=['Checkpoint'])
                self.assertEqual(request.call_args.kwargs['params']['base_model'], base)

    def test_repository_metadata_and_filters_use_the_same_base_names(self):
        for name in ('huggingface', 'modelscope'):
            source = self.api._browser_sources.get_browser_source(name)
            for repo, base in (('Qwen/Qwen-Image-2.1', 'Qwen 2.1'),
                               ('MiniMaxAI/MiniMax-H3', 'MiniMax H3')):
                with self.subTest(source=name, repo=repo):
                    targets = source._resolve_base_model_filter([base])
                    self.assertEqual(targets, [base])
                    if name == 'huggingface':
                        detected = source._detect_base_model(['base_model:' + repo], 'owner/model', '')
                        self.assertEqual(source._detect_base_model([], repo, repo), base)
                    else:
                        detected = source._detect_base_model([], 'owner/model', '', repo, None)
                        muse = {'model': {'stableDiffusionVersion': base}}
                        self.assertEqual(source._detect_base_model([], 'owner/model', '', None, muse), base)
                    self.assertEqual(detected, base)
                    self.assertTrue(source._matches_base_model_filter({'baseModel': detected}, targets))
                    self.assertFalse(source._matches_base_model_filter({'baseModel': 'Qwen'}, targets))

    def test_h3_huggingface_search_includes_its_video_pipeline(self):
        source = self.api._browser_sources.get_browser_source('huggingface')
        filters = source._resolve_hf_filters(['Checkpoint'], ['MiniMax H3'])
        self.assertIn('image-text-to-video', filters)
        self.assertNotIn('text-to-image', filters)
        self.assertEqual(source._detect_content_type([], 'MiniMaxAI/MiniMax-H3',
                                                   'image-text-to-video'), 'Checkpoint')
        self.assertEqual(source._resolve_hf_filters(['LORA'], ['MiniMax H3']), ['lora'])

    def test_loradex_does_not_mix_original_qwen_with_qwen_21(self):
        rows = [{'name': base, 'base_model': base} for base in ('Qwen', 'Qwen 2.1', 'MiniMax H3')]
        for base in ('Qwen 2.1', 'MiniMax H3'):
            with self.subTest(base=base):
                selected = self.fm._filter_lora_dex_data(rows, [base], 'All', False, '')
                self.assertEqual([row['base_model'] for row in selected], [base])
