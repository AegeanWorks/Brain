"""Unit tests for memory.store.MemoryStore."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.store import MemoryStore


class TestMemoryStore(unittest.TestCase):
    def test_save_and_count(self):
        with tempfile.TemporaryDirectory() as d:
            s = MemoryStore(os.path.join(d, "m.db"))
            self.assertEqual(s.count(), 0)
            s.save("k1", "alpha beta", 0.9)
            s.save("k2", "gamma delta", 0.5)
            self.assertEqual(s.count(), 2)
            s.close()

    def test_save_overwrites_same_key(self):
        with tempfile.TemporaryDirectory() as d:
            s = MemoryStore(os.path.join(d, "m.db"))
            s.save("k1", "first", 0.1)
            s.save("k1", "second", 0.9)
            self.assertEqual(s.count(), 1)
            snap = s.snapshot()
            self.assertEqual(snap["count"], 1)
            self.assertEqual(snap["entries"][0]["content"], "second")
            s.close()

    def test_recall_fts_and_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            s = MemoryStore(os.path.join(d, "m.db"))
            s.save("k1", "red apple orchard", 0.8)
            s.save("k2", "blue river bridge", 0.7)
            hits = s.recall("apple", limit=5)
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]["key"], "k1")
            # Query with FTS5 syntax chars must not raise; falls back to LIKE.
            fallback = s.recall("apple AND (", limit=5)
            self.assertIsInstance(fallback, list)
            s.close()

    def test_recall_limit_and_order(self):
        with tempfile.TemporaryDirectory() as d:
            s = MemoryStore(os.path.join(d, "m.db"))
            for i in range(5):
                s.save("k%d" % i, "shared token", 0.5)
            hits = s.recall("shared", limit=2)
            self.assertEqual(len(hits), 2)
            self.assertEqual([h["key"] for h in hits], ["k0", "k1"])
            s.close()

    def test_snapshot_deterministic(self):
        with tempfile.TemporaryDirectory() as d:
            s = MemoryStore(os.path.join(d, "m.db"))
            s.save("kb", "two", 0.2)
            s.save("ka", "one", 0.1)
            snap = s.snapshot()
            self.assertEqual(snap["count"], 2)
            ids = [e["id"] for e in snap["entries"]]
            self.assertEqual(ids, sorted(ids))
            s.close()


if __name__ == "__main__":
    unittest.main()
