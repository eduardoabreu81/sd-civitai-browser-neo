"""Lightweight unit tests for civitai_html_builder.py

These tests verify HTML string output without requiring Forge Neo.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.civitai_html_builder import (
    build_tags_html,
    build_permissions_html,
    build_model_page_html,
    build_uploader_html,
    build_version_info_html,
    build_version_permissions_html,
    build_description_html,
    build_trigger_words_html,
    assemble_model_info_html,
    # Revamp builders
    build_model_badges_html,
    build_download_info_card,
    build_local_model_status_card,
    assemble_model_info_html_revamp,
)


class TestBuildTagsHtml(unittest.TestCase):
    def test_empty_tags_returns_empty_string(self):
        result = build_tags_html([])
        self.assertEqual(result, '')

    def test_tags_are_escaped(self):
        result = build_tags_html(['<script>alert(1)</script>'])
        self.assertIn('&lt;script&gt;', result)
        self.assertNotIn('<script>', result)

    def test_multiple_tags(self):
        result = build_tags_html(['anime', 'portrait', 'sfw'])
        self.assertEqual(result.count('<span class="civitai-tag">'), 3)


class TestBuildPermissionsHtml(unittest.TestCase):
    def test_all_allowed(self):
        item = {
            'allowNoCredit': True,
            'allowCommercialUse': ['Image', 'Rent', 'RentCivit', 'Sell'],
            'allowDerivatives': True,
            'allowDifferentLicense': True,
        }
        result = build_permissions_html(item)
        self.assertIn('Use the model without crediting the creator', result)
        self.assertEqual(result.count('stroke="lime"'), 7)

    def test_all_denied(self):
        item = {
            'allowNoCredit': False,
            'allowCommercialUse': [],
            'allowDerivatives': False,
            'allowDifferentLicense': False,
        }
        result = build_permissions_html(item)
        self.assertEqual(result.count('stroke="red"'), 7)

    def test_mixed_permissions(self):
        item = {
            'allowNoCredit': True,
            'allowCommercialUse': ['Image'],
            'allowDerivatives': False,
            'allowDifferentLicense': False,
        }
        result = build_permissions_html(item)
        self.assertEqual(result.count('stroke="lime"'), 2)
        self.assertEqual(result.count('stroke="red"'), 5)


class TestBuildModelPageHtml(unittest.TestCase):
    def test_local_only_shows_plain_text(self):
        result = build_model_page_html('MyModel', '', 123, True)
        self.assertIn('Model Source:', result)
        self.assertIn('(Local file only)', result)
        self.assertNotIn('<a ', result)

    def test_online_shows_link_with_version_id(self):
        result = build_model_page_html('MyModel', 'https://civitai.com/models/456', 789, False)
        self.assertIn('Model Page:', result)
        self.assertIn('<a ', result)
        self.assertIn('modelVersionId=789', result)
        self.assertIn('MyModel', result)


class TestBuildUploaderHtml(unittest.TestCase):
    def test_known_creator_with_link(self):
        avatar = '<div class="avatar"><img src="http://example.com/avatar.png"></div>'
        result = build_uploader_html('JohnDoe', avatar, {'username': 'JohnDoe'})
        self.assertIn('Uploaded by:', result)
        self.assertIn('<a ', result)
        self.assertIn('/user/JohnDoe', result)
        self.assertIn(avatar, result)

    def test_unknown_creator_without_link(self):
        avatar = '<div class="avatar"></div>'
        result = build_uploader_html('User not found', avatar, None)
        self.assertIn('Uploaded Unknown:', result)
        self.assertNotIn('<a ', result)


class TestBuildVersionInfoHtml(unittest.TestCase):
    def test_all_fields_present(self):
        result = build_version_info_html(
            display_type='Checkpoint',
            model_version='v1.0',
            output_basemodel='SDXL',
            model_availability='EarlyAccess',
            model_date_published='2024-01-01',
            tags_html='<span class="civitai-tag">tag</span>',
            sha256_value='ABC123',
            model_url='https://civitai.com/download/123',
        )
        self.assertIn('Version Information', result)
        self.assertIn('Checkpoint', result)
        self.assertIn('v1.0', result)
        self.assertIn('SDXL', result)
        self.assertIn('EarlyAccess', result)
        self.assertIn('2024-01-01', result)
        self.assertIn('ABC123', result)
        self.assertIn('https://civitai.com/download/123', result)

    def test_missing_sha256_omits_row(self):
        result = build_version_info_html(
            display_type='Checkpoint',
            model_version='v1.0',
            output_basemodel='SDXL',
            model_availability='Public',
            model_date_published='2024-01-01',
            tags_html='',
            sha256_value='Unknown',
            model_url='',
        )
        self.assertNotIn('SHA256', result)

    def test_missing_model_url_omits_row(self):
        result = build_version_info_html(
            display_type='Checkpoint',
            model_version='v1.0',
            output_basemodel='SDXL',
            model_availability='Public',
            model_date_published='2024-01-01',
            tags_html='',
            sha256_value='',
            model_url='',
        )
        self.assertNotIn('Download link', result)


class TestBuildDescriptionHtml(unittest.TestCase):
    def test_contains_review_block_anchor(self):
        result = build_description_html('<p>Hello</p>', False)
        self.assertIn('<!-- REVIEW_BLOCK_ANCHOR -->', result)

    def test_prefix_from_preview(self):
        result = build_description_html('<p>Hello</p>', True)
        self.assertIn('id="preview-description-content"', result)
        self.assertIn("toggleDescription('preview-')", result)

    def test_no_prefix_when_not_preview(self):
        result = build_description_html('<p>Hello</p>', False)
        self.assertIn('id="description-content"', result)
        self.assertIn("toggleDescription('')", result)


class TestBuildTriggerWordsHtml(unittest.TestCase):
    def test_empty_returns_empty_string(self):
        result = build_trigger_words_html([], False, None)
        self.assertEqual(result, '')

    def test_lora_adds_synthetic_row(self):
        result = build_trigger_words_html([], True, 'my_lora.safetensors')
        self.assertIn('lora-tag-row', result)
        self.assertIn('&lt;lora:my_lora:1&gt;', result)
        self.assertIn('Trigger Words', result)

    def test_multiple_groups(self):
        result = build_trigger_words_html(['word1, word2', 'word3'], False, None)
        self.assertEqual(result.count('trigger-word-row'), 2)
        self.assertIn('word1, word2', result)
        self.assertIn('word3', result)
        self.assertIn('Add all to prompt', result)

    def test_single_group_shows_add_to_prompt(self):
        result = build_trigger_words_html(['word1'], False, None)
        self.assertIn('Add to prompt', result)
        self.assertNotIn('Add all to prompt', result)


class TestAssembleModelInfoHtml(unittest.TestCase):
    def test_contains_all_sections(self):
        result = assemble_model_info_html(
            model_page='<div>model</div>',
            uploader_page='<div>uploader</div>',
            version_info='<div>version</div>',
            version_permissions='<div>perms</div>',
            companion_banner='<div>banner</div>',
            trained_words_section='<div>words</div>',
            description_section='<div>desc</div>',
            img_html='<div>images</div>',
        )
        self.assertIn('main-container', result)
        self.assertIn('info-section', result)
        self.assertIn('images-section', result)
        self.assertIn('<div>model</div>', result)
        self.assertIn('<div>uploader</div>', result)
        self.assertIn('<div>version</div>', result)
        self.assertIn('<div>perms</div>', result)
        self.assertIn('<div>banner</div>', result)
        self.assertIn('<div>words</div>', result)
        self.assertIn('<div>desc</div>', result)
        self.assertIn('<div>images</div>', result)


# ═══════════════════════════════════════════════════════════════
# Revamp Layout Tests
# ═══════════════════════════════════════════════════════════════

class TestBuildModelBadgesHtml(unittest.TestCase):
    def test_all_badges_present(self):
        result = build_model_badges_html('Checkpoint', 'SDXL', nsfw_level=7, download_count=106940, thumbs_up_count=9237)
        self.assertIn('Checkpoint', result)
        self.assertIn('SDXL', result)
        self.assertIn('NSFW', result)
        self.assertIn('★ 9237', result)
        self.assertIn('↓ 106940', result)

    def test_nsfw_omitted_when_zero(self):
        result = build_model_badges_html('Checkpoint', 'SDXL', nsfw_level=0, download_count=100, thumbs_up_count=10)
        self.assertNotIn('NSFW', result)

    def test_empty_when_no_data(self):
        result = build_model_badges_html(None, None)
        self.assertEqual(result, '')


class TestBuildDownloadInfoCard(unittest.TestCase):
    def test_with_filename_and_meta(self):
        result = build_download_info_card('model.safetensors', 'SafeTensor · fp16 · 6.46 GB')
        self.assertIn('model.safetensors', result)
        self.assertIn('SafeTensor', result)
        self.assertIn('card-download', result)

    def test_with_filename_only(self):
        result = build_download_info_card('model.safetensors', None)
        self.assertIn('model.safetensors', result)
        self.assertNotIn('file-meta', result)

    def test_empty_when_no_filename(self):
        result = build_download_info_card(None, None)
        self.assertEqual(result, '')


class TestBuildLocalModelStatusCard(unittest.TestCase):
    def test_contains_review_anchor(self):
        result = build_local_model_status_card()
        self.assertIn('<!-- REVIEW_BLOCK_ANCHOR -->', result)
        self.assertIn('Local Model Status', result)
        self.assertIn('card-local-status', result)


class TestAssembleModelInfoHtmlRevamp(unittest.TestCase):
    def _build_sidebar(self, **overrides):
        """Helper to build revamp HTML with default blocks."""
        defaults = {
            'model_page': '<div class="model-page">Model</div>',
            'uploader_page': '<div class="uploader-page">Creator</div>',
            'model_badges_html': '<div class="badges">Type · Base</div>',
            'description_section': '<div class="description">Desc</div>',
            'img_html': '<div class="gallery">Images</div>',
            'download_info_card': '<div class="card-download">Download</div>',
            'trained_words_section': '',
            'local_status_card': build_local_model_status_card(),
            'metadata_card': '<div class="card-meta">Meta</div>',
            'permissions_card': '<div class="card-perms">Perms</div>',
            'companion_banner': '',
        }
        defaults.update(overrides)
        return assemble_model_info_html_revamp(**defaults)

    def test_two_column_structure(self):
        result = self._build_sidebar()
        self.assertIn('revamp-layout', result)
        self.assertIn('primary-column', result)
        self.assertIn('sidebar-column', result)
        self.assertIn('revamp-body', result)

    def test_header_contains_badges_and_source(self):
        result = self._build_sidebar()
        self.assertIn('revamp-header', result)
        self.assertIn('Model', result)
        self.assertIn('Type · Base', result)
        self.assertIn('Creator', result)

    def test_primary_has_description_then_gallery(self):
        result = self._build_sidebar()
        desc_pos = result.find('Desc')
        gallery_pos = result.find('Images')
        self.assertGreater(gallery_pos, desc_pos, 'Gallery must come after Description in primary column')

    def test_sidebar_order_download_first(self):
        result = self._build_sidebar()
        download_pos = result.find('card-download')
        local_pos = result.find('card-local')
        meta_pos = result.find('card-meta')
        perms_pos = result.find('card-perms')

        self.assertGreater(local_pos, download_pos, 'Local Model Status must come after Download')
        self.assertGreater(meta_pos, local_pos, 'Metadata must come after Local Model Status')
        self.assertGreater(perms_pos, meta_pos, 'Permissions must come after Metadata')

    def test_checkpoint_omits_empty_trigger_words(self):
        """Trigger Words must not render an empty card for Checkpoint."""
        result = self._build_sidebar(trained_words_section='')
        self.assertNotIn('trained-words-block', result)
        # Sidebar should still have Download, Local, Meta, Perms in order
        self.assertIn('card-download', result)
        self.assertIn('card-local', result)
        self.assertIn('card-meta', result)

    def test_lora_includes_trigger_words_after_download(self):
        """Trigger Words must appear for LoRA and be positioned after Download."""
        tw = '<div class="trained-words-block">Triggers</div>'
        result = self._build_sidebar(trained_words_section=tw)
        self.assertIn('trained-words-block', result)

        download_pos = result.find('card-download')
        tw_pos = result.find('trained-words-block')
        local_pos = result.find('card-local')

        self.assertGreater(tw_pos, download_pos, 'Trigger Words must come after Download')
        self.assertGreater(local_pos, tw_pos, 'Local Model Status must come after Trigger Words')

    def test_companion_banner_omitted_when_empty(self):
        result = self._build_sidebar(companion_banner='')
        self.assertNotIn('companion', result)

    def test_companion_banner_included_when_present(self):
        result = self._build_sidebar(companion_banner='<div class="companion">Alert</div>')
        self.assertIn('companion', result)
        perms_pos = result.find('card-perms')
        companion_pos = result.find('companion')
        self.assertGreater(companion_pos, perms_pos, 'Companion Banner must come after Permissions')

    def test_review_anchor_in_sidebar_not_description(self):
        """REVIEW_BLOCK_ANCHOR must be inside the Local Model Status card (sidebar),
        not inside the description block."""
        result = self._build_sidebar()
        anchor_pos = result.find('<!-- REVIEW_BLOCK_ANCHOR -->')
        sidebar_pos = result.find('sidebar-column')
        primary_pos = result.find('primary-column')

        self.assertGreater(anchor_pos, sidebar_pos, 'Review anchor must be inside sidebar')
        self.assertGreater(anchor_pos, primary_pos, 'Review anchor must be after primary column start')

    def test_local_status_before_metadata(self):
        """Explicit validation: Local Model Status card precedes Metadata card."""
        result = self._build_sidebar()
        local_pos = result.find('card-local')
        meta_pos = result.find('card-meta')
        self.assertGreater(meta_pos, local_pos, 'Metadata must come after Local Model Status')


if __name__ == '__main__':
    unittest.main()
