"""Verdict claims must be checked against the replayed trajectory.

``run_task_logged`` writes a verdict whose ``reason`` is a machine-formatted
claim: ``"steps=%d reward=%.1f"``. ``verify_action_replay`` compares the
logged step records against the world, but nothing compared that claim
with them, so a log could keep an honest trajectory and attach a verdict
asserting a different result.

Measured: a real ``T3_navigate:15`` log re-emitted with its verdict reason
rewritten to ``"steps=1 reward=99.0 success=true"`` kept a valid chain and
passed ``verify_action_replay``.

``verify_action_replay(..., check_verdict=True)`` parses the verdict reason
and rejects a step count or reward that the replay does not support. The
check is opt-in so every existing caller and pin is unchanged.
"""

import os
import re
import tempfile
import unittest

from agent import Agent
from episode_replay import parse_verdict_reason, verify_action_replay
from telemetry.log import Telemetry, verify_chain


def _write_log(directory, name="run.jsonl", task="T3_navigate", seed=15):
    path = os.path.join(directory, name)
    trace = Agent().run_task_logged(task, seed, max_steps=200, log_path=path)
    return path, trace


def _rewrite_verdict(log_path, out_path, verdict, reason):
    """Re-emit a log through Telemetry with a replaced verdict record."""
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
            tel.append_action(record["seq"], record.get("kind") or "exec",
                              dict(record.get("args") or {}),
                              M=record.get("M"), P=record.get("P"),
                              S=record.get("S"), hub=record.get("hub"))
        elif kind == "result":
            tel.append_result(record["seq"], bool(record.get("ok")),
                              record.get("output"), record.get("cost"),
                              M=record.get("M"), P=record.get("P"),
                              S=record.get("S"), hub=record.get("hub"))
        elif kind == "verdict":
            tel.write_verdict(verdict, reason)
    return out_path


class TestVerdictClaim(unittest.TestCase):
    def test_parse_verdict_reason_reads_the_machine_claim(self):
        claim = parse_verdict_reason("steps=13 reward=1.0")
        self.assertEqual(claim, {"steps": 13, "reward": 1.0})

    def test_parse_rejects_a_reason_without_the_fields(self):
        self.assertIsNone(parse_verdict_reason("just some prose"))
        self.assertIsNone(parse_verdict_reason(None))
        self.assertIsNone(parse_verdict_reason("steps=abc reward=1.0"))

    def test_honest_log_passes_verdict_check(self):
        with tempfile.TemporaryDirectory() as d:
            path, trace = _write_log(d)
            result = verify_action_replay(path, check_verdict=True)
        self.assertTrue(result["ok"], result["findings"])
        self.assertEqual(result["claimed"], {"steps": len(trace), "reward": 1.0})

    def test_inflated_reward_claim_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path, _trace = _write_log(d)
            forged = _rewrite_verdict(path, os.path.join(d, "f.jsonl"),
                                      "done", "steps=1 reward=99.0")
            # The trajectory itself is untouched, so it still replays.
            self.assertTrue(verify_action_replay(forged)["ok"])
            result = verify_action_replay(forged, check_verdict=True)
        self.assertFalse(result["ok"])
        self.assertIn("verdict-steps-mismatch", result["findings"])
        self.assertIn("verdict-reward-mismatch", result["findings"])

    def test_step_count_claim_is_checked_separately(self):
        with tempfile.TemporaryDirectory() as d:
            path, trace = _write_log(d)
            forged = _rewrite_verdict(
                path, os.path.join(d, "f.jsonl"), "done",
                "steps=%d reward=1.0" % (len(trace) + 5))
            result = verify_action_replay(forged, check_verdict=True)
        self.assertFalse(result["ok"])
        self.assertIn("verdict-steps-mismatch", result["findings"])

    def test_verdict_check_is_opt_in(self):
        with tempfile.TemporaryDirectory() as d:
            path, _trace = _write_log(d)
            forged = _rewrite_verdict(path, os.path.join(d, "f.jsonl"),
                                      "done", "steps=1 reward=99.0")
            self.assertTrue(verify_chain(forged)["ok"])
            result = verify_action_replay(forged)
        self.assertTrue(result["ok"])
        self.assertIsNone(result["claimed"])

    def test_missing_verdict_is_named_when_requested(self):
        with tempfile.TemporaryDirectory() as d:
            path, _trace = _write_log(d)
            stripped = os.path.join(d, "noverdict.jsonl")
            tel = Telemetry(stripped)
            for record in Telemetry(path).read_all():
                if record.get("type") == "verdict":
                    continue
                kind = record.get("type")
                if kind == "header":
                    tel.write_header(
                        record["task"], record["budget"],
                        policy=record.get("policy"),
                        policy_sha256=record.get("policy_sha256"),
                        model=record.get("model"),
                        episode_sha256=record.get("episode_sha256"),
                        workspace_sha256=record.get("workspace_sha256"),
                        seed=record.get("seed"),
                        manifest_sha256=record.get("manifest_sha256"))
                elif kind == "action":
                    tel.append_action(record["seq"],
                                      record.get("kind") or "exec",
                                      dict(record.get("args") or {}),
                                      M=record.get("M"), P=record.get("P"),
                                      S=record.get("S"), hub=record.get("hub"))
                elif kind == "result":
                    tel.append_result(record["seq"], bool(record.get("ok")),
                                      record.get("output"), record.get("cost"),
                                      M=record.get("M"), P=record.get("P"),
                                      S=record.get("S"), hub=record.get("hub"))
            result = verify_action_replay(stripped, check_verdict=True)
        self.assertFalse(result["ok"])
        self.assertIn("missing-verdict", result["findings"])


if __name__ == "__main__":
    unittest.main()
