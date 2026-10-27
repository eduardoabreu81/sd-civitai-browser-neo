"""Regression tests: versions that share a filename are told apart by their sidecar.

Model 2006914 publishes ABG.safetensors for MOSS Image, Krea 2 and SDXL. With the
MOSS file installed, the Browser panel matched the Krea version by filename,
showed it as installed and hid its Download button.
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

MOSS = {'id': 3431825, 'sha256': '2E93EA20E2'}
KREA = {'id': 3146316, 'sha256': '593D8E1390'}


class TestSameFilenameVersions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._saved_modules = dict(sys.modules)
        for name in [n for n in sys.modules if n == 'scripts' or n.startswith('scripts.')]:
            del sys.modules[name]
        _install_stubs()
        import scripts.civitai_api as api
        cls.api = api

    @classmethod
    def tearDownClass(cls):
        sys.modules.clear()
        sys.modules.update(cls._saved_modules)

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        with io.open(os.path.join(self.tmp, 'ABG.safetensors'), 'w', encoding='utf-8') as handle:
            handle.write('x')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _sidecar(self, data):
        with io.open(os.path.join(self.tmp, 'ABG.json'), 'w', encoding='utf-8') as handle:
            json.dump(data, handle)

    def _other(self, version):
        return self.api._same_name_is_other_version(self.tmp, 'ABG.safetensors', version['id'], version['sha256'])

    def test_sibling_version_is_not_installed(self):
        self._sidecar({'modelVersionId': MOSS['id'], 'sha256': MOSS['sha256']})
        self.assertTrue(self._other(KREA))
        self.assertFalse(self._other(MOSS))

    def test_hash_only_sidecar(self):
        self._sidecar({'sha256': MOSS['sha256'].lower()})
        self.assertTrue(self._other(KREA))
        self.assertFalse(self._other(MOSS))

    def test_no_sidecar_keeps_filename_match(self):
        self.assertFalse(self._other(KREA))


if __name__ == '__main__':
    unittest.main()
