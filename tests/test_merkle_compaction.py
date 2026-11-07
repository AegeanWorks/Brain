"""Merkle journal compaction: one union root, original preserved or backed up.

Failing-first: the journal appends one anchor per batch and grows without
bound. Compaction must merge all anchors into one root spanning their
union, preserve every record proof, leave the original untouched by
default, and with ``replace=True`` back the original up before replacing
the live journal.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

from telemetry.log import Telemetry
from telemetry.merkle import (append_merkle_anchor, compact_merkle_journal,
                              merkle_proof_for_journal_record,
                              verify_merkle_journal, verify_merkle_proof)

STAMP = "2026-11-07T00:00:00Z"


def _log(path, records):
    tel = Telemetry(path)
    for index in range(records):
        tel.append_action(index, "step", {"i": index})


def _three_batches(path):
    for _ in range(3):
        _log(path, 8)
        append_merkle_anchor(path, batch_size=8, created_at=STAMP)
    return path + ".merkle.journal"


def _truncate(path, keep):
    lines = Path(path).read_text(encoding="utf-8").splitlines(True)
    Path(path).write_text("".join(lines[:keep]), encoding="utf-8")


def _journal_records(path):
    return [json.loads(line) for line in
            Path(path).read_text(encoding="utf-8").splitlines()]


class TestMerkleCompaction(unittest.TestCase):
    def test_copy_merges_three_batches_and_keeps_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            journal = _three_batches(path)
            original = Path(journal).read_bytes()
            compact = path + ".compact"
            report = compact_merkle_journal(path, journal,
                                            output_path=compact)
            original_after = Path(journal).read_bytes()
            source = verify_merkle_journal(path, journal)
            merged = verify_merkle_journal(path, compact)
            proofs = [merkle_proof_for_journal_record(path, compact, index)
                      for index in (0, 12, 23)]
            proof_ok = [verify_merkle_proof(item) for item in proofs]
            records = _journal_records(compact)
            meta = json.loads(Path(compact + ".compaction").read_text(
                encoding="utf-8"))
            source_head = json.loads(Path(journal).read_text(
                encoding="utf-8").splitlines()[-1])["hash"]
        self.assertEqual(report["source_anchors"], 3)
        self.assertFalse(report["replaced"])
        self.assertEqual(report["start"], 0)
        self.assertEqual(report["end"], 24)
        self.assertEqual(report["count"], 24)
        self.assertEqual(source["anchors"], 3)
        self.assertTrue(merged["ok"], merged["findings"])
        self.assertEqual(merged["anchors"], 1)
        self.assertEqual(merged["latest"]["start"], 0)
        self.assertEqual(merged["latest"]["end"], 24)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["prev"], "GENESIS")
        self.assertEqual(records[0]["hash"], report["hash"])
        self.assertEqual(proof_ok, [True, True, True])
        self.assertEqual([item["batch"] for item in proofs], [1, 1, 1])
        self.assertEqual(original, original_after)
        self.assertEqual(meta["source_anchors"], 3)
        self.assertEqual(meta["source_head"], source_head)
        self.assertEqual(meta["compact_sha256"], report["hash"])

    def test_replace_backs_up_the_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            journal = _three_batches(path)
            report = compact_merkle_journal(path, journal, replace=True)
            live = verify_merkle_journal(path, journal)
            backup = verify_merkle_journal(path, journal + ".bak")
            proof = merkle_proof_for_journal_record(path, journal, 12)
            proof_ok = verify_merkle_proof(proof)
            leftovers = [name for name in os.listdir(tmp)
                         if name.endswith(".tmp")]
            meta_exists = Path(journal + ".compaction").exists()
        self.assertTrue(report["replaced"])
        self.assertEqual(report["backup"], journal + ".bak")
        self.assertEqual(live["anchors"], 1)
        self.assertTrue(live["ok"], live["findings"])
        self.assertEqual(backup["anchors"], 3)
        self.assertTrue(backup["ok"], backup["findings"])
        self.assertTrue(proof_ok)
        self.assertEqual(leftovers, [])
        self.assertTrue(meta_exists)

    def test_missing_journal_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            _log(path, 8)
            with self.assertRaises(ValueError):
                compact_merkle_journal(path, path + ".missing")

    def test_truncated_log_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            journal = _three_batches(path)
            _truncate(path, 20)
            with self.assertRaises(ValueError) as context:
                compact_merkle_journal(path, journal)
        self.assertIn("truncated", str(context.exception))

    def test_same_output_without_replace_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            journal = _three_batches(path)
            with self.assertRaises(ValueError):
                compact_merkle_journal(path, journal, output_path=journal)

    def test_invalid_replace_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            journal = _three_batches(path)
            with self.assertRaises(ValueError):
                compact_merkle_journal(path, journal, replace="yes")

    def test_proof_outside_union_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            _log(path, 16)
            append_merkle_anchor(path, batch_size=8, created_at=STAMP)
            _log(path, 8)
            append_merkle_anchor(path, batch_size=8, created_at=STAMP)
            journal = path + ".merkle.journal"
            compact = path + ".compact"
            report = compact_merkle_journal(path, journal,
                                            output_path=compact)
            with self.assertRaises(ValueError):
                merkle_proof_for_journal_record(path, compact, 0)
        self.assertEqual(report["start"], 8)
        self.assertEqual(report["end"], 24)

    def test_compaction_metadata_is_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            journal = _three_batches(path)
            compact = path + ".compact"
            compact_merkle_journal(path, journal, output_path=compact)
            meta = json.loads(Path(compact + ".compaction").read_text(
                encoding="utf-8"))
        self.assertEqual(meta["schema"], 1)
        self.assertEqual(meta["source"], Path(journal).name)
        self.assertEqual(meta["start"], 0)
        self.assertEqual(meta["end"], 24)
        self.assertEqual(meta["count"], 24)


if __name__ == "__main__":
    unittest.main()
