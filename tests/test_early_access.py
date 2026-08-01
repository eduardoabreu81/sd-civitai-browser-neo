"""Regression tests for paid/early-access detection.

CivitAI gates paid models three different ways depending on API vintage, and the
current one (``paidAccess``) coexists with ``availability: 'Public'`` — so a paid
version looks completely free to a check that only reads ``availability``.
That gap left paid models untagged in the Browser grid AND let their downloads
run until CivitAI silently redirected Aria2 to the purchase page.
"""

import unittest

from test_civitai_model_ids import _load_civitai_api_with_stubs


def _future(): return "2099-01-01T00:00:00.000Z"
def _past(): return "2020-01-01T00:00:00.000Z"


class TestIsEarlyAccess(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api = _load_civitai_api_with_stubs()

    def test_paid_access_window_still_open(self):
        """Real payload of model-version 3188880 (the reported download failure).

        Note `availability` is 'Public' — the legacy check saw nothing wrong.
        """
        version = {
            "id": 3188880,
            "name": "anima v1",
            "availability": "Public",
            "earlyAccessEndsAt": None,
            "paidAccess": {"permanent": False, "endsAt": _future()},
        }
        self.assertTrue(self.api.is_early_access(version))

    def test_free_sibling_version_of_the_same_model(self):
        """Version 1435042 of that same model is free — must stay untagged."""
        version = {
            "id": 1435042,
            "name": "V1",
            "availability": "Public",
            "earlyAccessEndsAt": None,
            "paidAccess": None,
        }
        self.assertFalse(self.api.is_early_access(version))

    def test_permanently_paid(self):
        self.assertTrue(self.api.is_early_access(
            {"paidAccess": {"permanent": True, "endsAt": None}}
        ))

    def test_expired_paid_window_is_free_again(self):
        self.assertFalse(self.api.is_early_access(
            {"paidAccess": {"permanent": False, "endsAt": _past()}}
        ))

    def test_legacy_availability_flag(self):
        self.assertTrue(self.api.is_early_access({"availability": "EarlyAccess"}))

    def test_legacy_early_access_ends_at(self):
        self.assertTrue(self.api.is_early_access({"earlyAccessEndsAt": _future()}))
        self.assertFalse(self.api.is_early_access({"earlyAccessEndsAt": _past()}))

    def test_plain_free_version(self):
        self.assertFalse(self.api.is_early_access(
            {"id": 1, "name": "v1", "availability": "Public"}
        ))

    def test_malformed_input_never_raises(self):
        for bad in (None, [], "EarlyAccess", {"paidAccess": "yes"},
                    {"paidAccess": {"endsAt": "not-a-date"}},
                    {"earlyAccessEndsAt": 12345}):
            with self.subTest(bad=bad):
                self.assertFalse(self.api.is_early_access(bad))


class TestAvailabilityLabel(unittest.TestCase):
    """The detail panel must not echo 'Public' for a version behind paid access."""

    @classmethod
    def setUpClass(cls):
        cls.api = _load_civitai_api_with_stubs()

    def test_paid_window_reports_the_end_date(self):
        label = self.api.get_availability_label({
            "availability": "Public",
            "paidAccess": {"permanent": False, "endsAt": "2099-01-01T00:00:00.000Z"},
        })
        self.assertEqual(label, "Early Access (paid until 2099-01-01)")

    def test_permanently_paid(self):
        label = self.api.get_availability_label({
            "availability": "Public",
            "paidAccess": {"permanent": True, "endsAt": None},
        })
        self.assertEqual(label, "Early Access (paid)")

    def test_free_version_keeps_raw_availability(self):
        self.assertEqual(
            self.api.get_availability_label({"availability": "Public"}), "Public"
        )

    def test_expired_paid_window_keeps_raw_availability(self):
        self.assertEqual(
            self.api.get_availability_label({
                "availability": "Public",
                "paidAccess": {"permanent": False, "endsAt": _past()},
            }),
            "Public",
        )

    def test_legacy_early_access_ends_at(self):
        self.assertEqual(
            self.api.get_availability_label({"earlyAccessEndsAt": "2099-05-06T10:00:00Z"}),
            "Early Access (until 2099-05-06)",
        )

    def test_legacy_availability_without_dates(self):
        self.assertEqual(
            self.api.get_availability_label({"availability": "EarlyAccess"}), "Early Access"
        )

    def test_missing_and_malformed_input(self):
        self.assertEqual(self.api.get_availability_label({}), "Unknown")
        self.assertEqual(self.api.get_availability_label(None), "Unknown")
        self.assertEqual(
            self.api.get_availability_label(
                {"availability": "Public", "paidAccess": {"permanent": False, "endsAt": "junk"}}
            ),
            "Public",
        )


if __name__ == "__main__":
    unittest.main()
