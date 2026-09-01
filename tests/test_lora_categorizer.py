"""Tests for the heuristic LoRA categorizer.

Regression cover for the report by CivitAI user ODSP1994, who requested the
feature and then found it misfiling in bulk:

    "the system does get confused with some style loras being classified as
     characters/sliders"

The old implementation failed three separate ways, each covered below:

1. ``_detect_slider_semantics`` ran before any tag matching, across the whole
   free-text description, with patterns including ``(?:more|less)\\s+\\w+`` and
   ``(?:increase|decrease|boost|reduce|enhance|...)\\s+\\w+``. Ordinary CivitAI
   description copy therefore forced Slider regardless of tags.
2. Keywords were matched as bare substrings, so "person" hit *personality* and
   "pose" hit *composition*.
3. First hit won while iterating a dict starting at Character, and name_hints
   carries the filename — which for a LoRA usually contains a character name.

scripts/lora_categorizer has no gradio/WebUI imports, so it is imported directly
rather than through the module stubs the other suites need.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.lora_categorizer import (  # noqa: E402
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MANUAL,
    CONFIDENCE_MEDIUM,
    LORA_CATEGORIES,
    categorize,
    categorize_lora_by_tags,
)


class TestStyleLorasAreNotSliders(unittest.TestCase):
    """Cause 1: the description must never be able to force a Slider."""

    def test_more_detail_in_the_description_does_not_win(self):
        # "(?:more|less)\s+\w+" used to fire here and return Slider outright.
        category, confidence = categorize(
            ['style'],
            'Auto',
            'This LoRA adds more detail to your images.',
            ['ghibli_style_v2'],
        )
        self.assertEqual(category, 'Style')
        self.assertEqual(confidence, CONFIDENCE_HIGH)

    def test_enhance_in_the_description_does_not_win(self):
        category, _ = categorize(
            ['style'], 'Auto', 'Will enhance your renders considerably.', ['x'])
        self.assertEqual(category, 'Style')

    def test_boost_and_reduce_prose_does_not_win(self):
        category, _ = categorize(
            ['style'], 'Auto', 'Boost saturation and reduce noise.', ['x'])
        self.assertEqual(category, 'Style')

    def test_slider_verbs_in_the_description_alone_suggest_nothing(self):
        # No tags, no name clues — prose alone must not manufacture a category.
        category, confidence = categorize(
            [], 'Auto', 'Increase the vibrance and boost contrast.', ['untitled'])
        self.assertIsNone(category)
        self.assertIsNone(confidence)

    def test_style_with_no_tags_still_resolves_from_the_name(self):
        category, confidence = categorize(
            [], 'Auto', 'A detailed anime style with more vibrant colors.',
            ['anime_style_v3'])
        self.assertEqual(category, 'Style')
        self.assertEqual(confidence, CONFIDENCE_MEDIUM)


class TestRealSlidersStillDetected(unittest.TestCase):
    """Tightening the rules must not cost us the true positives."""

    def test_slider_tag(self):
        category, confidence = categorize(['slider'], 'Auto', '', ['age_thing'])
        self.assertEqual(category, 'Slider')
        self.assertEqual(confidence, CONFIDENCE_HIGH)

    def test_slider_in_an_underscored_filename(self):
        # Underscores are word characters, so \bslider\b cannot match inside
        # "detail_slider_xl" unless separators are split first.
        category, _ = categorize([], 'Auto', '', ['detail_slider_xl'])
        self.assertEqual(category, 'Slider')

    def test_slider_in_a_hyphenated_filename(self):
        category, _ = categorize([], 'Auto', '', ['age-slider-v2'])
        self.assertEqual(category, 'Slider')

    def test_slider_in_a_dotted_filename(self):
        category, _ = categorize([], 'Auto', '', ['age.slider.v2'])
        self.assertEqual(category, 'Slider')

    def test_adjuster_and_booster_names(self):
        self.assertEqual(categorize([], 'Auto', '', ['weight_adjuster'])[0], 'Slider')
        self.assertEqual(categorize([], 'Auto', '', ['detail_booster'])[0], 'Slider')

    def test_slider_tag_beats_a_character_filename(self):
        category, _ = categorize(['slider'], 'Auto', '', ['makima_v2'])
        self.assertEqual(category, 'Slider')


class TestWordBoundaries(unittest.TestCase):
    """Cause 2: substring matching produced nonsense hits."""

    def test_personality_is_not_a_character(self):
        self.assertIsNone(categorize([], 'Auto', 'Gives a strong personality.', ['x'])[0])

    def test_persona_is_not_a_character(self):
        self.assertIsNone(categorize([], 'Auto', 'Adopts a persona.', ['x'])[0])

    def test_composition_is_not_a_pose(self):
        self.assertIsNone(categorize([], 'Auto', 'Improves composition.', ['x'])[0])

    def test_purpose_is_not_a_pose(self):
        self.assertIsNone(categorize([], 'Auto', 'Built for one purpose.', ['x'])[0])

    def test_detailed_is_not_utility(self):
        # "detail" is a Utility keyword; "detailed" must not trip it.
        self.assertIsNone(categorize([], 'Auto', 'Very detailed output.', ['x'])[0])

    def test_the_actual_word_still_matches(self):
        self.assertEqual(categorize([], 'Auto', 'Adds detail.', ['x'])[0], 'Utility')
        self.assertEqual(categorize(['character'], 'Auto', '', ['x'])[0], 'Character')

    def test_multi_word_keyword_tolerates_extra_whitespace(self):
        self.assertEqual(categorize(['art  style'], 'Auto', '', ['x'])[0], 'Style')
        self.assertEqual(categorize(['art\nstyle'], 'Auto', '', ['x'])[0], 'Style')


class TestSourceWeighting(unittest.TestCase):
    """Cause 3: order of evidence, not order of a dict, decides."""

    def test_a_style_tag_beats_a_character_filename(self):
        # The exact shape of the complaint: the filename carries a character
        # name, but the author tagged the model as a style.
        category, confidence = categorize(['style'], 'Auto', '', ['makima_style'])
        self.assertEqual(category, 'Style')
        self.assertEqual(confidence, CONFIDENCE_HIGH)

    def test_a_name_beats_the_description(self):
        category, confidence = categorize(
            [], 'Auto', 'Set in a detailed environment.', ['gothic_dress'])
        self.assertEqual(category, 'Clothing')
        self.assertEqual(confidence, CONFIDENCE_MEDIUM)

    def test_description_only_matches_report_low_confidence(self):
        category, confidence = categorize([], 'Auto', 'A landscape backdrop.', ['x'])
        self.assertEqual(category, 'Background')
        self.assertEqual(confidence, CONFIDENCE_LOW)

    def test_contested_tags_are_reported_as_low_confidence(self):
        # Tagged both ways, which is common on CivitAI. The winner is decided by
        # a deterministic tie-break, so it is surfaced as a coin flip rather than
        # as a confident answer — LoraDex sorts these to the top for review.
        category, confidence = categorize(['character', 'style'], 'Auto', '', ['x'])
        self.assertEqual(confidence, CONFIDENCE_LOW)
        self.assertIn(category, ('Character', 'Style'))

    def test_result_is_deterministic_regardless_of_tag_order(self):
        first = categorize(['character', 'style'], 'Auto', '', ['x'])
        second = categorize(['style', 'character'], 'Auto', '', ['x'])
        self.assertEqual(first, second,
                         'the outcome must not depend on iteration order')

    def test_repeated_evidence_accumulates(self):
        # Tag + name + description all pointing at Style beats a lone rival tag.
        category, _ = categorize(
            ['style', 'character'], 'Auto', 'An art style pack.', ['ink_style'])
        self.assertEqual(category, 'Style')


class TestManualCategoryContract(unittest.TestCase):
    """The three-state sentinel that used to collapse into one."""

    def test_explicit_category_wins_and_is_returned_verbatim(self):
        category, confidence = categorize(['character'], 'Style', 'a character', ['x'])
        self.assertEqual(category, 'Style')
        self.assertEqual(confidence, CONFIDENCE_MANUAL)

    def test_the_string_none_disables_detection(self):
        # LoraDex writes loraCategory: null for this; it must stay opted out.
        self.assertEqual(categorize(['character'], 'None', 'a character', ['x']),
                         (None, None))

    def test_none_is_case_insensitive(self):
        self.assertEqual(categorize(['character'], 'none', '', ['x']), (None, None))

    def test_auto_runs_the_heuristic(self):
        self.assertEqual(categorize(['character'], 'Auto', '', ['x'])[0], 'Character')

    def test_empty_string_runs_the_heuristic(self):
        self.assertEqual(categorize(['character'], '', '', ['x'])[0], 'Character')

    def test_omitted_argument_runs_the_heuristic(self):
        # The old default meant "disabled", so every caller that omitted this
        # argument silently got None back — which is why the Browser card badge
        # and the download-time category subfolder never worked.
        self.assertEqual(categorize(['character'])[0], 'Character')

    def test_whitespace_around_a_manual_value_is_tolerated(self):
        self.assertEqual(categorize(['character'], '  Auto  ', '', ['x'])[0], 'Character')


class TestInputRobustness(unittest.TestCase):
    """These run over a whole model library, including junk sidecars."""

    def test_no_input_at_all(self):
        self.assertEqual(categorize([], 'Auto', None, None), (None, None))
        self.assertEqual(categorize(None, 'Auto', None, None), (None, None))

    def test_empty_and_none_entries_are_skipped(self):
        self.assertEqual(categorize([None, ''], 'Auto', '', [None, '']), (None, None))

    def test_non_string_tags_do_not_raise(self):
        category, _ = categorize([123, None, 'style'], 'Auto', '', ['x'])
        self.assertEqual(category, 'Style')

    def test_a_very_long_description_is_truncated_not_rejected(self):
        # Descriptions can be several KB of HTML and this runs per file.
        padding = 'lorem ipsum ' * 5000
        category, _ = categorize(['style'], 'Auto', padding, ['x'])
        self.assertEqual(category, 'Style')

    def test_keyword_beyond_the_scan_limit_is_ignored(self):
        buried = ('x ' * 4000) + 'landscape'
        self.assertIsNone(categorize([], 'Auto', buried, ['plain'])[0])


class TestWrapperCompatibility(unittest.TestCase):
    """civitai_api and civitai_download import the category-only form."""

    def test_wrapper_returns_only_the_category(self):
        self.assertEqual(categorize_lora_by_tags(['style'], 'Auto', '', ['x']), 'Style')

    def test_wrapper_returns_none_when_nothing_matches(self):
        self.assertIsNone(categorize_lora_by_tags([], 'Auto', '', ['x']))

    def test_wrapper_honours_the_disabled_state(self):
        self.assertIsNone(categorize_lora_by_tags(['style'], 'None', '', ['x']))


class TestCategoryTable(unittest.TestCase):
    """Guard the taxonomy the Organization folders are named after."""

    def test_the_expected_categories_exist(self):
        self.assertEqual(
            set(LORA_CATEGORIES),
            {'Character', 'Style', 'Clothing', 'Concept',
             'Pose', 'Background', 'Utility', 'Slider'})

    def test_slider_no_longer_carries_generic_prose_words(self):
        # These matched ordinary description copy and caused the misfiling.
        for word in ('more', 'less', 'enhance', 'adjust', 'strength', 'boost'):
            self.assertNotIn(word, LORA_CATEGORIES['Slider'])

    def test_every_category_resolves_from_its_own_name_as_a_tag(self):
        for category in LORA_CATEGORIES:
            with self.subTest(category=category):
                self.assertEqual(categorize([category.lower()], 'Auto', '', [])[0],
                                 category)


if __name__ == '__main__':
    unittest.main()
