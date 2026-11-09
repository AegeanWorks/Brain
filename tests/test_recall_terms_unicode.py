"""Search terms must keep non-ASCII words whole.

Cycle 132 added ``recall_terms`` to stop the LIKE fallback searching a raw
FTS expression. It tokenises with ``[A-Za-z0-9_]+``, so a word containing
an accented or non-Latin character is split at that character::

    recall_terms("Türkçe")  -> ["rk"]          # "ü" and "ç" are separators
    recall_terms("français")-> ["fran", "ais"]
    recall_terms("éè")      -> []              # nothing left at all

The last case is the defect class cycle 132 fixed, reintroduced for
non-ASCII input: a query with no ASCII letters returns no rows even when a
stored row contains exactly that text. These tests pin whole-word
tokenisation for non-ASCII input.
"""

import os
import tempfile
import unittest

from memory.store import MemoryStore, recall_terms


class TestRecallTermsUnicode(unittest.TestCase):
    def test_an_accented_word_stays_one_term(self):
        self.assertEqual(recall_terms("Türkçe"), ["Türkçe"])
        self.assertEqual(recall_terms("français"), ["français"])
        self.assertEqual(recall_terms("içerik"), ["içerik"])

    def test_a_word_of_only_non_ascii_characters_is_a_term(self):
        self.assertEqual(recall_terms("éè"), ["éè"])
        self.assertEqual(recall_terms("日本語"), ["日本語"])

    def test_operators_between_non_ascii_words_are_dropped(self):
        self.assertEqual(recall_terms("Türkçe AND français"),
                         ["Türkçe", "français"])

    def test_ascii_behaviour_is_unchanged(self):
        self.assertEqual(recall_terms("T3_navigate AND ("), ["T3_navigate"])
        self.assertEqual(recall_terms("a"), [])
        self.assertEqual(recall_terms("AND OR NOT NEAR"), [])
        self.assertEqual(recall_terms(""), [])

    def test_a_non_ascii_query_finds_its_row_through_the_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            store = MemoryStore(os.path.join(d, "m.db"))
            try:
                store.save("tr", "Türkçe içerik burada", 0.5)
                store.save("fr", "contenu français ici", 0.5)
                fts = store.recall("Türkçe", limit=10)
                fallback = store.recall("Türkçe AND (", limit=10)
            finally:
                store.close()
        self.assertEqual([h["key"] for h in fts], ["tr"])
        self.assertEqual([h["key"] for h in fallback], ["tr"])

    def test_a_wholly_non_ascii_query_finds_its_row(self):
        with tempfile.TemporaryDirectory() as d:
            store = MemoryStore(os.path.join(d, "m.db"))
            try:
                store.save("jp", "日本語のテキスト", 0.5)
                hits = store.recall("日本語 AND (", limit=10)
            finally:
                store.close()
        self.assertEqual([h["key"] for h in hits], ["jp"])

    def test_a_missing_non_ascii_word_is_still_a_miss(self):
        with tempfile.TemporaryDirectory() as d:
            store = MemoryStore(os.path.join(d, "m.db"))
            try:
                store.save("tr", "Türkçe içerik", 0.5)
                hits = store.recall("zzzz AND (", limit=10)
            finally:
                store.close()
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
