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


class TestResolveLocalModelMeta(unittest.TestCase):
    """Unit tests for _resolve_local_model_meta()"""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _make_model_file(self, name):
        path = os.path.join(self.tmp_dir.name, name)
        with open(path, 'wb') as f:
            f.write(b'dummy')
        return path

    def _write_json(self, model_path, data):
        json_path = os.path.splitext(model_path)[0] + '.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f)

    def _write_api_info(self, model_path, data):
        api_path = os.path.splitext(model_path)[0] + '.api_info.json'
        with open(api_path, 'w', encoding='utf-8') as f:
            json.dump(data, f)

    # ------------------------------------------------------------------
    # 0. Validation
    # ------------------------------------------------------------------
    def test_none_path_raises_valueerror(self):
        with self.assertRaises(ValueError) as ctx:
            lrv._resolve_local_model_meta(None)
        self.assertIn('file_path is required', str(ctx.exception))

    def test_empty_path_raises_valueerror(self):
        with self.assertRaises(ValueError) as ctx:
            lrv._resolve_local_model_meta('')
        self.assertIn('file_path is required', str(ctx.exception))

    def test_whitespace_path_raises_valueerror(self):
        with self.assertRaises(ValueError) as ctx:
            lrv._resolve_local_model_meta('   ')
        self.assertIn('file_path is required', str(ctx.exception))

    # ------------------------------------------------------------------
    # 1. File without sidecars returns basic fields
    # ------------------------------------------------------------------
    def test_no_sidecars_returns_basic_fields(self):
        path = self._make_model_file('model.safetensors')
        result = lrv._resolve_local_model_meta(path)
        self.assertEqual(result['fileName'], 'model.safetensors')
        self.assertEqual(result['filePath'], path)
        # contentType may or may not be present depending on Forge availability

    # ------------------------------------------------------------------
    # 2. .json sidecar populates sha256, modelId, modelVersionId and
    #    provides fallback baseModel via "sd version"
    # ------------------------------------------------------------------
    def test_json_sidecar_populates_fields(self):
        path = self._make_model_file('lora.safetensors')
        self._write_json(path, {
            'sha256': 'aabbccdd',
            'modelId': 123,
            'modelVersionId': 456,
            'sd version': 'Pony',
        })
        result = lrv._resolve_local_model_meta(path)
        self.assertEqual(result['sha256'], 'AABBCCDD')
        self.assertEqual(result['modelId'], 123)
        self.assertEqual(result['modelVersionId'], 456)
        self.assertEqual(result['baseModel'], 'Pony')

    # ------------------------------------------------------------------
    # 3. .api_info.json populates baseModel, modelName and versionName
    # ------------------------------------------------------------------
    def test_api_info_populates_fields(self):
        path = self._make_model_file('checkpoint.safetensors')
        self._write_api_info(path, {
            'baseModel': 'SDXL',
            'name': 'v2.0',
            'model': {'name': 'MyCheckpoint'},
        })
        result = lrv._resolve_local_model_meta(path)
        self.assertEqual(result['baseModel'], 'SDXL')
        self.assertEqual(result['versionName'], 'v2.0')
        self.assertEqual(result['modelName'], 'MyCheckpoint')

    # ------------------------------------------------------------------
    # 4. .json has priority for modelId / modelVersionId over .api_info.json
    # ------------------------------------------------------------------
    def test_json_priority_for_ids(self):
        path = self._make_model_file('model.safetensors')
        self._write_json(path, {
            'modelId': 100,
            'modelVersionId': 200,
        })
        self._write_api_info(path, {
            'modelId': 999,
            'id': 888,
        })
        result = lrv._resolve_local_model_meta(path)
        self.assertEqual(result['modelId'], 100)
        self.assertEqual(result['modelVersionId'], 200)

    # ------------------------------------------------------------------
    # 5. .api_info.json has priority for baseModel over "sd version"
    # ------------------------------------------------------------------
    def test_api_info_priority_for_basemodel(self):
        path = self._make_model_file('model.safetensors')
        self._write_json(path, {
            'sd version': 'Other',
        })
        self._write_api_info(path, {
            'baseModel': 'Illustrious',
        })
        result = lrv._resolve_local_model_meta(path)
        self.assertEqual(result['baseModel'], 'Illustrious')

    def test_api_info_overrides_sd_version(self):
        path = self._make_model_file('model.safetensors')
        self._write_json(path, {
            'sd version': 'Pony',
        })
        self._write_api_info(path, {
            'baseModel': 'SDXL',
        })
        result = lrv._resolve_local_model_meta(path)
        self.assertEqual(result['baseModel'], 'SDXL')

    # ------------------------------------------------------------------
    # 6. Invalid sidecar does not crash the function
    # ------------------------------------------------------------------
    def test_invalid_json_sidecar_does_not_crash(self):
        path = self._make_model_file('model.safetensors')
        json_path = os.path.splitext(path)[0] + '.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            f.write('not valid json {{{')
        result = lrv._resolve_local_model_meta(path)
        self.assertEqual(result['fileName'], 'model.safetensors')
        self.assertNotIn('sha256', result)

    def test_invalid_api_info_does_not_crash(self):
        path = self._make_model_file('model.safetensors')
        api_path = os.path.splitext(path)[0] + '.api_info.json'
        with open(api_path, 'w', encoding='utf-8') as f:
            f.write('not valid json {{{')
        result = lrv._resolve_local_model_meta(path)
        self.assertEqual(result['fileName'], 'model.safetensors')
        self.assertNotIn('baseModel', result)

    # ------------------------------------------------------------------
    # 7. Function does not call API or generate SHA256 from binary
    # ------------------------------------------------------------------
    def test_no_api_call_or_sha256_generation(self):
        path = self._make_model_file('model.safetensors')
        # No sidecars present; if the function tried to call the API or
        # hash the file it would either fail or be very slow.  The fast
        # return proves it does neither.
        result = lrv._resolve_local_model_meta(path)
        self.assertEqual(result['fileName'], 'model.safetensors')
        self.assertNotIn('sha256', result)
        self.assertNotIn('modelId', result)


class TestMarkFileForReview(unittest.TestCase):
    """Unit tests for mark_file_for_review()"""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.original_file = lrv.REVIEW_FILE
        lrv.REVIEW_FILE = os.path.join(self.tmp_dir.name, 'local_review_status.json')

    def tearDown(self):
        lrv.REVIEW_FILE = self.original_file
        self.tmp_dir.cleanup()

    def _make_model_file(self, name):
        path = os.path.join(self.tmp_dir.name, name)
        with open(path, 'wb') as f:
            f.write(b'dummy')
        return path

    def _write_json(self, model_path, data):
        json_path = os.path.splitext(model_path)[0] + '.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f)

    # ------------------------------------------------------------------
    # 1. Creates entry using metadata resolved from sidecars
    # ------------------------------------------------------------------
    def test_creates_entry_from_sidecars(self):
        path = self._make_model_file('lora.safetensors')
        self._write_json(path, {
            'sha256': 'deadbeef',
            'modelId': 42,
            'modelVersionId': 99,
            'sd version': 'Pony',
        })
        entry = lrv.mark_file_for_review(path)
        # sha256 is the dict key, not stored inside the entry
        self.assertEqual(entry['status'], 'needs_review')
        self.assertEqual(entry['modelId'], 42)
        self.assertEqual(entry['modelVersionId'], 99)
        self.assertEqual(entry['baseModel'], 'Pony')
        self.assertEqual(entry['fileName'], 'lora.safetensors')
        # Verify it was persisted under the correct SHA256 key
        self.assertEqual(lrv.get_review_status('deadbeef')['status'], 'needs_review')

    # ------------------------------------------------------------------
    # 2. Forwards reasons and manual_note correctly
    # ------------------------------------------------------------------
    def test_forwards_reasons_and_manual_note(self):
        path = self._make_model_file('model.safetensors')
        self._write_json(path, {
            'sha256': 'cafebabe',
        })
        entry = lrv.mark_file_for_review(
            path,
            reasons=['blurry preview', 'nsfw'],
            manual_note='Check before using'
        )
        self.assertEqual(entry['reasons'], ['blurry preview', 'nsfw'])
        self.assertEqual(entry['manualNote'], 'Check before using')

    # ------------------------------------------------------------------
    # 3. Normalizes reasons via mark_for_review
    # ------------------------------------------------------------------
    def test_normalizes_reasons(self):
        path = self._make_model_file('model.safetensors')
        self._write_json(path, {
            'sha256': 'aabbccdd',
        })
        entry = lrv.mark_file_for_review(
            path,
            reasons=['  duplicate  ', 'duplicate', '', 'low-quality'],
        )
        self.assertEqual(entry['reasons'], ['duplicate', 'low-quality'])

    # ------------------------------------------------------------------
    # 4. Raises ValueError for invalid file_path
    # ------------------------------------------------------------------
    def test_invalid_path_raises_valueerror(self):
        with self.assertRaises(ValueError) as ctx:
            lrv.mark_file_for_review(None)
        self.assertIn('file_path is required', str(ctx.exception))

    def test_empty_path_raises_valueerror(self):
        with self.assertRaises(ValueError) as ctx:
            lrv.mark_file_for_review('')
        self.assertIn('file_path is required', str(ctx.exception))

    # ------------------------------------------------------------------
    # 5. Raises ValueError when no sha256 in sidecar
    # ------------------------------------------------------------------
    def test_missing_sha256_raises_valueerror(self):
        path = self._make_model_file('model.safetensors')
        self._write_json(path, {
            'modelId': 1,
            # sha256 intentionally omitted
        })
        with self.assertRaises(ValueError) as ctx:
            lrv.mark_file_for_review(path)
        self.assertIn('no sha256 found', str(ctx.exception))

    # ------------------------------------------------------------------
    # 6. Does not call API or generate SHA256
    # ------------------------------------------------------------------
    def test_no_api_call_or_sha256_generation(self):
        path = self._make_model_file('model.safetensors')
        # No sidecars at all; should fail fast on sha256 check,
        # never attempting to hash the file or call the API.
        with self.assertRaises(ValueError) as ctx:
            lrv.mark_file_for_review(path)
        self.assertIn('no sha256 found', str(ctx.exception))


# ------------------------------------------------------------------------------
# Test helpers from scripts/civitai_file_manage.py
# ------------------------------------------------------------------------------

class TestReviewButtonHtml(unittest.TestCase):
    """Unit tests for _build_review_button_html and _inject_review_block_into_model_html."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.original_file = lrv.REVIEW_FILE
        lrv.REVIEW_FILE = os.path.join(self.tmp_dir.name, 'local_review_status.json')

    def tearDown(self):
        lrv.REVIEW_FILE = self.original_file
        self.tmp_dir.cleanup()

    def _make_model_with_sidecar(self, name, sha256):
        path = os.path.join(self.tmp_dir.name, name)
        with open(path, 'w') as f:
            f.write('dummy')
        sidecar = os.path.splitext(path)[0] + '.json'
        with open(sidecar, 'w') as f:
            json.dump({'sha256': sha256}, f)
        return path

    def test_build_review_button_not_marked(self):
        from scripts.civitai_local_review import _build_review_button_html
        path = self._make_model_with_sidecar('model1.safetensors', 'AABBCC')
        html = _build_review_button_html(path)
        self.assertIn('Mark for review', html)
        self.assertIn('markForReviewOverlay', html)
        self.assertNotIn('disabled', html)
        # Revamp markup structure
        self.assertIn('local-review-content', html)
        self.assertIn('local-review-status', html)
        self.assertIn('local-review-btn', html)
        self.assertIn('data-review-state="unmarked"', html)
        self.assertIn('Not marked for review', html)

    def test_build_review_button_already_marked(self):
        from scripts.civitai_local_review import _build_review_button_html
        path = self._make_model_with_sidecar('model2.safetensors', 'DDEEFF')
        lrv.mark_for_review({'sha256': 'DDEEFF', 'status': 'needs_review'})
        html = _build_review_button_html(path)
        self.assertIn('Marked for review', html)
        self.assertIn('disabled', html)
        self.assertNotIn('markForReviewOverlay', html)
        # Revamp markup structure
        self.assertIn('local-review-content', html)
        self.assertIn('local-review-status', html)
        self.assertIn('local-review-btn', html)
        self.assertIn('data-review-state="marked"', html)

    def test_build_review_button_no_inline_styles(self):
        from scripts.civitai_local_review import _build_review_button_html
        path = self._make_model_with_sidecar('model3.safetensors', 'AABBCC')
        html = _build_review_button_html(path)
        self.assertNotIn('style="', html, 'Review button HTML must not contain inline styles')

    def test_build_review_button_missing_file(self):
        from scripts.civitai_local_review import _build_review_button_html
        html = _build_review_button_html('/nonexistent/file.safetensors')
        self.assertEqual(html, '')

    def test_inject_review_block_inside_description_anchor(self):
        from scripts.civitai_local_review import _inject_review_block_into_model_html
        base = '<div class="main-container"><div class="description-block">Desc<!-- REVIEW_BLOCK_ANCHOR --></div><div class="image-block"><img></div></div>'
        review = '<div class="review-block">Review</div>'
        result = _inject_review_block_into_model_html(base, review)
        self.assertIn(review, result)
        # Review must be INSIDE description-block, before the anchor
        self.assertLess(result.index(review), result.index('<!-- REVIEW_BLOCK_ANCHOR -->'))
        # And still inside description-block (before its closing </div>)
        desc_close = result.index('</div>', result.index('<!-- REVIEW_BLOCK_ANCHOR -->'))
        self.assertLess(result.index(review), desc_close)

    def test_inject_review_block_inside_description_no_anchor(self):
        from scripts.civitai_local_review import _inject_review_block_into_model_html
        # Simulate OLD saved HTML without anchor comment
        base = '<div class="main-container"><div class="description-block"><h2>Model Description</h2><div class="description-wrapper">Text</div></div><div class="image-block"><img></div></div>'
        review = '<div class="review-block">Review</div>'
        result = _inject_review_block_into_model_html(base, review)
        self.assertIn(review, result)
        # Review must be INSIDE description-block: after its start and before image-block
        desc_start = result.index('class="description-block"')
        image_start = result.index('<div class="image-block">')
        review_idx = result.index(review)
        self.assertGreater(review_idx, desc_start)
        self.assertLess(review_idx, image_start)
        # And there must be a closing </div> after the review but before image-block
        # (this proves it's inside the description-block, not after it)
        close_after_review = result.index('</div>', review_idx)
        self.assertLess(close_after_review, image_start)

    def test_inject_review_block_before_image_block(self):
        from scripts.civitai_local_review import _inject_review_block_into_model_html
        base = '<div class="main-container"><h1>Title</h1><p>Desc</p><div class="image-block"><img></div></div>'
        review = '<div class="review-block">Review</div>'
        result = _inject_review_block_into_model_html(base, review)
        self.assertIn(review, result)
        # Review must come BEFORE image-block
        self.assertLess(result.index(review), result.index('<div class="image-block">'))

    def test_inject_review_block_fallback_main_container(self):
        from scripts.civitai_local_review import _inject_review_block_into_model_html
        base = '<div class="main-container"><h1>Title</h1><p>Content</p></div>'
        review = '<div class="review-block">Review</div>'
        result = _inject_review_block_into_model_html(base, review)
        self.assertIn(review, result)
        # Review before final closing </div>
        self.assertLess(result.index(review), result.rindex('</div>'))

    def test_inject_review_block_fallback_append(self):
        from scripts.civitai_local_review import _inject_review_block_into_model_html
        base = '<h1>No container here</h1>'
        review = '<div class="review-block">Review</div>'
        result = _inject_review_block_into_model_html(base, review)
        # No anchor, no image-block, no main-container -> append at end
        self.assertTrue(result.endswith(review))

    def test_inject_review_block_empty_review(self):
        from scripts.civitai_local_review import _inject_review_block_into_model_html
        base = '<div class="main-container"><h1>Title</h1></div>'
        result = _inject_review_block_into_model_html(base, '')
        self.assertEqual(result, base)

    def test_inject_review_block_empty_html(self):
        from scripts.civitai_local_review import _inject_review_block_into_model_html
        review = '<div class="review-block">Review</div>'
        result = _inject_review_block_into_model_html('', review)
        self.assertEqual(result, '')


if __name__ == '__main__':
    unittest.main(verbosity=2)
