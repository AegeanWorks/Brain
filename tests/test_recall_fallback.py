"""A malformed FTS query must not make the fallback find nothing.

``MemoryStore.recall`` tries FTS5 ``MATCH`` first and falls back to ``LIKE``
when the query raises ``OperationalError``. The fallback uses the query
verbatim as a LIKE pattern, so a query containing FTS syntax characters
becomes a literal substring search: ``"T3_navigate AND ("`` matches no row
whose key is ``T3_navigate:15:0``.

Measured against real agent-written rows (13 rows, keys like
``T3_navigate:15:3``, JSON content):

  recall("T3_navigate")        -> 13   (FTS path)
  recall("T3_navigate AND (")  ->  0   (fallback searches the whole string)

A caller that passes user text through gets silence instead of the rows it
asked for. The fix is to search the fallback for the query's ordinary
tokens, not the raw expression.
"""

import os
import tempfile
import unittest

from agent import Agent
from memory.store import MemoryStore, recall_terms


class TestRecallFallback(unittest.TestCase):
    def _store_with_rows(self, tmp):
        store = MemoryStore(os.path.join(tmp, "m.db"))
        Agent(memory_store=store).run_task("T3_navigate", 15)
        return store

    def test_recall_terms_strips_fts_operators(self):
        self.assertEqual(recall_terms("T3_navigate AND ("), ["T3_navigate"])
        self.assertEqual(recall_terms('"target" OR *'), ["target"])
        self.assertEqual(recall_terms("plain"), ["plain"])
        self.assertEqual(recall_terms(""), [])

    def test_a_malformed_query_still_finds_the_rows(self):
        with tempfile.TemporaryDirectory() as d:
            store = self._store_with_rows(d)
            try:
                hits = store.recall("T3_navigate AND (", limit=100)
            finally:
                store.close()
        self.assertEqual(len(hits), 13, "fallback lost the matching rows")

    def test_a_well_formed_query_is_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            store = self._store_with_rows(d)
            try:
                good = store.recall("T3_navigate", limit=100)
            finally:
                store.close()
        self.assertEqual(len(good), 13)

    def test_a_query_with_no_terms_returns_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            store = self._store_with_rows(d)
            try:
                hits = store.recall("((( ", limit=100)
            finally:
                store.close()
        self.assertEqual(hits, [])

    def test_the_fallback_preserves_limit_and_ordering(self):
        with tempfile.TemporaryDirectory() as d:
            store = self._store_with_rows(d)
            try:
                hits = store.recall("T3_navigate AND (", limit=3)
            finally:
                store.close()
        self.assertEqual(len(hits), 3)
        self.assertEqual([h["key"] for h in hits],
                         ["T3_navigate:15:0", "T3_navigate:15:1",
                          "T3_navigate:15:2"])

    def test_no_match_is_still_no_match(self):
        with tempfile.TemporaryDirectory() as d:
            store = self._store_with_rows(d)
            try:
                hits = store.recall("zzzz AND (", limit=100)
            finally:
                store.close()
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
