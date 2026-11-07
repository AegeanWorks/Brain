"""Append-only Merkle batch journal and historical inclusion proofs.

Failing-first: the single ``.merkle`` sidecar is overwritten by each new
anchor, so an earlier batch root and its proofs are lost. The journal
must chain anchors with ``prev``/``hash``, keep monotonic ranges, verify
the journal against the log, and prove a record in an earlier batch
after a newer batch has been appended. The single-anchor API must stay
unchanged.
"""

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from telemetry.log import Telemetry
from telemetry.merkle import (append_merkle_anchor,
                              merkle_proof_for_journal_record,
                              merkle_proof_for_record, verify_merkle_anchor,
                              verify_merkle_journal, verify_merkle_proof,
                              write_merkle_anchor)

STAMP = "2026-11-07T00:00:00Z"


def _log(path, records=24):
    tel = Telemetry(path)
    for index in range(records):
        tel.append_action(index, "step", {"i": index})
    return tel


def _truncate(path, keep):
    lines = Path(path).read_text(encoding="utf-8").splitlines(True)
    Path(path).write_text("".join(lines[:keep]), encoding="utf-8")


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _resign(record):
    body = {key: value for key, value in record.items() if key != "hash"}
    record["hash"] = hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()
    return record


def _rewrite(path, records):
    Path(path).write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n"
                for record in records),
        encoding="utf-8")


class TestMerkleJournal(unittest.TestCase):
    def test_two_batches_chain_and_historical_proof(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            _log(path, 24)
            first = append_merkle_anchor(path, batch_size=8, created_at=STAMP)
            _log(path, 8)
            second = append_merkle_anchor(path, batch_size=8, created_at=STAMP)
            journal = path + ".merkle.journal"
            verified = verify_merkle_journal(path, journal)
            history = merkle_proof_for_journal_record(path, journal, 20)
            latest = merkle_proof_for_journal_record(path, journal, 28)
            history_ok = verify_merkle_proof(history)
            latest_ok = verify_merkle_proof(latest)
        self.assertEqual(first["start"], 16)
        self.assertEqual(first["end"], 24)
        self.assertEqual(first["prev"], "GENESIS")
        self.assertEqual(second["start"], 24)
        self.assertEqual(second["end"], 32)
        self.assertEqual(second["prev"], first["hash"])
        self.assertTrue(verified["ok"], verified["findings"])
        self.assertEqual(verified["anchors"], 2)
        self.assertEqual(verified["latest"]["hash"], second["hash"])
        self.assertEqual(history["batch"], 1)
        self.assertEqual(latest["batch"], 2)
        self.assertTrue(history_ok)
        self.assertTrue(latest_ok)

    def test_truncated_log_names_the_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            _log(path, 24)
            append_merkle_anchor(path, batch_size=8, created_at=STAMP)
            _log(path, 8)
            append_merkle_anchor(path, batch_size=8, created_at=STAMP)
            journal = path + ".merkle.journal"
            _truncate(path, 30)
            verified = verify_merkle_journal(path, journal)
            history = merkle_proof_for_journal_record(path, journal, 20)
        self.assertFalse(verified["ok"])
        self.assertTrue(any(finding.startswith("truncated-batch:2:32>30")
                            for finding in verified["findings"]))
        self.assertTrue(verify_merkle_proof(history))

    def test_deleted_first_anchor_breaks_prev(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            _log(path, 24)
            append_merkle_anchor(path, batch_size=8, created_at=STAMP)
            _log(path, 8)
            append_merkle_anchor(path, batch_size=8, created_at=STAMP)
            journal = path + ".merkle.journal"
            lines = Path(journal).read_text(encoding="utf-8").splitlines(True)
            Path(journal).write_text("".join(lines[1:]), encoding="utf-8")
            verified = verify_merkle_journal(path, journal)
        self.assertFalse(verified["ok"])
        self.assertTrue(any("prev" in finding
                            for finding in verified["findings"]))

    def test_tampered_root_with_resigned_hash_is_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            _log(path, 24)
            append_merkle_anchor(path, batch_size=8, created_at=STAMP)
            _log(path, 8)
            append_merkle_anchor(path, batch_size=8, created_at=STAMP)
            journal = path + ".merkle.journal"
            records = [json.loads(line) for line in
                       Path(journal).read_text(encoding="utf-8").splitlines()]
            records[1]["root"] = "0" * 64
            _resign(records[1])
            _rewrite(journal, records)
            verified = verify_merkle_journal(path, journal)
        self.assertFalse(verified["ok"])
        self.assertIn("root-mismatch:2", verified["findings"])

    def test_tampered_hash_is_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            _log(path, 24)
            append_merkle_anchor(path, batch_size=8, created_at=STAMP)
            _log(path, 8)
            append_merkle_anchor(path, batch_size=8, created_at=STAMP)
            journal = path + ".merkle.journal"
            records = [json.loads(line) for line in
                       Path(journal).read_text(encoding="utf-8").splitlines()]
            records[1]["root"] = "0" * 64
            _rewrite(journal, records)
            verified = verify_merkle_journal(path, journal)
        self.assertFalse(verified["ok"])
        self.assertTrue(any("hash does not match" in finding
                            for finding in verified["findings"]))

    def test_range_rollback_rejected_on_append(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            _log(path, 24)
            append_merkle_anchor(path, batch_size=8, created_at=STAMP)
            _truncate(path, 16)
            with self.assertRaises(ValueError):
                append_merkle_anchor(path, batch_size=8, created_at=STAMP)

    def test_missing_and_empty_journal_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            _log(path, 4)
            missing = verify_merkle_journal(path, path + ".merkle.journal")
            Path(path + ".merkle.journal").write_text("", encoding="utf-8")
            empty = verify_merkle_journal(path, path + ".merkle.journal")
        self.assertIn("missing-journal", missing["findings"])
        self.assertIn("empty-journal", empty["findings"])

    def test_journal_links_verify_without_a_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            _log(path, 24)
            append_merkle_anchor(path, batch_size=8, created_at=STAMP)
            _log(path, 8)
            append_merkle_anchor(path, batch_size=8, created_at=STAMP)
            verified = verify_merkle_journal(None, path + ".merkle.journal")
        self.assertTrue(verified["ok"], verified["findings"])
        self.assertEqual(verified["anchors"], 2)

    def test_proof_outside_every_batch_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            _log(path, 24)
            append_merkle_anchor(path, batch_size=8, created_at=STAMP)
            with self.assertRaises(ValueError):
                merkle_proof_for_journal_record(
                    path, path + ".merkle.journal", 3)

    def test_telemetry_wrapper_and_atomic_append(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            tel = _log(path, 12)
            record = tel.append_merkle_anchor(batch_size=4, created_at=STAMP)
            leftovers = [name for name in os.listdir(tmp)
                         if name.endswith(".tmp")]
            journal_exists = Path(path + ".merkle.journal").exists()
        self.assertEqual(record["end"], 12)
        self.assertEqual(leftovers, [])
        self.assertTrue(journal_exists)

    def test_single_anchor_api_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            _log(path, 20)
            anchor = write_merkle_anchor(path, batch_size=8, created_at=STAMP)
            verified = verify_merkle_anchor(path, path + ".merkle")
            proof = merkle_proof_for_record(path, path + ".merkle", 15)
        self.assertEqual(anchor["start"], 12)
        self.assertTrue(verified["ok"], verified["findings"])
        self.assertTrue(verify_merkle_proof(proof))


if __name__ == "__main__":
    unittest.main()
