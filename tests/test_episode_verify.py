"""Episode-header verification: recompute episode_sha256 from the seed.

Failing-first: the header binds an episode digest built from the initial
state, task, seed, max_steps and policy digest, but omits the seed, so
the digest cannot be independently recomputed. The header must carry the
seed and a verifier must rebuild the deterministic world and compare.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

from agent import Agent, policy_digest
from claims import ClaimLedger
from claims_verify import verify_claim_refs
from episode_verify import verify_episode_header
from identity import input_digest
from telemetry.log import Telemetry
from worlds.grid import GridWorld

AT = "2026-11-07T00:00:00Z"


def _run(tmp, task, seed, name):
    path = os.path.join(tmp, name + ".jsonl")
    Agent().run_task_logged(task, seed, max_steps=200, log_path=path)
    header = Telemetry(path).read_all()[0]
    return path, header


def _ledger(episode):
    ledger = ClaimLedger()
    ledger.add("T3:15 takes 13 steps", "steps != 13")
    ledger.record("C1", "supports", "actual=13", at=AT, ref=episode)
    return ledger


def _rewrite_header(path, mutate):
    lines = Path(path).read_text(encoding="utf-8").splitlines(True)
    header = json.loads(lines[0])
    mutate(header)
    lines[0] = json.dumps(header, sort_keys=True) + "\n"
    Path(path).write_text("".join(lines), encoding="utf-8")


class TestEpisodeVerify(unittest.TestCase):
    def test_logged_header_has_seed_and_verifies(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, header = _run(tmp, "T3_navigate", 15, "intact")
            result = verify_episode_header(path)
        self.assertEqual(header["seed"], 15)
        self.assertTrue(result["ok"], result["findings"])
        self.assertEqual(result["headers"], 1)
        self.assertEqual(result["results"][0]["recomputed"],
                         header["episode_sha256"])

    def test_wrong_seed_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, header = _run(tmp, "T3_navigate", 15, "wrong-seed")
            _rewrite_header(path, lambda value: value.__setitem__("seed", 16))
            result = verify_episode_header(path)
        self.assertFalse(result["ok"])
        self.assertIn("episode-mismatch", result["findings"])
        self.assertNotEqual(result["results"][0]["recomputed"],
                            header["episode_sha256"])

    def test_wrong_episode_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, _header = _run(tmp, "T3_navigate", 15, "wrong-episode")
            _rewrite_header(path, lambda value:
                            value.__setitem__("episode_sha256", "0" * 64))
            result = verify_episode_header(path)
        self.assertFalse(result["ok"])
        self.assertIn("episode-mismatch", result["findings"])

    def test_missing_seed_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "no-seed.jsonl")
            Telemetry(path).write_header("T3_navigate", 200,
                                         episode_sha256="a" * 64)
            result = verify_episode_header(path)
        self.assertFalse(result["ok"])
        self.assertIn("missing-seed", result["findings"])

    def test_missing_header_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "no-header.jsonl")
            Telemetry(path).append_action(0, "step", {"i": 0})
            result = verify_episode_header(path)
        self.assertFalse(result["ok"])
        self.assertIn("missing-header", result["findings"])

    def test_malformed_log_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bad.jsonl")
            Path(path).write_text("{bad json\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_episode_header(path)

    def test_expected_policy_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, _header = _run(tmp, "T3_navigate", 15, "policy-ok")
            result = verify_episode_header(
                path, expected_policy_sha256=policy_digest())
        self.assertTrue(result["ok"], result["findings"])
        self.assertEqual(result["expected_policy_sha256"], policy_digest())

    def test_expected_policy_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, header = _run(tmp, "T3_navigate", 15, "policy-wrong")
            result = verify_episode_header(
                path, expected_policy_sha256="0" * 64)
        self.assertFalse(result["ok"])
        self.assertIn("policy-mismatch", result["findings"])
        self.assertEqual(result["results"][0]["recomputed"],
                         header["episode_sha256"])

    def test_forged_policy_with_matching_episode_is_caught_by_pin(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forged.jsonl")
            fake_policy = "f" * 64
            state = GridWorld("T3_navigate", 15).reset()
            fake_episode, _projection = input_digest(state, {
                "task": "T3_navigate", "seed": 15, "max_steps": 200,
                "policy_sha256": fake_policy,
            })
            Telemetry(path).write_header(
                "T3_navigate", 200, seed=15,
                policy_sha256=fake_policy, episode_sha256=fake_episode)
            internal = verify_episode_header(path)
            pinned = verify_episode_header(
                path, expected_policy_sha256=policy_digest())
        self.assertTrue(internal["ok"], internal["findings"])
        self.assertFalse(pinned["ok"])
        self.assertIn("policy-mismatch", pinned["findings"])

    def test_invalid_expected_policy_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, _header = _run(tmp, "T3_navigate", 15, "policy-invalid")
            for value in ("text", 3, "0" * 63, "G" * 64):
                with self.assertRaises(ValueError):
                    verify_episode_header(
                        path, expected_policy_sha256=value)

    def test_claims_expected_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, header = _run(tmp, "T3_navigate", 15, "claims-policy")
            ledger = _ledger(header["episode_sha256"])
            good = verify_claim_refs(
                ledger, path, verify_episodes=True,
                expected_policy_sha256=policy_digest())
            with self.assertRaises(ValueError):
                verify_claim_refs(
                    ledger, path, verify_episodes=True,
                    expected_policy_sha256="0" * 64)
            with self.assertRaises(ValueError):
                verify_claim_refs(
                    ledger, path, expected_policy_sha256=policy_digest())
        self.assertTrue(good["ok"], good["findings"])
        self.assertEqual(good["verified"], 1)

    def test_claim_refs_verify_episodes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, header = _run(tmp, "T3_navigate", 15, "claims")
            ledger = _ledger(header["episode_sha256"])
            good = verify_claim_refs(ledger, path, verify_episodes=True)
            _rewrite_header(path, lambda value:
                            value.__setitem__("episode_sha256", "0" * 64))
            with self.assertRaises(ValueError):
                verify_claim_refs(ledger, path, verify_logs=False,
                                  verify_episodes=True)
        self.assertTrue(good["ok"], good["findings"])
        self.assertEqual(good["verified"], 1)

    def test_episode_check_is_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, header = _run(tmp, "T3_navigate", 15, "opt-in")
            _rewrite_header(path, lambda value:
                            value.__setitem__("episode_sha256", "0" * 64))
            ledger = _ledger("0" * 64)
            membership = verify_claim_refs(ledger, path, verify_logs=False)
            with self.assertRaises(ValueError):
                verify_claim_refs(ledger, path, verify_logs=False,
                                  verify_episodes=True)
        self.assertTrue(membership["ok"], membership["findings"])
        self.assertEqual(membership["verified"], 1)


if __name__ == "__main__":
    unittest.main()
