"""Tests for user-defined LoRA categories.

The built-in list is a suggestion, not the only valid taxonomy. A user's own
category — typed in, already declared in a sidecar, or implied by a folder they
made themselves — has to survive every path through the tool.

It did not. The LoraDex row rendered a closed <select> built solely from
LORA_DEX_CATEGORIES, so a sidecar holding loraCategory "Anime" matched no
<option>, no option carried `selected`, and the browser fell back to the first
entry — "Auto". The row displayed Auto while the file said Anime, and one click
on that row's apply button sent "Auto" back, deleting the category the user had
set. Silent data loss, with nothing on screen suggesting a change was pending.

The field is now a free-text input backed by a datalist, so the stored value is
always what is displayed. The one constraint kept is safety: a category is
concatenated into a filesystem path by the organizer, so it must be a single
safe path segment.

scripts/lora_categorizer and scripts/organization_paths have no gradio imports,
so they are imported directly.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.lora_categorizer import (  # noqa: E402
    LORA_CATEGORIES,
    MAX_CATEGORY_LENGTH,
    RESERVED_CATEGORY_STATES,
    is_reserved_state,
    merge_category_suggestions,
    sanitize_category,
)
from scripts.organization_paths import category_from_current_folder  # noqa: E402


class TestSanitizeAcceptsUserTaxonomy(unittest.TestCase):
    """Unfamiliar is not invalid — only unsafe is."""

    def test_a_category_we_never_heard_of_is_accepted(self):
        self.assertEqual(sanitize_category('Anime'), ('Anime', None))

    def test_multi_word_categories_are_accepted(self):
        self.assertEqual(sanitize_category('Cyberpunk 2077'), ('Cyberpunk 2077', None))

    def test_non_ascii_categories_are_accepted(self):
        self.assertEqual(sanitize_category('Ilustração'), ('Ilustração', None))
        self.assertEqual(sanitize_category('アニメ'), ('アニメ', None))

    def test_surrounding_whitespace_is_trimmed_without_a_note(self):
        self.assertEqual(sanitize_category('  Anime  '), ('Anime', None))

    def test_the_users_own_casing_is_preserved(self):
        self.assertEqual(sanitize_category('anime')[0], 'anime')
        self.assertEqual(sanitize_category('ANIME')[0], 'ANIME')


class TestSanitizeRejectsUnsafeNames(unittest.TestCase):
    """The category becomes a folder name, so it must be one safe segment."""

    def test_path_separators_are_replaced(self):
        clean, note = sanitize_category('Anime/Style')
        self.assertEqual(clean, 'Anime-Style')
        self.assertIsNotNone(note, 'the user must be told the name changed')

    def test_backslash_is_replaced(self):
        self.assertEqual(sanitize_category(r'Anime\Style')[0], 'Anime-Style')

    def test_parent_traversal_cannot_survive(self):
        clean, note = sanitize_category('../../etc')
        self.assertNotIn('..', clean)
        self.assertNotIn('/', clean)
        self.assertIsNotNone(note)

    def test_windows_invalid_characters_are_replaced(self):
        clean, _ = sanitize_category('My:Cat*?"<>|')
        for char in ':*?"<>|':
            self.assertNotIn(char, clean)

    def test_control_characters_are_replaced(self):
        clean, _ = sanitize_category('Ani\x00me\x1f')
        self.assertNotIn('\x00', clean)
        self.assertNotIn('\x1f', clean)

    def test_windows_device_names_are_refused(self):
        for name in ('CON', 'con', 'PRN', 'AUX', 'NUL', 'COM1', 'LPT9'):
            with self.subTest(name=name):
                clean, note = sanitize_category(name)
                self.assertIsNone(clean)
                self.assertIsNotNone(note, 'a refusal must explain itself')

    def test_device_name_with_extension_is_refused(self):
        self.assertIsNone(sanitize_category('con.txt')[0])

    def test_trailing_dots_and_spaces_are_stripped(self):
        # Windows drops these silently, which would desync the stored category
        # from the folder actually created.
        clean, note = sanitize_category('Anime. ')
        self.assertEqual(clean, 'Anime')
        self.assertIsNotNone(note)

    def test_overlong_names_are_shortened_with_a_note(self):
        clean, note = sanitize_category('x' * 200)
        self.assertEqual(len(clean), MAX_CATEGORY_LENGTH)
        self.assertIsNotNone(note)

    def test_empty_input_is_not_an_error(self):
        for value in (None, '', '   '):
            with self.subTest(value=value):
                self.assertEqual(sanitize_category(value), (None, None))

    def test_a_name_with_nothing_usable_is_refused_with_a_reason(self):
        clean, note = sanitize_category('///')
        # Either it is refused outright, or it survives as separators-replaced;
        # what must never happen is a path separator reaching the caller.
        if clean is not None:
            self.assertNotIn('/', clean)
        else:
            self.assertIsNotNone(note)


class TestReservedStates(unittest.TestCase):
    """'Auto' and 'None' are states, not categories."""

    def test_states_round_trip_with_canonical_casing(self):
        self.assertEqual(sanitize_category('auto'), ('Auto', None))
        self.assertEqual(sanitize_category('NONE'), ('None', None))

    def test_is_reserved_state(self):
        for value in ('Auto', 'auto', ' None ', 'NONE'):
            self.assertTrue(is_reserved_state(value))
        for value in ('Anime', 'Style', '', None):
            self.assertFalse(is_reserved_state(value))

    def test_states_are_never_offered_as_suggestions(self):
        merged = merge_category_suggestions(['Auto', 'None', 'Anime'])
        for state in RESERVED_CATEGORY_STATES:
            self.assertNotIn(state, merged)
        self.assertIn('Anime', merged)


class TestMergeSuggestions(unittest.TestCase):
    def test_builtin_categories_come_first(self):
        merged = merge_category_suggestions(['Zebra', 'Anime'])
        self.assertEqual(merged[:len(LORA_CATEGORIES)], list(LORA_CATEGORIES))

    def test_user_categories_follow_alphabetically(self):
        merged = merge_category_suggestions(['Zebra', 'Anime', 'Mecha'])
        extras = merged[len(LORA_CATEGORIES):]
        self.assertEqual(extras, ['Anime', 'Mecha', 'Zebra'])

    def test_deduplication_is_case_insensitive(self):
        merged = merge_category_suggestions(['anime', 'Anime', 'ANIME'])
        matches = [c for c in merged if c.lower() == 'anime']
        self.assertEqual(len(matches), 1)

    def test_the_users_first_spelling_wins(self):
        # Never show someone a competing capitalization of their own word.
        merged = merge_category_suggestions(['anime'], ['Anime'])
        self.assertIn('anime', merged)
        self.assertNotIn('Anime', merged)

    def test_a_builtin_is_not_duplicated_by_a_user_entry(self):
        merged = merge_category_suggestions(['style', 'Style'])
        self.assertEqual(len([c for c in merged if c.lower() == 'style']), 1)

    def test_blank_entries_are_dropped(self):
        merged = merge_category_suggestions([None, '', '   ', 'Anime'])
        self.assertIn('Anime', merged)
        self.assertNotIn('', merged)

    def test_multiple_sources_are_combined(self):
        merged = merge_category_suggestions(['FromSidecar'], ['FromFolder'], ['FromTag'])
        for name in ('FromSidecar', 'FromFolder', 'FromTag'):
            self.assertIn(name, merged)

    def test_no_sources_returns_just_the_builtins(self):
        self.assertEqual(merge_category_suggestions(), list(LORA_CATEGORIES))


class TestCustomFolderProtection(unittest.TestCase):
    """A folder the user invented deserves the same protection as ours."""

    def _p(self, *parts):
        return os.path.abspath(os.path.join(*parts))

    def test_builtin_folder_is_recognized_without_extras(self):
        path = self._p('D:/loras/Pony/Slider/x.safetensors')
        self.assertEqual(category_from_current_folder(path), 'Slider')

    def test_custom_folder_needs_to_be_declared(self):
        path = self._p('D:/loras/Pony/Anime/x.safetensors')
        self.assertIsNone(category_from_current_folder(path))
        self.assertEqual(category_from_current_folder(path, {'Anime'}), 'Anime')

    def test_declared_match_is_case_insensitive(self):
        path = self._p('D:/loras/Pony/Anime/x.safetensors')
        self.assertEqual(category_from_current_folder(path, {'anime'}), 'Anime',
                         'the folder as it exists on disk is what is returned')

    def test_an_undeclared_folder_is_still_organizable(self):
        # The crucial limit: treating every folder as a category would exempt
        # whole trees from ever being organized.
        path = self._p('D:/loras/ill_loras/A/x.safetensors')
        self.assertIsNone(category_from_current_folder(path, {'Anime'}))

    def test_empty_extras_behave_like_none(self):
        path = self._p('D:/loras/Pony/Anime/x.safetensors')
        self.assertIsNone(category_from_current_folder(path, set()))
        self.assertIsNone(category_from_current_folder(path, []))

    def test_file_at_the_library_root(self):
        self.assertIsNone(category_from_current_folder(self._p('D:/loras/x.safetensors'),
                                                       {'Anime'}))


class TestShippedImplementation(unittest.TestCase):
    """Guard the wiring that the unit tests above cannot reach."""

    def setUp(self):
        path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'civitai_file_manage.py')
        with open(path, 'r', encoding='utf-8') as handle:
            self.source = handle.read()

    def test_the_category_field_is_an_input_not_a_closed_select(self):
        self.assertIn('<input class="loradex-cat', self.source,
                      'a closed <select> silently dropped any custom value')
        self.assertNotIn('<select class="loradex-cat"', self.source)

    def test_the_field_renders_the_stored_value(self):
        self.assertIn('value="{html.escape(str(current), quote=True)}"', self.source)

    def test_saving_sanitizes_first(self):
        start = self.source.index('def _save_lora_category(')
        end = self.source.index('\ndef ', start + 1)
        body = self.source[start:end]
        self.assertIn('_categorizer.sanitize_category(category)', body,
                      'this value is concatenated into a filesystem path')

    def test_organization_uses_the_declared_set_not_every_folder(self):
        self.assertIn('declared_lora_categories(folders_to_check)', self.source)
        self.assertIn('category_from_current_folder(file_path, declared_categories)', self.source)

    def test_declared_categories_come_from_sidecars(self):
        start = self.source.index('def declared_lora_categories(')
        end = self.source.index('\ndef ', start + 1)
        body = self.source[start:end]
        self.assertIn('get_lora_category_from_sidecar', body,
                      'a name counts only once a sidecar declares it')

    def test_the_filter_dropdown_offers_user_categories(self):
        self.assertIn('def lora_dex_filter_choices(', self.source)


if __name__ == '__main__':
    unittest.main()
