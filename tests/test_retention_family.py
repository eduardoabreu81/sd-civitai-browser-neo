"""Regression tests: retention must never delete another baseModel's file.

One CivitAI model page can hold versions for several families. A creator who
publishes an Anima LoRA and a MOSS Image LoRA on the same page gives both files
the same modelId. Downloading the MOSS version used to pick the installed Anima
file as the "old version" (find_installed_file_by_model_id matched by modelId
only) and the 'replace' retention policy deleted it.

These exercise the real civitai_file_manage helpers against a temp model tree,
with the same stubs as test_official_tags_integration.
"""

import io
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from test_official_tags_integration import _install_stubs  # noqa: E402

MODEL_ID = 2649530
ANIMA_V1 = {'id': 111, 'baseModel': 'Anima', 'files': [{'hashes': {'SHA256': 'AAA111'}}]}
ANIMA_V2 = {'id': 222, 'baseModel': 'Anima', 'files': [{'hashes': {'SHA256': 'AAA222'}}]}
MOSS_V1 = {'id': 3427803, 'baseModel': 'MOSS Image', 'files': [{'hashes': {'SHA256': 'D7F7'}}]}
VERSIONS = [MOSS_V1, ANIMA_V2, ANIMA_V1]


class TestRetentionFamily(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._saved_modules = dict(sys.modules)
        for name in [n for n in sys.modules if n == 'scripts' or n.startswith('scripts.')]:
            del sys.modules[name]
        _install_stubs()
        import scripts.civitai_file_manage as fm
        cls.fm = fm

    @classmethod
    def tearDownClass(cls):
        sys.modules.clear()
        sys.modules.update(cls._saved_modules)

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._orig_folders = self.fm._get_all_model_folders
        self.fm._get_all_model_folders = lambda: [self.tmp]

    def tearDown(self):
        self.fm._get_all_model_folders = self._orig_folders
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _install(self, folder, name, sidecar):
        target = os.path.join(self.tmp, folder)
        os.makedirs(target, exist_ok=True)
        path = os.path.join(target, name + '.safetensors')
        with io.open(path, 'w', encoding='utf-8') as handle:
            handle.write('')
        with io.open(os.path.join(target, name + '.json'), 'w', encoding='utf-8') as handle:
            json.dump(sidecar, handle)
        return path

    def _install_anima_v1(self, **overrides):
        sidecar = {'modelId': MODEL_ID, 'modelVersionId': 111, 'sha256': 'AAA111',
                   'sd version': 'Anima'}
        sidecar.update(overrides)
        return self._install('Anima', 'male_bottom_pov_Anima', sidecar)

    def _find(self, new_version, filename, use_index=True):
        index = self.fm.build_installed_index() if use_index else None
        return self.fm.find_installed_file_by_model_id(
            MODEL_ID, filename, index=index,
            base_model=new_version['baseModel'], versions_list=VERSIONS)

    # --- the reported bug ----------------------------------------------

    def test_other_family_is_not_the_old_version(self):
        self._install_anima_v1()
        for use_index in (True, False):
            with self.subTest(use_index=use_index):
                self.assertEqual(
                    self._find(MOSS_V1, 'male_bottom_pov_moss.safetensors', use_index), '')

    # --- same-family updates still replace -----------------------------

    def test_same_family_older_version_is_found(self):
        anima = self._install_anima_v1()
        for use_index in (True, False):
            with self.subTest(use_index=use_index):
                self.assertEqual(
                    self._find(ANIMA_V2, 'male_bottom_pov_Anima_v2.safetensors', use_index), anima)

    def test_picks_same_family_when_both_are_installed(self):
        self._install('MOSS Image', 'male_bottom_pov_moss_old',
                      {'modelId': MODEL_ID, 'modelVersionId': 999, 'sha256': 'OLD',
                       'sd version': 'MOSS Image'})
        anima = self._install_anima_v1()
        self.assertEqual(self._find(ANIMA_V2, 'male_bottom_pov_Anima_v2.safetensors'), anima)

    # --- classification -------------------------------------------------

    def test_api_version_wins_over_stale_sidecar_base(self):
        # Sidecar says Anima, but its modelVersionId is the MOSS version.
        path = self._install_anima_v1(modelVersionId=3427803)
        self.assertEqual(self.fm.installed_base_model(path, VERSIONS), 'MOSS Image')

    def test_hash_identifies_version_without_version_id(self):
        path = self._install_anima_v1(modelVersionId=None, **{'sd version': ''})
        self.assertEqual(self.fm.installed_base_model(path, VERSIONS), 'Anima')

    def test_unknown_family_is_kept(self):
        self._install_anima_v1(modelVersionId=None, sha256='', **{'sd version': ''})
        self.assertEqual(self._find(ANIMA_V2, 'male_bottom_pov_Anima_v2.safetensors'), '')

    def test_same_base_model_requires_both_known(self):
        self.assertTrue(self.fm.same_base_model('MOSS Image', 'moss image '))
        self.assertFalse(self.fm.same_base_model('Anima', 'MOSS Image'))
        self.assertFalse(self.fm.same_base_model('', ''))
        self.assertFalse(self.fm.same_base_model(None, 'Anima'))

    # --- unfiltered lookup (delete flow) keeps its behavior ---------------

    def test_no_base_model_means_no_family_filter(self):
        anima = self._install_anima_v1()
        self.assertEqual(self.fm.find_installed_file_by_model_id(MODEL_ID), anima)

    # --- the download queue must use the filter ---------------------------

    def test_selected_to_queue_filters_by_base_model(self):
        src_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'civitai_download.py')
        with open(src_path, encoding='utf-8') as f:
            src = f.read()
        self.assertIn('base_model=output_basemodel, versions_list=versions_list', src,
                      'retention fallback lookup no longer filters by baseModel')
        self.assertIn('_file.same_base_model(', src,
                      'gl.update_items candidates are no longer checked against the new baseModel')


if __name__ == '__main__':
    unittest.main()
