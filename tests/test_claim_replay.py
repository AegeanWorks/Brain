"""Claim refs must be checkable against the trajectory, not just the header.

``verify_claim_refs`` matches a verdict ref against the header's
``episode_sha256``. Measured: a log whose every action was replaced with
``wait`` and re-emitted through ``Telemetry`` keeps its header, so the ref
still matches and the claim verifies (``ok: True``) even though
``verify_action_replay`` reports the trajectory false. A claim could
therefore cite an episode the agent never ran.

``verify_claim_refs(..., verify_replay=True)`` composes the replay check
into ref verification: a log whose actions do not reproduce the header's
world is rejected instead of trusted. Omitting it keeps the previous
behaviour, so the check is opt-in and every existing pin is unchanged.
"""

import os
import tempfile
import unittest

from agent import Agent
from claims import ClaimLedger
from claims_verify import verify_claim_refs
from episode_replay import verify_action_replay
from telemetry.log import Telemetry, verify_chain


def _forged(log_path, out_path, action="wait"):
    """Re-emit a log through Telemetry with every step action replaced."""
    tel = Telemetry(out_path)
    for record in Telemetry(log_path).read_all():
        kind = record.get("type")
        if kind == "header":
            tel.write_header(
                record["task"], record["budget"], policy=record.get("policy"),
                policy_sha256=record.get("policy_sha256"),
                model=record.get("model"),
                episode_sha256=record.get("episode_sha256"),
                workspace_sha256=record.get("workspace_sha256"),
                seed=record.get("seed"),
                manifest_sha256=record.get("manifest_sha256"))
        elif kind == "action":
            args = dict(record.get("args") or {})
            if record.get("kind") == "step":
                args["action"] = action
            tel.append_action(record["seq"], record.get("kind") or "exec", args,
                              M=record.get("M"), P=record.get("P"),
                              S=record.get("S"), hub=record.get("hub"))
        elif kind == "result":
            tel.append_result(record["seq"], bool(record.get("ok")),
                              record.get("output"), record.get("cost"),
                              M=record.get("M"), P=record.get("P"),
                              S=record.get("S"), hub=record.get("hub"))
        elif kind == "verdict":
            tel.write_verdict(record.get("verdict"), record.get("reason"))
    return out_path


class TestClaimReplay(unittest.TestCase):
    def _fixture(self, directory):
        log = os.path.join(directory, "run.jsonl")
        Agent().run_task_logged("T3_navigate", 15, max_steps=200, log_path=log)
        header = [r for r in Telemetry(log).read_all()
                  if r.get("type") == "header"][0]
        ledger = ClaimLedger()
        claim = ledger.add("reaches target", "replay ends at the target")
        ledger.record(claim.id, "supports", "ran it",
                      ref=header["episode_sha256"])
        return log, ledger

    def test_honest_log_verifies_with_replay_enabled(self):
        with tempfile.TemporaryDirectory() as d:
            log, ledger = self._fixture(d)
            result = verify_claim_refs(ledger, log, verify_replay=True)
        self.assertTrue(result["ok"])
        self.assertEqual(result["verified"], 1)
        self.assertTrue(result["replay"])

    def test_chain_valid_forgery_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            log, ledger = self._fixture(d)
            forged = _forged(log, os.path.join(d, "forged.jsonl"))
            # The forgery keeps a valid chain and a matching ref.
            self.assertTrue(verify_chain(forged)["ok"])
            self.assertFalse(verify_action_replay(forged)["ok"])
            with self.assertRaises(ValueError) as caught:
                verify_claim_refs(ledger, forged, verify_replay=True)
        self.assertIn("replay", str(caught.exception).lower())

    def test_replay_is_opt_in_and_off_by_default(self):
        with tempfile.TemporaryDirectory() as d:
            log, ledger = self._fixture(d)
            forged = _forged(log, os.path.join(d, "forged.jsonl"))
            # Default behaviour is unchanged: the ref still matches.
            result = verify_claim_refs(ledger, forged)
        self.assertTrue(result["ok"])
        self.assertFalse(result["replay"])

    def test_replay_requires_log_verification(self):
        with tempfile.TemporaryDirectory() as d:
            log, ledger = self._fixture(d)
            with self.assertRaises(ValueError) as caught:
                verify_claim_refs(ledger, log, verify_logs=False,
                                  verify_replay=True)
        self.assertIn("verify_logs", str(caught.exception))

    def test_replay_must_be_a_bool(self):
        with tempfile.TemporaryDirectory() as d:
            log, ledger = self._fixture(d)
            with self.assertRaises(ValueError):
                verify_claim_refs(ledger, log, verify_replay="yes")


if __name__ == "__main__":
    unittest.main()
