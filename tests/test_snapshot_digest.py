"""Content-vs-graph snapshot digests and meta verification.

Failing-first: snapshots have no exact or semantic digest and no meta
verification. A re-capture with a new volatile timestamp must change the
graph digest but not the content digest; a changed steps/action/syn field
must change both.
"""

import copy
import json
import os
import tempfile
import unittest
from pathlib import Path

from snapshot import (capture_snapshot, content_sha256, export_snapshot,
                      graph_sha256, read_snapshot, snapshot_digests,
                      verify_snapshot, write_snapshot_meta)


def _record(identifier="a", steps=13, captured=1, syn=-0.1):
    return {"record_type": "run", "id": identifier, "task": "T3_navigate",
            "seed": 15, "steps": steps, "reward": 1.0, "success": True,
            "action_sha256": "a" * 64, "syn": syn, "phi": 0.0,
            "captured_at": captured}


class TestSnapshotDigest(unittest.TestCase):
    def test_graph_changes_content_stable_on_volatile(self):
        first = [_record(captured=1)]
        second = [_record(captured=2)]
        self.assertNotEqual(graph_sha256(first), graph_sha256(second))
        self.assertEqual(content_sha256(first), content_sha256(second))

    def test_real_change_changes_both_digests(self):
        first = [_record(steps=13)]
        second = [_record(steps=14)]
        self.assertNotEqual(graph_sha256(first), graph_sha256(second))
        self.assertNotEqual(content_sha256(first), content_sha256(second))

    def test_digests_shape(self):
        records = [_record("b", captured=2), _record("a", captured=1)]
        got = snapshot_digests(records)
        self.assertEqual(got["records"], 2)
        self.assertEqual(len(got["graph_sha256"]), 64)
        self.assertEqual(len(got["content_sha256"]), 64)

    def test_meta_roundtrip_and_verify(self):
        records = [_record("a", captured=1), _record("b", 6, 2)]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "snapshot.jsonl")
            meta_path = path + ".meta"
            export_snapshot(records, path, meta_path=meta_path)
            intact = verify_snapshot(path, meta_path)
            meta = json.loads(Path(meta_path).read_text(encoding="utf-8"))
            meta["content_sha256"] = "0" * 64
            Path(meta_path).write_text(json.dumps(meta), encoding="utf-8")
            bad_meta = verify_snapshot(path, meta_path)
            Path(meta_path).unlink()
            missing = verify_snapshot(path, meta_path)
        self.assertTrue(intact["ok"], intact["findings"])
        self.assertIn("content-mismatch", bad_meta["findings"])
        self.assertIn("missing-meta", missing["findings"])

    def test_changed_record_breaks_meta_verify(self):
        records = [_record("a", captured=1)]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "snapshot.jsonl")
            meta_path = path + ".meta"
            export_snapshot(records, path, meta_path=meta_path)
            changed = copy.deepcopy(records)
            changed[0]["steps"] = 14
            export_snapshot(changed, path)
            result = verify_snapshot(path, meta_path)
        self.assertFalse(result["ok"])
        self.assertIn("graph-mismatch", result["findings"])
        self.assertIn("content-mismatch", result["findings"])

    def test_capture_graph_differs_content_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            cases = (("T3_navigate", 15), ("T3_navigate", 65))
            first = capture_snapshot(cases, tmp)
            second = capture_snapshot(cases, tmp)
            first_digests = snapshot_digests(first)
            second_digests = snapshot_digests(second)
        self.assertNotEqual(first_digests["graph_sha256"],
                            second_digests["graph_sha256"])
        self.assertEqual(first_digests["content_sha256"],
                         second_digests["content_sha256"])
        self.assertEqual(first_digests["records"], 2)


if __name__ == "__main__":
    unittest.main()
