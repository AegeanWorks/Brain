"""Snapshot records must carry the integrity evidence, not just the score.

``capture_snapshot`` builds ``run_record`` from a logged run, and
``diff_records`` is the gate that names a behavioral change. The record
carried only steps/reward/success/action hash/syn/phi, so the integrity
facts added later — the synergy scope, the replayed trajectory's verdict,
and the world's terminal state — were invisible to the snapshot gate. A
regression that made a run unverifiable would leave every snapshot record
byte-identical.

These tests pin the evidence fields; the existing fields are unchanged.
"""

import os
import tempfile
import unittest

from snapshot import capture_snapshot, diff_records, run_record


def _trace(steps=3, reward=0.0):
    return [{"step": i, "action": "right", "reward": reward if i == steps - 1 else 0.0,
             "done": i == steps - 1, "state": {"x": i, "y": 0}}
            for i in range(steps)]


class TestSnapshotEvidence(unittest.TestCase):
    def test_run_record_carries_the_integrity_fields(self):
        stats = {
            "syn": 0.1, "syn_n": 0.2, "phi": 0.0,
            "syn_scope": {"columns": [0, 1], "sufficient": True, "reason": None},
            "replay": {"ok": True, "steps": 3, "replayed": 3,
                       "claimed": {"steps": 3, "reward": 0.0}},
        }
        record = run_record("T3_navigate", 15, _trace(), stats)
        self.assertIn("syn_scope", record)
        self.assertIn("replay_ok", record)
        self.assertIn("verdict_claimed", record)
        self.assertEqual(record["syn_scope"]["sufficient"], True)
        self.assertEqual(record["replay_ok"], True)
        self.assertEqual(record["verdict_claimed"],
                         {"steps": 3, "reward": 0.0})

    def test_existing_fields_are_unchanged(self):
        record = run_record("T3_navigate", 15, _trace(), {"syn": 0.1, "phi": 0.0})
        for key in ("record_type", "id", "task", "seed", "steps", "reward",
                    "success", "action_sha256", "syn", "phi"):
            self.assertIn(key, record)
        self.assertEqual(record["steps"], 3)
        self.assertEqual(record["id"], "T3_navigate:15")

    def test_a_changed_scope_is_visible_to_the_diff(self):
        base = run_record("T3_navigate", 15, _trace(), {
            "syn": 0.1, "phi": 0.0,
            "syn_scope": {"columns": [0, 1], "sufficient": True, "reason": None}})
        changed = dict(base)
        changed["syn_scope"] = {"columns": [0, 1], "sufficient": False,
                                "reason": "constant-scope-column"}
        diff = diff_records([base], [changed])
        self.assertEqual(diff["summary"]["changed"], 1)
        self.assertIn("syn_scope", diff["changed"][0]["fields"])

    def test_a_failed_replay_is_visible_to_the_diff(self):
        base = run_record("T3_navigate", 15, _trace(),
                          {"syn": 0.1, "phi": 0.0, "replay": {"ok": True}})
        changed = dict(base)
        changed["replay_ok"] = False
        diff = diff_records([base], [changed])
        self.assertEqual(diff["summary"]["changed"], 1)

    def test_capture_snapshot_includes_the_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            records = capture_snapshot([("T3_navigate", 15)], d)
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertIn("syn_scope", record)
        self.assertIn("replay_ok", record)
        self.assertTrue(record["replay_ok"])

    def test_absent_stats_leave_the_evidence_null(self):
        record = run_record("T3_navigate", 15, _trace(), {})
        self.assertIsNone(record["syn_scope"])
        self.assertIsNone(record["replay_ok"])
        self.assertIsNone(record["verdict_claimed"])


if __name__ == "__main__":
    unittest.main()
