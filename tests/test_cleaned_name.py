"""cleaned_name() must strip Windows-illegal characters from the whole name.

os.path.splitext() treats everything after the last dot as the extension, so a
version name such as 'v1.5?' used to keep its '?' in the "extension" part.
"""

import unittest
from unittest import mock

from test_civitai_model_ids import _load_civitai_api_with_stubs


class TestCleanedNameWindows(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.api = _load_civitai_api_with_stubs()

    def clean(self, value):
        with mock.patch.object(self.api.platform, 'system', return_value='Windows'):
            return self.api.cleaned_name(value)

    def test_trailing_question_mark_without_dot(self):
        self.assertEqual(self.clean('What?'), 'What')

    def test_trailing_question_mark_after_dotted_version(self):
        self.assertEqual(self.clean('v1.5?'), 'v1.5')
        self.assertEqual(self.clean('Model v2.0 - Why?'), 'Model v2.0 - Why')

    def test_no_trailing_dot_left_behind(self):
        self.assertEqual(self.clean('v1.?'), 'v1')

    def test_real_extension_is_kept(self):
        self.assertEqual(self.clean('a?b.safetensors'), 'ab.safetensors')


if __name__ == '__main__':
    unittest.main()
