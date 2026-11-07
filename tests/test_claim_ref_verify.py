"""Claim-ref verification: every referenced verdict must match a live log.

Failing-first: cycle 85 stores caller-provided refs but nothing checks
them. The verifier must read header episode_sha256 values from one or
more logs and report verified, unverified and unreferenced verdicts,
naming the claim/verdict for an unknown ref. It writes nothing.
"""

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from agent import Agent
from claims import ClaimLedger
from claims_store import save_ledger
from claims_verify import verify_claim_refs, verify_claim_store
from telemetry.log import Telemetry

STAMP = 1700000000.0
AT = "2026-11-07T00:00:00Z"


def _run(tmp, task, seed, name):
    log_path = os.path.join(tmp, name + ".jsonl")
    trace = Agent().run_task_logged(task, seed, max_steps=200,
                                    log_path=log_path)
    header = Telemetry(log_path).read_all()[0]
    return trace, header["episode_sha256"], log_path


def _ledger(ref_one, ref_two=None):
    ledger = ClaimLedger()
    ledger.add("T3:15 takes 13 steps", "steps != 13")
    ledger.record("C1", "supports", "actual=13", at=AT, ref=ref_one)
    if ref_two is not None:
        ledger.add("T3:65 takes 6 steps", "steps != 6")
        ledger.record("C2", "supports", "actual=6", at=AT, ref=ref_two)
    return ledger


class TestClaimRefVerifier(unittest.TestCase):
    def test_two_logs_verify_both_refs(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, first, log1 = _run(tmp, "T3_navigate", 15, "first")
            _, second, log2 = _run(tmp, "T3_navigate", 65, "second")
            result = verify_claim_refs(_ledger(first, second), [log1, log2])
        self.assertTrue(result["ok"], result["findings"])
        self.assertEqual(result["verified"], 2)
        self.assertEqual(result["unverified"], 0)
        self.assertEqual(result["unreferenced"], 0)
        self.assertEqual(len(result["episodes"]), 2)
        self.assertEqual(len(result["logs"]), 2)

    def test_missing_log_leaves_ref_unverified(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, first, log1 = _run(tmp, "T3_navigate", 15, "first")
            _, second, _log2 = _run(tmp, "T3_navigate", 65, "second")
            result = verify_claim_refs(_ledger(first, second), log1)
        self.assertFalse(result["ok"])
        self.assertEqual(result["verified"], 1)
        self.assertEqual(result["unverified"], 1)
        self.assertEqual(result["findings"][0]["claim"], "C2")
        self.assertEqual(result["findings"][0]["reason"], "unknown-episode")
        self.assertEqual(result["findings"][0]["ref"], second)

    def test_fabricated_ref_unverified(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, _first, log1 = _run(tmp, "T3_navigate", 15, "first")
            result = verify_claim_refs(_ledger("f" * 64), log1)
        self.assertFalse(result["ok"])
        self.assertEqual(result["verified"], 0)
        self.assertEqual(result["unverified"], 1)
        self.assertEqual(result["findings"][0]["claim"], "C1")

    def test_unreferenced_verdict_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, _first, log1 = _run(tmp, "T3_navigate", 15, "first")
            ledger = ClaimLedger()
            ledger.add("unreferenced", "never")
            ledger.record("C1", "supports", "no ref", at=AT)
            result = verify_claim_refs(ledger, log1)
        self.assertTrue(result["ok"])
        self.assertEqual(result["verified"], 0)
        self.assertEqual(result["unverified"], 0)
        self.assertEqual(result["unreferenced"], 1)

    def test_missing_log_path_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, first, _log1 = _run(tmp, "T3_navigate", 15, "first")
            with self.assertRaises(ValueError):
                verify_claim_refs(_ledger(first),
                                  os.path.join(tmp, "missing.jsonl"))

    def test_log_without_header_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "no-header.jsonl")
            tel = Telemetry(path)
            tel.append_action(0, "step", {"i": 0})
            with self.assertRaises(ValueError):
                verify_claim_refs(_ledger("a" * 64), path)

    def test_malformed_log_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bad.jsonl")
            Path(path).write_text("{bad json\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_claim_refs(_ledger("a" * 64), path)

    def test_multiple_headers_in_one_log_are_unioned(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "multi.jsonl")
            tel = Telemetry(path)
            tel.write_header("T3_navigate", 1, episode_sha256="a" * 64)
            tel.append_action(0, "step", {"i": 0})
            tel.write_header("T3_navigate", 1, episode_sha256="b" * 64)
            tel.append_action(1, "step", {"i": 1})
            result = verify_claim_refs(_ledger("a" * 64, "b" * 64), path)
        self.assertTrue(result["ok"], result["findings"])
        self.assertEqual(result["verified"], 2)
        self.assertEqual(result["episodes"], ["a" * 64, "b" * 64])

    def test_store_verifier_loads_and_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, episode, log1 = _run(tmp, "T3_navigate", 15, "first")
            store = os.path.join(tmp, "claims.json")
            save_ledger(_ledger(episode), store, saved_at=STAMP)
            result = verify_claim_store(store, log1)
        self.assertTrue(result["ok"], result["findings"])
        self.assertEqual(result["verified"], 1)

    def test_tampered_log_rejected_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, episode, log1 = _run(tmp, "T3_navigate", 15, "tampered")
            lines = Path(log1).read_text(encoding="utf-8").splitlines(True)
            for index, line in enumerate(lines):
                record = json.loads(line)
                if record.get("type") == "action":
                    record["args"]["i"] = 999
                    lines[index] = json.dumps(record, sort_keys=True) + "\n"
                    break
            Path(log1).write_text("".join(lines), encoding="utf-8")
            ledger = _ledger(episode)
            with self.assertRaises(ValueError) as context:
                verify_claim_refs(ledger, log1)
            membership = verify_claim_refs(ledger, log1, verify_logs=False)
        self.assertIn("chain verification", str(context.exception))
        self.assertTrue(membership["ok"], membership["findings"])
        self.assertEqual(membership["verified"], 1)

    def test_keyed_log_correct_and_wrong_key(self):
        key = hashlib.sha256(b"claim-ref-key").digest()
        wrong = hashlib.sha256(b"claim-ref-wrong").digest()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "keyed.jsonl")
            tel = Telemetry(path, hmac_key=key)
            tel.write_header("T3_navigate", 200, episode_sha256="a" * 64)
            tel.append_action(0, "step", {"i": 0})
            ledger = _ledger("a" * 64)
            good = verify_claim_refs(ledger, path, hmac_key=key)
            with self.assertRaises(ValueError):
                verify_claim_refs(ledger, path, hmac_key=wrong)
            unkeyed = verify_claim_refs(ledger, path)
        self.assertTrue(good["ok"], good["findings"])
        self.assertEqual(good["verified"], 1)
        self.assertTrue(unkeyed["ok"])

    def test_invalid_options_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, episode, log1 = _run(tmp, "T3_navigate", 15, "options")
            ledger = _ledger(episode)
            with self.assertRaises(ValueError):
                verify_claim_refs(ledger, log1, verify_logs="yes")
            with self.assertRaises(ValueError):
                verify_claim_refs(ledger, log1, hmac_key="text")

    def test_store_verifier_can_require_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, episode, log1 = _run(tmp, "T3_navigate", 15, "store-chain")
            store = os.path.join(tmp, "claims.json")
            save_ledger(_ledger(episode), store, saved_at=STAMP)
            lines = Path(log1).read_text(encoding="utf-8").splitlines(True)
            record = json.loads(lines[1])
            record["args"]["i"] = 999
            lines[1] = json.dumps(record, sort_keys=True) + "\n"
            Path(log1).write_text("".join(lines), encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_claim_store(store, log1)
            membership = verify_claim_store(store, log1, verify_logs=False)
        self.assertTrue(membership["ok"], membership["findings"])

    def test_invalid_inputs_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, episode, log1 = _run(tmp, "T3_navigate", 15, "first")
            with self.assertRaises(ValueError):
                verify_claim_refs({}, log1)
            with self.assertRaises(ValueError):
                verify_claim_refs(_ledger(episode), [])
            with self.assertRaises(ValueError):
                verify_claim_refs(_ledger(episode), 3)


if __name__ == "__main__":
    unittest.main()
