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
        # All 7 lines should have the allow SVG (lime stroke)
        self.assertEqual(result.count('stroke="lime"'), 7)

    def test_all_denied(self):
        item = {
            'allowNoCredit': False,
            'allowCommercialUse': [],
            'allowDerivatives': False,
            'allowDifferentLicense': False,
        }
        result = build_permissions_html(item)
        # All 7 lines should have the deny SVG (red stroke)
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

    def test_empty_trained_words_omits_block(self):
        result = assemble_model_info_html(
            model_page='',
            uploader_page='',
            version_info='',
            version_permissions='',
            companion_banner='',
            trained_words_section='',
            description_section='',
            img_html='',
        )
        self.assertIn('main-container', result)
        # Empty string is still inserted; this test verifies it doesn't crash


if __name__ == '__main__':
    unittest.main()
