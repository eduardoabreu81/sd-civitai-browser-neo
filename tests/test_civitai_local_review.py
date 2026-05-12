import unittest
import os
import sys
import tempfile
import json

# Allow importing scripts/ modules from the repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from scripts import civitai_local_review as lrv


class TestLocalReviewStatus(unittest.TestCase):
    """Unit tests for scripts/civitai_local_review.py"""

    def setUp(self):
        """Redirect REVIEW_FILE to a temporary path for every test."""
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.original_file = lrv.REVIEW_FILE
        lrv.REVIEW_FILE = os.path.join(self.tmp_dir.name, 'local_review_status.json')

    def tearDown(self):
        """Restore original REVIEW_FILE and clean up temp directory."""
        lrv.REVIEW_FILE = self.original_file
        self.tmp_dir.cleanup()

    # ------------------------------------------------------------------
    # 1. Missing file returns a valid versioned empty structure
    # ------------------------------------------------------------------
    def test_load_missing_file_returns_versioned_empty_dict(self):
        data = lrv.load_local_review_status()
        self.assertIsInstance(data, dict)
        self.assertEqual(data.get('schemaVersion'), 1)
        self.assertIsInstance(data.get('items'), dict)
        self.assertEqual(data['items'], {})

    def test_get_missing_sha_returns_empty_dict(self):
        result = lrv.get_review_status('DEADBEEF')
        self.assertIsInstance(result, dict)
        self.assertEqual(result, {})

    # ------------------------------------------------------------------
    # 2. mark_for_review creates an item inside data["items"]
    # ------------------------------------------------------------------
    def test_mark_creates_entry_inside_items(self):
        item = {
            'sha256': 'aabbccdd',
            'status': 'needs_review',
            'modelName': 'TestModel',
            'versionName': 'v1',
        }
        entry = lrv.mark_for_review(item)
        self.assertIn('updatedAt', entry)
        self.assertEqual(entry['status'], 'needs_review')
        self.assertEqual(entry['modelName'], 'TestModel')

        # Verify persistence inside the versioned structure
        data = lrv.load_local_review_status()
        self.assertEqual(data.get('schemaVersion'), 1)
        self.assertIn('AABBCCDD', data['items'])
        self.assertEqual(data['items']['AABBCCDD']['status'], 'needs_review')

    # ------------------------------------------------------------------
    # 3. mark_for_review preserves and updates expected fields
    # ------------------------------------------------------------------
    def test_mark_preserves_existing_fields(self):
        first = {
            'sha256': '00112233',
            'status': 'needs_review',
            'reasons': [' blurry preview'],
            'manualNote': 'check later',
            'modelId': 42,
            'modelVersionId': 99,
            'fileName': 'model.safetensors',
            'filePath': '/models/LORA/model.safetensors',
            'contentType': 'LORA',
            'baseModel': 'Pony',
            'modelName': 'OldName',
            'versionName': 'v2',
        }
        lrv.mark_for_review(first)

        second = {
            'sha256': '00112233',
            'status': 'manual_keep',
            'modelName': 'NewName',
            # other fields omitted -> should be preserved
        }
        entry = lrv.mark_for_review(second)

        self.assertEqual(entry['status'], 'manual_keep')        # updated
        self.assertEqual(entry['modelName'], 'NewName')         # updated
        self.assertEqual(entry['reasons'], ['blurry preview'])  # preserved + normalized
        self.assertEqual(entry['manualNote'], 'check later')    # preserved
        self.assertEqual(entry['modelId'], 42)                  # preserved
        self.assertEqual(entry['modelVersionId'], 99)           # preserved
        self.assertEqual(entry['fileName'], 'model.safetensors')
        self.assertEqual(entry['filePath'], '/models/LORA/model.safetensors')
        self.assertEqual(entry['contentType'], 'LORA')
        self.assertEqual(entry['baseModel'], 'Pony')
        self.assertEqual(entry['versionName'], 'v2')

    # ------------------------------------------------------------------
    # 4. get_review_status returns the correct item from items
    # ------------------------------------------------------------------
    def test_get_returns_correct_item(self):
        lrv.mark_for_review({
            'sha256': 'deadbeef',
            'status': 'manual_delete_candidate',
            'modelName': 'FlaggedModel',
        })

        result = lrv.get_review_status('deadbeef')
        self.assertEqual(result['status'], 'manual_delete_candidate')
        self.assertEqual(result['modelName'], 'FlaggedModel')

        # SHA256 normalization (lowercase input -> uppercase key)
        result2 = lrv.get_review_status('DeadBeef')
        self.assertEqual(result2['status'], 'manual_delete_candidate')

    # ------------------------------------------------------------------
    # 5. clear_review_status removes the correct item from items
    # ------------------------------------------------------------------
    def test_clear_removes_item(self):
        lrv.mark_for_review({
            'sha256': 'cafebabe',
            'status': 'needs_review',
        })
        self.assertTrue(lrv.clear_review_status('cafebabe'))
        self.assertEqual(lrv.get_review_status('cafebabe'), {})

    def test_clear_missing_returns_false(self):
        self.assertFalse(lrv.clear_review_status('nonexistent'))

    # ------------------------------------------------------------------
    # 6. save/load round-trip keeps data intact inside versioned structure
    # ------------------------------------------------------------------
    def test_save_load_roundtrip(self):
        payload = {
            'sha256': 'feedface',
            'status': 'manual_delete_candidate',
            'reasons': ['nsfw', 'low-quality'],
            'manualNote': 'Do not use in production.',
            'modelId': 123,
            'modelVersionId': 456,
            'fileName': 'unsafe.safetensors',
            'filePath': '/tmp/unsafe.safetensors',
            'contentType': 'Checkpoint',
            'baseModel': 'SDXL',
            'modelName': 'UnsafeXL',
            'versionName': 'v3-final',
        }
        lrv.mark_for_review(payload)

        # Force reload from disk
        reloaded = lrv.load_local_review_status()
        self.assertEqual(reloaded.get('schemaVersion'), 1)
        key = 'FEEDFACE'
        self.assertIn(key, reloaded['items'])
        self.assertEqual(reloaded['items'][key]['status'], 'manual_delete_candidate')
        self.assertEqual(reloaded['items'][key]['reasons'], ['nsfw', 'low-quality'])
        self.assertEqual(reloaded['items'][key]['manualNote'], 'Do not use in production.')
        self.assertEqual(reloaded['items'][key]['modelId'], 123)
        self.assertEqual(reloaded['items'][key]['modelVersionId'], 456)
        self.assertEqual(reloaded['items'][key]['fileName'], 'unsafe.safetensors')
        self.assertEqual(reloaded['items'][key]['filePath'], '/tmp/unsafe.safetensors')
        self.assertEqual(reloaded['items'][key]['contentType'], 'Checkpoint')
        self.assertEqual(reloaded['items'][key]['baseModel'], 'SDXL')
        self.assertEqual(reloaded['items'][key]['modelName'], 'UnsafeXL')
        self.assertEqual(reloaded['items'][key]['versionName'], 'v3-final')
        self.assertIn('updatedAt', reloaded['items'][key])

    # ------------------------------------------------------------------
    # 7. Legacy flat format is migrated in memory
    # ------------------------------------------------------------------
    def test_legacy_format_migrated_in_memory(self):
        # Write a legacy file (direct SHA256 keys, no schemaVersion / items)
        legacy = {
            'LEGACYSHA1': {
                'status': 'needs_review',
                'modelName': 'LegacyModel',
            },
            'LEGACYSHA2': {
                'status': 'manual_keep',
                'modelName': 'LegacyModel2',
            },
        }
        with open(lrv.REVIEW_FILE, 'w', encoding='utf-8') as f:
            json.dump(legacy, f)

        data = lrv.load_local_review_status()
        self.assertEqual(data.get('schemaVersion'), 1)
        self.assertIn('LEGACYSHA1', data['items'])
        self.assertIn('LEGACYSHA2', data['items'])
        self.assertEqual(data['items']['LEGACYSHA1']['status'], 'needs_review')
        self.assertEqual(data['items']['LEGACYSHA2']['modelName'], 'LegacyModel2')

    # ------------------------------------------------------------------
    # 8. Reasons are normalized (strip, dedupe, remove empties)
    # ------------------------------------------------------------------
    def test_reasons_normalization(self):
        entry = lrv.mark_for_review({
            'sha256': 'badfood',
            'status': 'needs_review',
            'reasons': ['  nsfw  ', '', 'duplicate', 'duplicate', '  ', 'low-quality'],
        })
        self.assertEqual(entry['reasons'], ['nsfw', 'duplicate', 'low-quality'])

    def test_reasons_none_defaults_to_empty(self):
        entry = lrv.mark_for_review({
            'sha256': 'cafefood',
            'status': 'needs_review',
        })
        self.assertEqual(entry['reasons'], [])

    # ------------------------------------------------------------------
    # 9. Validation
    # ------------------------------------------------------------------
    def test_mark_none_raises_valueerror(self):
        with self.assertRaises(ValueError) as ctx:
            lrv.mark_for_review(None)
        self.assertIn('item must be a dict', str(ctx.exception))

    def test_mark_non_dict_raises_valueerror(self):
        with self.assertRaises(ValueError) as ctx:
            lrv.mark_for_review('not a dict')
        self.assertIn('item must be a dict', str(ctx.exception))

    def test_mark_without_sha_raises_valueerror(self):
        with self.assertRaises(ValueError) as ctx:
            lrv.mark_for_review({'modelName': 'NoHash'})
        self.assertIn('sha256 is required', str(ctx.exception))

    def test_mark_empty_sha_raises_valueerror(self):
        with self.assertRaises(ValueError) as ctx:
            lrv.mark_for_review({'sha256': '   '})
        self.assertIn('sha256 is required', str(ctx.exception))


if __name__ == '__main__':
    unittest.main(verbosity=2)
