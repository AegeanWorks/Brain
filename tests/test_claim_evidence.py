"""Claim/evidence cross-link: verdict refs cite logged episode digests.

Failing-first: verdict evidence is free text with no run identity. A
logged run exposes its episode digest in the header; a verdict `ref` must
preserve that digest through claim-store save/load and keep two runs
distinct.
"""

import os
import tempfile
import unittest
from pathlib import Path

from agent import Agent
from claims import ClaimLedger
from claims_store import load_ledger, save_ledger, verify_ledger_file
from telemetry.log import Telemetry

STAMP = 1700000000.0
AT = "2026-11-07T00:00:00Z"


def _run(tmp, task, seed, name):
    log_path = os.path.join(tmp, name + ".jsonl")
    agent = Agent()
    trace = agent.run_task_logged(task, seed, max_steps=200,
                                  log_path=log_path)
    header = Telemetry(log_path).read_all()[0]
    return agent, trace, header


class TestClaimEvidence(unittest.TestCase):
    def test_logged_episode_ref_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent, trace, header = _run(tmp, "T3_navigate", 15, "run")
            episode = header["episode_sha256"]
            path = os.path.join(tmp, "claims.json")
            ledger = ClaimLedger()
            ledger.add("T3:15 takes 13 steps", "steps != 13")
            ledger.record("C1", "supports", "actual=13", at=AT,
                          ref=episode)
            save_ledger(ledger, path, saved_at=STAMP)
            loaded = load_ledger(path)
            verified = verify_ledger_file(path)
            verdict = loaded.get("C1").verdicts[0]
        self.assertEqual(len(trace), 13)
        self.assertEqual(agent.last_episode_sha256, episode)
        self.assertEqual(len(episode), 64)
        self.assertEqual(verdict.ref, episode)
        self.assertEqual(loaded.get("C1").status, "supported")
        self.assertTrue(verified["ok"], verified["findings"])

    def test_two_run_refs_are_distinct(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, _, first_header = _run(tmp, "T3_navigate", 15, "first")
            _, _, second_header = _run(tmp, "T3_navigate", 65, "second")
            first_episode = first_header["episode_sha256"]
            second_episode = second_header["episode_sha256"]
            path = os.path.join(tmp, "claims.json")
            ledger = ClaimLedger()
            ledger.add("T3:15 takes 13 steps", "steps != 13")
            ledger.record("C1", "supports", "actual=13", at=AT,
                          ref=first_episode)
            ledger.add("T3:65 takes 6 steps", "steps != 6")
            ledger.record("C2", "supports", "actual=6", at=AT,
                          ref=second_episode)
            save_ledger(ledger, path, saved_at=STAMP)
            loaded = load_ledger(path)
            refs = [loaded.get("C1").verdicts[0].ref,
                    loaded.get("C2").verdicts[0].ref]
        self.assertEqual(refs, [first_episode, second_episode])
        self.assertNotEqual(first_episode, second_episode)

    def test_legacy_payload_without_ref_still_loads(self):
        payload = {
            "claims": [{
                "id": "C1", "text": "legacy", "kill_test": "never",
                "status": "supported", "confidence": 0.5,
                "verdicts": [{"status": "supports", "evidence": "old",
                              "at": AT}],
            }]
        }
        ledger = ClaimLedger.from_dict(payload)
        self.assertIsNone(ledger.get("C1").verdicts[0].ref)

    def test_invalid_ref_does_not_change_history(self):
        ledger = ClaimLedger()
        ledger.add("text", "kill")
        with self.assertRaises(ValueError):
            ledger.record("C1", "supports", "ok", at=AT, ref="")
        self.assertEqual(ledger.get("C1").verdicts, ())
        with self.assertRaises(ValueError):
            ledger.record("C1", "supports", "ok", at=AT, ref=7)
        self.assertEqual(ledger.get("C1").verdicts, ())


if __name__ == "__main__":
    unittest.main()
