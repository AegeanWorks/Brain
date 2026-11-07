"""Anchor journal: each run head commits to the previous anchor.

Failing-first: Brain has only a single mutable ``.anchor`` sidecar. A
journal of anchors makes deleting or rewinding the sidecar detectable,
and lets ``verify_chain`` compare a log against the latest committed
head. The existing single-anchor API must stay unchanged.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

from telemetry.log import (Telemetry, append_anchor, verify_anchor_journal,
                           verify_chain)

STAMP = "2026-11-07T00:00:00Z"


def _log(path, records=10):
    tel = Telemetry(path)
    for index in range(records):
        tel.append_action(index, "step", {"i": index})
    return tel


def _truncate(path, keep):
    lines = Path(path).read_text(encoding="utf-8").splitlines(True)
    Path(path).write_text("".join(lines[:keep]), encoding="utf-8")


class TestAnchorJournal(unittest.TestCase):
    def test_journal_chains_two_anchors(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            tel = _log(path, 10)
            first = tel.write_anchor_journal(created_at=STAMP)
            for index in range(10, 15):
                tel.append_action(index, "step", {"i": index})
            second = tel.write_anchor_journal(created_at=STAMP)
            journal = os.path.join(tmp, "run.jsonl.anchors")
            result = verify_anchor_journal(journal)
            chained = verify_chain(path, journal_path=journal)
        self.assertEqual(first["prev"], "GENESIS")
        self.assertEqual(second["prev"], first["hash"])
        self.assertEqual(first["seq"], 10)
        self.assertEqual(second["seq"], 15)
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(result["anchors"], 2)
        self.assertEqual(result["latest"]["hash"], second["hash"])
        self.assertTrue(chained["ok"], chained["findings"])

    def test_truncated_log_detected_against_latest_anchor(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            tel = _log(path, 20)
            tel.write_anchor_journal(created_at=STAMP)
            _truncate(path, 15)
            plain = verify_chain(path)
            anchored = verify_chain(path, journal_path=path + ".anchors")
        self.assertTrue(plain["ok"])
        self.assertEqual(plain["records"], 15)
        self.assertFalse(anchored["ok"])
        self.assertTrue(any(finding.startswith("truncated-tail:15<20")
                            for finding in anchored["findings"]))

    def test_deleted_anchor_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            tel = _log(path, 10)
            tel.write_anchor_journal(created_at=STAMP)
            tel.append_action(10, "step", {"i": 10})
            tel.write_anchor_journal(created_at=STAMP)
            journal = path + ".anchors"
            lines = Path(journal).read_text(encoding="utf-8").splitlines(True)
            Path(journal).write_text("".join(lines[1:]), encoding="utf-8")
            result = verify_anchor_journal(journal)
        self.assertFalse(result["ok"])
        self.assertTrue(any("prev" in error for error in result["errors"]))

    def test_tampered_anchor_head_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            tel = _log(path, 5)
            tel.write_anchor_journal(created_at=STAMP)
            journal = path + ".anchors"
            record = json.loads(Path(journal).read_text(encoding="utf-8"))
            record["head"] = "0" * 64
            Path(journal).write_text(json.dumps(record) + "\n", encoding="utf-8")
            result = verify_anchor_journal(journal)
        self.assertFalse(result["ok"])
        self.assertTrue(any("hash" in error for error in result["errors"]))

    def test_backwards_seq_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            journal = path + ".anchors"
            append_anchor(path, "a" * 64, 10, journal_path=journal,
                          created_at=STAMP)
            with self.assertRaises(ValueError):
                append_anchor(path, "b" * 64, 5, journal_path=journal,
                              created_at=STAMP)

    def test_missing_journal_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            _log(path, 3)
            result = verify_anchor_journal(path + ".anchors")
        self.assertFalse(result["ok"])
        self.assertIn("missing-journal", result["errors"])

    def test_single_anchor_api_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            tel = _log(path, 4)
            anchor = tel.write_anchor()
            result = verify_chain(path, anchor_path=anchor)
        self.assertTrue(result["ok"])
        self.assertEqual(result["records"], 4)


if __name__ == "__main__":
    unittest.main()
