"""Tests for LoraDex's filter and sort layer.

Covers the review workflow CivitAI user ODSP1994 described as his workaround:

    "Might be easier to accept all the changes without looking and then going
     through each category through the option on top and correctly putting them
     where they belong"

Accepting every suggestion unseen was not a preference — it was forced. The
Category dropdown filtered on ``saved_category``, so a suggestion that had not
been applied yet was invisible to it, and there was no way to review
"everything suggested as Style" before committing to it. Filtering now works on
``current_category`` (what the row actually shows), which makes review-then-apply
possible in the order a person would want to do it.

civitai_file_manage imports gradio and modules.shared, neither available outside
Forge, so the two pure functions under test are mirrored here and
test_shipped_* reads the shipped source to keep the mirrors honest.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

_SCRIPTS = os.path.join(os.path.dirname(__file__), '..', 'scripts')

LORA_DEX_SORT_MODES = ['Name', 'Least confident first', 'Category', 'Base model']

_CONFIDENCE_RANK = {None: 0, 'low': 1, 'medium': 2, 'high': 3, 'manual': 4}


def _filter(data, base_filter, category_filter, pending_only, search_term,
            suggested_only=False, pending_paths=()):
    """Mirror of civitai_file_manage._filter_lora_dex_data.

    gl.lora_dex_pending is module state in the real thing; passed in here.
    """
    result = list(data)

    term = (search_term or '').strip().lower()
    if term:
        result = [d for d in result
                  if term in d['name'].lower() or term in d.get('file_name', '').lower()]

    if base_filter:
        if isinstance(base_filter, str):
            base_filter = [base_filter]
        base_filter = [b for b in base_filter if b]
        if base_filter:
            bf_lower = {b.lower() for b in base_filter}
            result = [d for d in result if d.get('base_model', '').lower() in bf_lower]

    if category_filter and str(category_filter).lower() != 'all':
        cat = str(category_filter).strip()
        result = [d for d in result if d.get('current_category', 'Auto') == cat]

    if suggested_only:
        result = [d for d in result if d.get('suggested_category')]

    if pending_only:
        result = [d for d in result if d.get('file_path') in pending_paths]

    return result


def _sort(data, sort_mode):
    """Mirror of civitai_file_manage._sort_lora_dex_data."""
    mode = (sort_mode or 'Name').strip()
    if mode == 'Least confident first':
        return sorted(data, key=lambda d: (
            _CONFIDENCE_RANK.get(d.get('suggested_confidence'), 0),
            d.get('name', '').lower()))
    if mode == 'Category':
        return sorted(data, key=lambda d: (
            str(d.get('current_category') or 'Auto'), d.get('name', '').lower()))
    if mode == 'Base model':
        return sorted(data, key=lambda d: (
            d.get('base_model', '').lower(), d.get('name', '').lower()))
    return sorted(data, key=lambda d: d.get('name', '').lower())


def _row(name, saved='Auto', suggested=None, confidence=None,
         base='Illustrious', file_name=None):
    return {
        'file_path': f'D:/loras/{name}.safetensors',
        'name': name,
        'file_name': file_name if file_name is not None else name.lower().replace(' ', '_'),
        'base_model': base,
        'saved_category': saved,
        'current_category': suggested or saved,
        'suggested_category': suggested,
        'suggested_confidence': confidence,
    }


class TestCategoryFilter(unittest.TestCase):
    """The fix that removes the need for the accept-everything workaround."""

    def setUp(self):
        self.data = [
            _row('Applied Style', saved='Style'),
            _row('Suggested Style', suggested='Style', confidence='high'),
            _row('Suggested Character', suggested='Character', confidence='low'),
            _row('Untouched'),
        ]

    def test_filtering_by_category_includes_unapplied_suggestions(self):
        found = _filter(self.data, None, 'Style', False, '')
        names = {d['name'] for d in found}
        self.assertEqual(names, {'Applied Style', 'Suggested Style'},
                         'a suggestion must be reviewable before it is applied')

    def test_filtering_by_category_excludes_other_categories(self):
        found = _filter(self.data, None, 'Character', False, '')
        self.assertEqual([d['name'] for d in found], ['Suggested Character'])

    def test_auto_matches_rows_with_no_category_at_all(self):
        found = _filter(self.data, None, 'Auto', False, '')
        self.assertEqual([d['name'] for d in found], ['Untouched'])

    def test_all_is_a_passthrough(self):
        self.assertEqual(len(_filter(self.data, None, 'All', False, '')), 4)

    def test_missing_category_filter_is_a_passthrough(self):
        self.assertEqual(len(_filter(self.data, None, None, False, '')), 4)


class TestSuggestedOnlyFilter(unittest.TestCase):
    def setUp(self):
        self.data = [
            _row('Has Suggestion', suggested='Style', confidence='high'),
            _row('Already Saved', saved='Character'),
            _row('Nothing'),
        ]

    def test_keeps_only_rows_carrying_a_suggestion(self):
        found = _filter(self.data, None, 'All', False, '', suggested_only=True)
        self.assertEqual([d['name'] for d in found], ['Has Suggestion'])

    def test_off_by_default(self):
        self.assertEqual(len(_filter(self.data, None, 'All', False, '')), 3)

    def test_combines_with_the_category_filter(self):
        found = _filter(self.data, None, 'Style', False, '', suggested_only=True)
        self.assertEqual([d['name'] for d in found], ['Has Suggestion'])


class TestSearch(unittest.TestCase):
    def setUp(self):
        self.data = [
            _row('Ghibli Backgrounds', file_name='ghibli_bg_v2'),
            _row('Ink Wash', file_name='sumi_e_style'),
        ]

    def test_search_matches_the_model_name(self):
        found = _filter(self.data, None, 'All', False, 'ghibli')
        self.assertEqual([d['name'] for d in found], ['Ghibli Backgrounds'])

    def test_search_matches_the_filename_too(self):
        # The table shows a Filename column, so it must be searchable; several
        # LoRAs can share one CivitAI model name.
        found = _filter(self.data, None, 'All', False, 'sumi_e')
        self.assertEqual([d['name'] for d in found], ['Ink Wash'])

    def test_search_is_case_insensitive(self):
        self.assertEqual(len(_filter(self.data, None, 'All', False, 'GHIBLI')), 1)

    def test_blank_search_is_a_passthrough(self):
        self.assertEqual(len(_filter(self.data, None, 'All', False, '   ')), 2)


class TestBaseModelFilter(unittest.TestCase):
    def setUp(self):
        self.data = [
            _row('A', base='Illustrious'),
            _row('B', base='Pony'),
            _row('C', base='SDXL 1.0'),
        ]

    def test_single_value_as_a_string(self):
        self.assertEqual([d['name'] for d in _filter(self.data, 'Pony', 'All', False, '')], ['B'])

    def test_multiple_values(self):
        found = _filter(self.data, ['Pony', 'SDXL 1.0'], 'All', False, '')
        self.assertEqual({d['name'] for d in found}, {'B', 'C'})

    def test_case_insensitive(self):
        self.assertEqual([d['name'] for d in _filter(self.data, ['pony'], 'All', False, '')], ['B'])

    def test_empty_entries_are_ignored(self):
        self.assertEqual(len(_filter(self.data, [None, ''], 'All', False, '')), 3)


class TestSorting(unittest.TestCase):
    def setUp(self):
        self.data = [
            _row('Zebra', suggested='Style', confidence='high'),
            _row('Alpha', suggested='Character', confidence='low'),
            _row('Mango', suggested='Pose', confidence='medium'),
            _row('Delta', base='Pony'),
        ]

    def test_least_confident_first_puts_the_coin_flips_on_top(self):
        # The point of the mode: review the guesses, skip the certainties.
        order = [d['name'] for d in _sort(self.data, 'Least confident first')]
        self.assertEqual(order, ['Delta', 'Alpha', 'Mango', 'Zebra'])

    def test_name_is_the_default(self):
        self.assertEqual([d['name'] for d in _sort(self.data, 'Name')],
                         ['Alpha', 'Delta', 'Mango', 'Zebra'])

    def test_unknown_mode_falls_back_to_name(self):
        self.assertEqual([d['name'] for d in _sort(self.data, 'Nonsense')],
                         ['Alpha', 'Delta', 'Mango', 'Zebra'])

    def test_none_mode_falls_back_to_name(self):
        self.assertEqual([d['name'] for d in _sort(self.data, None)],
                         ['Alpha', 'Delta', 'Mango', 'Zebra'])

    def test_category_groups_then_orders_by_name(self):
        order = [d['current_category'] for d in _sort(self.data, 'Category')]
        self.assertEqual(order, sorted(order), 'categories must come out grouped')

    def test_base_model_sort_groups_by_base_then_name(self):
        result = _sort(self.data, 'Base model')
        bases = [d['base_model'] for d in result]
        self.assertEqual(bases, sorted(bases), 'base models must come out grouped')
        # Illustrious sorts before Pony, and within it names are alphabetical.
        self.assertEqual([d['name'] for d in result],
                         ['Alpha', 'Mango', 'Zebra', 'Delta'])

    def test_sorting_never_drops_or_duplicates_rows(self):
        for mode in LORA_DEX_SORT_MODES:
            with self.subTest(mode=mode):
                result = _sort(self.data, mode)
                self.assertEqual(len(result), len(self.data))
                self.assertEqual({d['name'] for d in result},
                                 {d['name'] for d in self.data})


class TestPendingCount(unittest.TestCase):
    """What 'Apply changes on ALL pages' promises to write."""

    def test_counts_every_row_differing_from_what_is_saved(self):
        data = [
            _row('One', suggested='Style'),
            _row('Two', suggested='Character'),
            _row('Three', saved='Pose'),
        ]
        pending = [d for d in data if d['current_category'] != d['saved_category']]
        self.assertEqual(len(pending), 2)

    def test_an_applied_row_is_not_pending(self):
        row = _row('Done', saved='Style', suggested='Style')
        row['current_category'] = 'Style'
        self.assertEqual(row['current_category'], row['saved_category'])


class TestShippedImplementation(unittest.TestCase):
    """Keep the mirrors above from drifting from the real code."""

    def setUp(self):
        with open(os.path.join(_SCRIPTS, 'civitai_file_manage.py'),
                  'r', encoding='utf-8') as handle:
            self.source = handle.read()

    def test_shipped_filter_uses_current_category(self):
        self.assertIn("d.get('current_category', 'Auto') == cat", self.source,
                      'filtering on saved_category is the bug this fixes')

    def test_shipped_filter_searches_the_filename(self):
        self.assertIn("term in d.get('file_name', '').lower()", self.source)

    def test_shipped_sort_modes_match(self):
        self.assertIn(str(LORA_DEX_SORT_MODES), self.source)

    def test_apply_all_reads_the_dataset_not_the_dom(self):
        start = self.source.index('def apply_all_lora_dex_suggestions(')
        end = self.source.index('\ndef ', start + 1)
        body = self.source[start:end]
        self.assertIn('_current_lora_dex_selection()', body,
                      'applying across all pages must not depend on rendered rows')

    def test_apply_everywhere_is_two_stage(self):
        self.assertIn('def preview_all_lora_dex_suggestions(', self.source,
                      'a bulk write must state its size before it runs')


if __name__ == '__main__':
    unittest.main()
