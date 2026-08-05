"""Regression tests for paid/early-access detection.

CivitAI gates downloads two ways that look identical to a naive check but mean
opposite things to the user:

  * a timed early-access window (``paidAccess.endsAt`` in the future) — costs
    Buzz now, becomes free by itself once the window closes;
  * a permanent purchase (``paidAccess.permanent``) — never becomes free.

Both coexist with ``availability: 'Public'`` (or a missing ``availability``
altogether on ``/api/v1/model-versions``), so a check that only reads
``availability`` sees a completely free version. That gap left gated models
untagged in the Browser grid AND let their downloads run until CivitAI silently
redirected Aria2 to the purchase page.
"""

import unittest

from test_civitai_model_ids import _load_civitai_api_with_stubs


def _future(): return "2099-01-01T00:00:00.000Z"
def _past(): return "2020-01-01T00:00:00.000Z"


class TestGetAccessKind(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api = _load_civitai_api_with_stubs()

    def test_paid_access_window_is_early_access(self):
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
        self.assertEqual(self.api.get_access_kind(version), self.api.ACCESS_EARLY)
        self.assertTrue(self.api.is_access_gated(version))

    def test_free_sibling_version_of_the_same_model(self):
        """Version 1435042 of that same model is free — must stay untagged."""
        version = {
            "id": 1435042,
            "name": "V1",
            "availability": "Public",
            "earlyAccessEndsAt": None,
            "paidAccess": None,
        }
        self.assertEqual(self.api.get_access_kind(version), self.api.ACCESS_FREE)
        self.assertFalse(self.api.is_access_gated(version))

    def test_permanent_purchase_is_paid_not_early_access(self):
        """Real shape of model 2835660 / version 3200276 — the yellow-Buzz kind."""
        version = {
            "id": 3200276,
            "name": "Maria long",
            "availability": "Public",
            "paidAccess": {"permanent": True, "endsAt": None},
        }
        self.assertEqual(self.api.get_access_kind(version), self.api.ACCESS_PAID)
        self.assertTrue(self.api.is_access_gated(version))

    def test_gated_without_an_end_date_is_paid(self):
        """Real payload of model 2830035 / version 3193296, which the site shows as
        paid. A populated `paidAccess` IS the gate; `permanent: false` with a null
        `endsAt` means gated with no published end date. It must read as PAID, not
        EARLY — with no date there is nothing to wait for, so an "it becomes free
        later" label would be a lie. Rare but real: 1 of 1660 live versions sampled.
        """
        version = {
            "id": 3193296,
            "name": "v1.0",
            "availability": "Public",
            "paidAccess": {"permanent": False, "endsAt": None},
        }
        self.assertEqual(self.api.get_access_kind(version), self.api.ACCESS_PAID)
        self.assertTrue(self.api.is_access_gated(version))

    def test_empty_paid_access_object_is_not_a_gate(self):
        """`{}` carries no gate information — don't invent one."""
        self.assertEqual(
            self.api.get_access_kind({"availability": "Public", "paidAccess": {}}),
            self.api.ACCESS_FREE,
        )

    def test_permanent_wins_over_a_stale_end_date(self):
        """`permanent` is authoritative: an endsAt alongside it must not downgrade
        the version to the (free-eventually) early-access kind."""
        self.assertEqual(
            self.api.get_access_kind(
                {"paidAccess": {"permanent": True, "endsAt": _future()}}
            ),
            self.api.ACCESS_PAID,
        )

    def test_expired_paid_window_is_free_again(self):
        self.assertEqual(
            self.api.get_access_kind({"paidAccess": {"permanent": False, "endsAt": _past()}}),
            self.api.ACCESS_FREE,
        )

    def test_legacy_availability_flag(self):
        self.assertEqual(
            self.api.get_access_kind({"availability": "EarlyAccess"}), self.api.ACCESS_EARLY
        )

    def test_legacy_early_access_ends_at(self):
        self.assertEqual(
            self.api.get_access_kind({"earlyAccessEndsAt": _future()}), self.api.ACCESS_EARLY
        )
        self.assertEqual(
            self.api.get_access_kind({"earlyAccessEndsAt": _past()}), self.api.ACCESS_FREE
        )

    def test_plain_free_version(self):
        self.assertEqual(
            self.api.get_access_kind({"id": 1, "name": "v1", "availability": "Public"}),
            self.api.ACCESS_FREE,
        )

    def test_missing_availability_field(self):
        """/api/v1/model-versions omits `availability` entirely nowadays."""
        self.assertEqual(
            self.api.get_access_kind({"id": 1, "name": "v1", "usageControl": "Download"}),
            self.api.ACCESS_FREE,
        )

    def test_malformed_input_never_raises(self):
        for bad in (None, [], "EarlyAccess", {"paidAccess": "yes"},
                    {"paidAccess": {"endsAt": "not-a-date"}},
                    {"earlyAccessEndsAt": 12345}):
            with self.subTest(bad=bad):
                self.assertEqual(self.api.get_access_kind(bad), self.api.ACCESS_FREE)
                self.assertFalse(self.api.is_access_gated(bad))


class TestAvailabilityLabel(unittest.TestCase):
    """The detail panel must not echo 'Public' for a gated version, and must name
    which of the two gates applies."""

    @classmethod
    def setUpClass(cls):
        cls.api = _load_civitai_api_with_stubs()

    def test_early_access_window_reports_when_it_turns_free(self):
        label = self.api.get_availability_label({
            "availability": "Public",
            "paidAccess": {"permanent": False, "endsAt": "2099-01-01T00:00:00.000Z"},
        })
        self.assertEqual(label, "Early Access (free after 2099-01-01)")

    def test_permanently_paid_never_mentions_a_date(self):
        label = self.api.get_availability_label({
            "availability": "Public",
            "paidAccess": {"permanent": True, "endsAt": None},
        })
        self.assertEqual(label, "Paid (Buzz purchase)")

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
            "Early Access (free after 2099-05-06)",
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


class TestStripVersionSuffixes(unittest.TestCase):
    """Dropdown labels carry decorations; resolving a selection back to an API
    version name must remove every one of them, in any order."""

    @classmethod
    def setUpClass(cls):
        cls.api = _load_civitai_api_with_stubs()

    def test_each_suffix_alone(self):
        for decorated, expected in (
            ("v1 [Installed]", "v1"),
            ("v1 (Early Access)", "v1"),
            ("v1 (Paid)", "v1"),
        ):
            with self.subTest(decorated=decorated):
                self.assertEqual(self.api.strip_version_suffixes(decorated), expected)

    def test_combined_suffixes(self):
        self.assertEqual(
            self.api.strip_version_suffixes("anima v1 [Installed] (Paid)"), "anima v1"
        )

    def test_undecorated_name_is_untouched(self):
        self.assertEqual(self.api.strip_version_suffixes("v1.5 Pruned"), "v1.5 Pruned")

    def test_empty_and_none(self):
        self.assertEqual(self.api.strip_version_suffixes(None), "")
        self.assertEqual(self.api.strip_version_suffixes(""), "")


if __name__ == "__main__":
    unittest.main()
