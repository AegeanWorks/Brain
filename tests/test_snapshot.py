"""Snapshot capture and diff (lattice transfer).

Failing-first: there is no portable run snapshot or deterministic
added/removed/changed diff. Records are keyed by ``(record_type, id)``;
volatile timestamps never count as changes; every list is sorted.
"""

import os
import tempfile
import unittest
from pathlib import Path

from agent import Agent
from snapshot import (capture_snapshot, diff_records, export_snapshot,
                      read_snapshot, run_record)


def _record(identifier, steps=13, created="a"):
    return {"record_type": "run", "id": identifier, "task": "T3_navigate",
            "seed": 15, "steps": steps, "reward": 1.0, "success": True,
            "action_sha256": "a" * 64, "syn": -0.1, "phi": 0.0,
            "created_at": created}


class TestSnapshotDiff(unittest.TestCase):
    def test_added_removed_changed_and_volatile(self):
        old = [_record("a", 13, "old"), _record("b", 6, "old")]
        new = [_record("a", 14, "new"), _record("c", 9, "new")]
        result = diff_records(old, new)
        self.assertEqual(result["added"], [{"record_type": "run", "id": "c"}])
        self.assertEqual(result["removed"], [{"record_type": "run", "id": "b"}])
        self.assertEqual(result["changed"], [{"record_type": "run",
                                              "id": "a", "fields": ["steps"]}])
        self.assertEqual(result["summary"], {"added": 1, "removed": 1,
                                             "changed": 1, "unchanged": 0})

    def test_volatile_only_change_is_unchanged(self):
        old = [_record("a", 13, "old")]
        new = [_record("a", 13, "new")]
        result = diff_records(old, new)
        self.assertEqual(result["changed"], [])
        self.assertEqual(result["summary"]["unchanged"], 1)

    def test_same_records_empty_diff(self):
        records = [_record("a"), _record("b", 6)]
        result = diff_records(records, list(records))
        self.assertEqual(result["summary"], {"added": 0, "removed": 0,
                                             "changed": 0, "unchanged": 2})

    def test_export_read_roundtrip_is_atomic(self):
        records = [_record("b", 6), _record("a")]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "snapshot.jsonl")
            export_snapshot(records, path)
            loaded = read_snapshot(path)
            leftovers = [name for name in os.listdir(tmp)
                         if name.endswith(".tmp")]
        self.assertEqual(loaded, sorted(records, key=lambda r: r["id"]))
        self.assertEqual(leftovers, [])

    def test_run_record_fields(self):
        trace = Agent().run_task("T3_navigate", 15)
        record = run_record("T3_navigate", 15, trace, {"syn": -0.1,
                                                       "phi": 0.0})
        self.assertEqual(record["id"], "T3_navigate:15")
        self.assertEqual(record["steps"], 13)
        self.assertEqual(record["reward"], 1.0)
        self.assertTrue(record["success"])
        self.assertEqual(len(record["action_sha256"]), 64)

    def test_capture_same_battery_diffs_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            cases = (("T3_navigate", 15), ("T3_navigate", 65))
            first = capture_snapshot(cases, tmp)
            second = capture_snapshot(cases, tmp)
            result = diff_records(first, second)
        self.assertEqual([record["id"] for record in first],
                         ["T3_navigate:15", "T3_navigate:65"])
        self.assertEqual([record["steps"] for record in first], [13, 6])
        self.assertEqual(result["summary"], {"added": 0, "removed": 0,
                                             "changed": 0, "unchanged": 2})


if __name__ == "__main__":
    unittest.main()
