"""New base models stay distinct through discovery, badges and organization."""

import ast
import json
import sys
import types
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from test_civarchive_recovered_html import _RecoveredTestCase


# Base models Forge Neo runs through its own extensions or natively.
NEW_BASES = ('Qwen 2.1', 'MiniMax H3', 'Flux.3 Klein', 'Flux.3 Klein-base',
             'MOSS Image', 'MOSS Image Base', 'Iris 3B', 'Krea 2 Turbo',
             'LTXV2', 'LTXV 2.3', 'LTXV 2.5')

# Hub repository → canonical base name, shared by Hugging Face and ModelScope.
REPOSITORIES = (
    ('Qwen/Qwen-Image-2.1', 'Qwen 2.1'),
    ('MiniMaxAI/MiniMax-H3', 'MiniMax H3'),
    ('black-forest-labs/FLUX.2-klein-4B', 'Flux.2 Klein 4B'),
    ('black-forest-labs/FLUX.2-klein-base-4B', 'Flux.2 Klein 4B-base'),
    ('black-forest-labs/FLUX.2-klein-9B', 'Flux.2 Klein 9B'),
    ('black-forest-labs/FLUX.2-klein-base-9b-fp8', 'Flux.2 Klein 9B-base'),
    ('black-forest-labs/FLUX.2-dev', 'Flux.2 D'),
    ('black-forest-labs/flux-3-image-klein', 'Flux.3 Klein'),
    ('black-forest-labs/flux-3-image-klein-base', 'Flux.3 Klein-base'),
    ('OpenMOSS-Team/MOSS-Image-SFT', 'MOSS Image'),
    ('OpenMOSS-Team/MOSS-Image-Base', 'MOSS Image Base'),
    ('speridlabs/iris-3b', 'Iris 3B'),
    ('krea/Krea-2-Turbo', 'Krea 2 Turbo'),
    ('Lightricks/LTX-2', 'LTXV2'),
    ('Lightricks/LTX-2.3', 'LTXV 2.3'),
    ('Lightricks/LTX-2.5', 'LTXV 2.5'),
)


class TestNewBaseModels(_RecoveredTestCase):
    def _choices(self):
        # Load the shipped function without registering Forge's Gradio UI.
        path = Path(__file__).resolve().parents[1] / 'scripts' / 'civitai_gui.py'
        tree = ast.parse(path.read_text(encoding='utf-8'))
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                    and n.name == 'get_base_models')
        namespace = {'_api': self.api, 'json': json, 'print': lambda *args: None}
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), namespace)
        with patch.object(self.api, 'request_civit_api') as request:
            choices = namespace['get_base_models']()
        self.assertFalse(request.called)
        return choices

    def test_filters_are_the_curated_forge_neo_list(self):
        choices = self._choices()
        for base in NEW_BASES + ('Qwen', 'Krea 2', 'LTXV'):
            with self.subTest(base=base):
                self.assertIn(base, choices)
        # CivitAI models Forge Neo cannot run stay out of the filters.
        for base in ('Ideogram 4.0', 'Boogu', 'HiDream', 'Flux.3'):
            with self.subTest(base=base):
                self.assertNotIn(base, choices)
        self.assertEqual(len(choices), len(set(choices)))

    def test_badges_keep_versions_apart(self):
        for base, badge in (('Qwen', 'Qwen'), ('Qwen 2.1', 'Q21'),
                            ('Qwen 2.1 variant', 'Q21'),
                            ('MiniMax H3', 'H3'), ('minimax h3 turbo', 'H3'),
                            ('Flux.1 D', 'F1'), ('Flux.1 Krea', 'F1'), ('FLUX.1', 'F1'),
                            ('Flux.2 Klein 4B', 'F2'), ('Flux.2 Future', 'F2'),
                            ('Flux.3 Klein', 'F3'), ('Flux.3 Klein-base', 'F3'),
                            ('Flux.3 Future', 'F3'), ('Flux 3 Video', 'F3'),
                            ('Krea 2', 'Krea'), ('Krea 2 Turbo', 'Krea'),
                            ('MOSS Image', 'MOSS'), ('MOSS Image Base', 'MOSS'),
                            ('Iris 3B', 'Iris'),
                            ('LTXV', 'LTX'), ('LTXV2', 'LTX2'),
                            ('LTXV 2.3', 'LTX2'), ('LTXV 2.5', 'LTX2')):
            with self.subTest(base=base):
                self.assertEqual(self.api.get_base_model_short(base), badge)

    def test_organization_uses_one_folder_per_model(self):
        with patch.object(self.fm.opts, 'civitai_neo_model_categories', None, create=True):
            for base, folder in (('Qwen', 'Qwen'), ('Qwen 2.1', 'Qwen 2.1'),
                                 ('MiniMax H3', 'MiniMax H3'),
                                 ('Flux.1 D', 'Flux.1'), ('Flux.1 Krea', 'Flux.1'),
                                 ('FLUX.1', 'Flux.1'), ('Flux', 'Flux.1'),
                                 ('Flux.2 Klein 9B-base', 'Flux.2'),
                                 ('Flux.3 Klein', 'Flux.3'), ('Flux.3 Klein-base', 'Flux.3'),
                                 ('Krea 2', 'Krea'), ('Krea 2 Turbo', 'Krea'),
                                 ('MOSS Image', 'MOSS Image'), ('MOSS Image Base', 'MOSS Image'),
                                 ('Iris 3B', 'Iris 3B'),
                                 ('LTXV', 'LTX'), ('LTXV2', 'LTX 2'),
                                 ('LTXV 2.3', 'LTX 2'), ('LTXV 2.5', 'LTX 2')):
                with self.subTest(base=base):
                    self.assertEqual(self.fm.normalize_base_model(base), folder)

    def test_sources_send_canonical_base_names_without_renaming(self):
        civitai = self.api._browser_sources.get_browser_source('civitai')
        archive = self.api._browser_sources.get_browser_source('civarchive')
        for base in NEW_BASES:
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
            for repo, base in REPOSITORIES:
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

    def test_ltx2_huggingface_search_uses_video_pipelines(self):
        source = self.api._browser_sources.get_browser_source('huggingface')
        for base in ('LTXV2', 'LTXV 2.3', 'LTXV 2.5'):
            with self.subTest(base=base):
                filters = source._resolve_hf_filters(['Checkpoint'], [base])
                self.assertEqual(filters, ['text-to-video', 'image-to-video'])

    def _companion_banner(self, base, present=()):
        # Point models_path at a temp dir holding only the given files.
        for folder, filename in present:
            target = Path(self.tmp) / folder
            target.mkdir(parents=True, exist_ok=True)
            (target / filename).write_bytes(b'')
        paths = types.ModuleType('modules.paths')
        paths.models_path = self.tmp
        with patch.dict(sys.modules, {'modules.paths': paths}):
            return self.fm.get_companion_banner(base)

    def test_companion_files_follow_the_flux_generation(self):
        for base, expected, absent in (
            ('Flux.1 D', 't5xxl_fp8_e4m3fn_scaled.safetensors', 'flux2-vae.safetensors'),
            ('Flux.2 Klein 4B', 'qwen_3_4b.safetensors', 'clip_l.safetensors'),
            ('Flux.2 Klein 9B-base', 'qwen_3_8b_fp8mixed.safetensors', 'qwen_3_4b.safetensors'),
            ('Flux.3 Klein', 'qwen3vl_4b_int8_convrot.safetensors', 'clip_l.safetensors'),
            ('Flux.3 Klein-base', 'flux2-vae.safetensors', 't5xxl_fp8_e4m3fn_scaled.safetensors'),
        ):
            with self.subTest(base=base):
                banner = self._companion_banner(base)
                self.assertIn(expected, banner)
                self.assertNotIn(absent, banner)
        # Forge Neo cannot run Flux.2 Dev, so no FLUX.1 files are suggested.
        self.assertEqual(self._companion_banner('Flux.2 D'), '')

    def test_companion_alternative_encoder_counts_as_present(self):
        banner = self._companion_banner('Flux.3 Klein', present=(
            ('VAE', 'flux2-vae.safetensors'),
            ('text_encoder', 'qwen3vl_4b_bf16.safetensors'),
        ))
        self.assertEqual(banner, '')

    def test_loradex_does_not_mix_model_versions(self):
        bases = ('Qwen', 'Qwen 2.1', 'MiniMax H3', 'Flux.2 Klein 4B', 'Flux.3 Klein',
                 'Krea 2', 'Krea 2 Turbo', 'LTXV', 'LTXV 2.5', 'MOSS Image', 'Iris 3B')
        rows = [{'name': base, 'base_model': base} for base in bases]
        for base in ('Qwen 2.1', 'MiniMax H3', 'Flux.3 Klein', 'Krea 2 Turbo',
                     'LTXV 2.5', 'MOSS Image', 'Iris 3B'):
            with self.subTest(base=base):
                selected = self.fm._filter_lora_dex_data(rows, [base], 'All', False, '')
                self.assertEqual([row['base_model'] for row in selected], [base])
