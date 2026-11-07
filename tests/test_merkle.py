"""Merkle batch anchors and inclusion proofs (merklock transfer).

Failing-first: Brain has a linear chain, an anchor sidecar and an anchor
journal, but no compact batch commitment or per-record inclusion proof.
The Merkle root commits the batch digests; a proof carries only the
sibling path. A truncated log, edited root or wrong leaf must fail.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

from telemetry.log import Telemetry
from telemetry.merkle import (merkle_proof, merkle_proof_for_record,
                              merkle_root, merkle_verify,
                              verify_merkle_anchor, verify_merkle_proof,
                              write_merkle_anchor)

STAMP = "2026-11-07T00:00:00Z"


def _leaves(count):
    return [bytes([index]) * 32 for index in range(1, count + 1)]


def _log(path, records=20):
    tel = Telemetry(path)
    for index in range(records):
        tel.append_action(index, "step", {"i": index})
    return tel


def _truncate(path, keep):
    lines = Path(path).read_text(encoding="utf-8").splitlines(True)
    Path(path).write_text("".join(lines[:keep]), encoding="utf-8")


class TestMerkleTree(unittest.TestCase):
    def test_root_and_proof_roundtrip(self):
        leaves = _leaves(8)
        root = merkle_root(leaves)
        for index, leaf in enumerate(leaves):
            proof = merkle_proof(leaves, index)
            self.assertTrue(merkle_verify(leaf, index, proof, root))
            self.assertFalse(merkle_verify(b"x" * 32, index, proof, root))
            self.assertFalse(merkle_verify(leaf, index + 1, proof, root))

    def test_odd_tree_promotes_without_duplication(self):
        leaves = _leaves(5)
        root = merkle_root(leaves)
        for index, leaf in enumerate(leaves):
            proof = merkle_proof(leaves, index)
            self.assertTrue(merkle_verify(leaf, index, proof, root))

    def test_empty_tree_is_deterministic(self):
        self.assertEqual(merkle_root([]), merkle_root([]))
        self.assertNotEqual(merkle_root([]), merkle_root(_leaves(1)))

    def test_proof_rejects_out_of_range(self):
        leaves = _leaves(3)
        with self.assertRaises(IndexError):
            merkle_proof(leaves, 3)


class TestMerkleAnchor(unittest.TestCase):
    def test_batch_anchor_and_proof(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            tel = _log(path, 20)
            anchor = tel.write_merkle_anchor(batch_size=8, created_at=STAMP)
            anchor_path = path + ".merkle"
            verified = verify_merkle_anchor(path, anchor_path)
            proof = merkle_proof_for_record(path, anchor_path, 15)
            proof_ok = verify_merkle_proof(proof)
        self.assertEqual(anchor["start"], 12)
        self.assertEqual(anchor["end"], 20)
        self.assertEqual(anchor["count"], 8)
        self.assertTrue(verified["ok"], verified["findings"])
        self.assertEqual(proof["record_index"], 15)
        self.assertEqual(proof["index"], 3)
        self.assertTrue(proof_ok)

    def test_anchor_detects_truncated_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            _log(path, 20)
            write_merkle_anchor(path, batch_size=8, created_at=STAMP)
            _truncate(path, 15)
            result = verify_merkle_anchor(path, path + ".merkle")
        self.assertFalse(result["ok"])
        self.assertTrue(any("truncated" in finding
                            for finding in result["findings"]))

    def test_anchor_detects_tampered_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            _log(path, 20)
            write_merkle_anchor(path, batch_size=8, created_at=STAMP)
            anchor_path = path + ".merkle"
            anchor = json.loads(Path(anchor_path).read_text(encoding="utf-8"))
            anchor["root"] = "0" * 64
            Path(anchor_path).write_text(json.dumps(anchor), encoding="utf-8")
            result = verify_merkle_anchor(path, anchor_path)
        self.assertFalse(result["ok"])
        self.assertIn("root-mismatch", result["findings"])

    def test_anchor_detects_edited_record_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            _log(path, 20)
            write_merkle_anchor(path, batch_size=8, created_at=STAMP)
            lines = Path(path).read_text(encoding="utf-8").splitlines(True)
            record = json.loads(lines[15])
            record["digest"] = "b" * 64
            lines[15] = json.dumps(record, sort_keys=True) + "\n"
            Path(path).write_text("".join(lines), encoding="utf-8")
            result = verify_merkle_anchor(path, path + ".merkle")
        self.assertFalse(result["ok"])

    def test_proof_rejects_tampered_leaf(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            _log(path, 20)
            write_merkle_anchor(path, batch_size=8, created_at=STAMP)
            proof = merkle_proof_for_record(path, path + ".merkle", 15)
            proof["leaf"] = "0" * 64
        self.assertFalse(verify_merkle_proof(proof))

    def test_missing_anchor_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            _log(path, 4)
            result = verify_merkle_anchor(path, path + ".merkle")
        self.assertFalse(result["ok"])
        self.assertIn("missing-anchor", result["findings"])

    def test_anchor_write_is_atomic(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            _log(path, 4)
            write_merkle_anchor(path, batch_size=4, created_at=STAMP)
            leftovers = [name for name in os.listdir(tmp)
                         if name.endswith(".tmp")]
        self.assertEqual(leftovers, [])


if __name__ == "__main__":
    unittest.main()
