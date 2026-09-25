"""Local Models base-model filter must follow the INSTALLED version.

One CivitAI listing can span many base models: "Smug Face [ANIMA & IL & ZIT]"
publishes Anima, Illustrious and ZImageTurbo versions. With only the Anima file
installed, the card must show under Anima — not under ZImageTurbo too, which is
what matching any version of the listing did.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from test_civarchive_recovered_html import _RecoveredTestCase  # noqa: E402

ANIMA_SHA = 'A' * 64
KREA_SHA = 'B' * 64


def _listing():
    return {
        'id': 2197913,
        'name': 'Smug Face [ANIMA & IL & ZIT]',
        'modelVersions': [
            {'id': 2493973, 'baseModel': 'Illustrious', 'files': [{'hashes': {'SHA256': 'C' * 64}}]},
            {'id': 2713194, 'baseModel': 'Anima', 'files': [{'hashes': {'SHA256': ANIMA_SHA}}]},
            {'id': 2474733, 'baseModel': 'ZImageTurbo', 'files': [{'hashes': {'SHA256': 'D' * 64}}]},
            {'id': 3309368, 'baseModel': 'Krea 2', 'files': [{'hashes': {'SHA256': KREA_SHA}}]},
        ],
    }


class TestInstalledBaseModels(_RecoveredTestCase):
    def _file(self, name, sidecar):
        path = os.path.join(self.tmp, name + '.safetensors')
        open(path, 'w').close()
        self._write(name + '.json', sidecar)
        return path

    def test_matched_by_cached_version_id(self):
        path = self._file('smug', {'modelId': 2197913, 'modelVersionId': 2713194})
        self.assertEqual(self.fm._installed_base_models(_listing(), [path]), {'anima'})

    def test_version_id_stored_as_string_still_matches(self):
        path = self._file('smug', {'modelId': '2197913', 'modelVersionId': '2713194'})
        self.assertEqual(self.fm._installed_base_models(_listing(), [path]), {'anima'})

    def test_matched_by_hash_when_no_version_id(self):
        path = self._file('smug', {'modelId': 2197913, 'sha256': ANIMA_SHA.lower()})
        self.assertEqual(self.fm._installed_base_models(_listing(), [path]), {'anima'})

    def test_every_installed_version_counts(self):
        # Real Dream: an Anima file and a Krea 2 file from the same listing.
        anima = self._file('rd_anima', {'modelVersionId': 2713194})
        krea = self._file('rd_krea', {'modelVersionId': 3309368})
        self.assertEqual(self.fm._installed_base_models(_listing(), [anima, krea]), {'anima', 'krea 2'})

    def test_unmatched_install_falls_back_to_every_version(self):
        path = self._file('odd', {'modelId': 2197913})
        self.assertEqual(self.fm._installed_base_models(_listing(), [path]),
                         {'illustrious', 'anima', 'zimageturbo', 'krea 2'})

    def test_local_only_card_uses_its_own_file(self):
        path = self._file('local', {'sha256': ANIMA_SHA})
        item = self.fm._build_local_fallback_browser_item(path)
        item['modelVersions'][0]['baseModel'] = 'Anima'
        paths = self.fm._item_local_paths(item, {})
        self.assertEqual(paths, [path])
        self.assertEqual(self.fm._installed_base_models(item, paths), {'anima'})


if __name__ == '__main__':
    unittest.main()
