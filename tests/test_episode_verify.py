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

from agent import Agent
from claims import ClaimLedger
from claims_verify import verify_claim_refs
from episode_verify import verify_episode_header
from telemetry.log import Telemetry

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
