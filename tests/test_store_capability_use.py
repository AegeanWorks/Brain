"""The agent must declare whether its store writes are consumed.

The agent writes one JSON row per step into ``memories`` and the store
maintains an FTS5 index over it. Nothing in production calls ``recall``:
``get_layout`` reads the separate ``layouts`` table, and ``count`` reads a
COUNT. So the row *content* and the FTS index are write-only today.

That is not a bug — ADR-001 chose FTS5 as the memory substrate — but it is
an unstated integration fact. A reader of the telemetry cannot tell whether
a store-backed run exercised recall or merely paid for the writes. These
tests pin the measured fact and record it where the probe table lives, so
the claim "memory is read back" is either true and tested, or absent.
"""

import ast
import os
import tempfile
import unittest

from agent import Agent
from memory.store import MemoryStore, recall_terms

BRAIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP = {"__pycache__", ".git", "scratch"}


def _production_sources():
    for root, dirs, files in os.walk(BRAIN):
        dirs[:] = [d for d in dirs if d not in SKIP]
        for name in files:
            if not name.endswith(".py"):
                continue
            path = os.path.join(root, name)
            rel = os.path.relpath(path, BRAIN).replace("\\", "/")
            if rel.startswith("tests/") or rel.startswith("evals/"):
                continue
            with open(path, encoding="utf-8") as handle:
                yield rel, handle.read()


def store_capability_use():
    """Report which MemoryStore read paths production code calls.

    A capability counts as used when production code calls it on a
    store-like receiver (``memory_store.<name>(``, ``store.<name>(``,
    ``_store.<name>(``) or resolves it dynamically through
    ``getattr(store, "<name>")``. ``self.memory.recall(`` is the in-memory
    ``Memory`` ring, not the SQLite store, and must not count — that
    conflation is the reason this probe exists.
    """
    methods = ("recall", "snapshot", "get_layout", "layout_fingerprint",
               "count", "recovery_notes")
    receivers = ("memory_store", "store", "_store", "self.memory_store")
    getattr_receivers = ("store", "memory_store", "_store")
    used = {}
    for rel, body in _production_sources():
        if rel.startswith("memory/"):
            continue
        for name in methods:
            hit = any((receiver + "." + name + "(") in body
                      for receiver in receivers)
            if not hit:
                hit = any('getattr(%s, "%s"' % (receiver, name) in body
                          or "getattr(%s, '%s'" % (receiver, name) in body
                          for receiver in getattr_receivers)
            if hit:
                used.setdefault(name, set()).add(rel)
    return {name: sorted(paths) for name, paths in used.items()}


class TestStoreCapabilityUse(unittest.TestCase):
    def test_the_agent_writes_content_every_step(self):
        with tempfile.TemporaryDirectory() as d:
            store = MemoryStore(os.path.join(d, "m.db"))
            try:
                Agent(memory_store=store).run_task("T3_navigate", 15)
                rows = store.snapshot()["entries"]
                fts = store._conn.execute(
                    "SELECT COUNT(*) FROM memories_fts").fetchone()[0]
            finally:
                store.close()
        self.assertEqual(len(rows), 13)
        self.assertEqual(fts, 13)
        self.assertTrue(all(entry["content"] for entry in rows))

    def test_recall_has_no_production_caller(self):
        used = store_capability_use()
        self.assertNotIn("recall", used,
                         "recall gained a caller; update the recorded "
                         "integration fact and this test")

    def test_the_measured_capabilities_are_the_documented_ones(self):
        used = store_capability_use()
        # count is read into the M vector; get_layout backs cold recovery.
        self.assertIn("count", used)
        self.assertIn("get_layout", used)

    def test_the_index_is_populated_and_queryable_even_though_unread(self):
        # The capability works; it is simply not wired into the loop.
        with tempfile.TemporaryDirectory() as d:
            store = MemoryStore(os.path.join(d, "m.db"))
            try:
                Agent(memory_store=store).run_task("T3_navigate", 15)
                hits = store.recall("T3_navigate", limit=100)
            finally:
                store.close()
        self.assertEqual(len(hits), 13)

    def test_the_tokeniser_is_the_documented_one(self):
        self.assertEqual(recall_terms("T3_navigate AND ("), ["T3_navigate"])
        self.assertEqual(recall_terms("Türkçe"), ["Türkçe"])


if __name__ == "__main__":
    unittest.main()
