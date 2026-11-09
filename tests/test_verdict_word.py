"""The verdict word must agree with the trajectory and the budget.

``Agent._episode_verdict`` writes ``done`` only for a pre-cap completion and
``truncated`` when the run consumed its step budget, even though the world
sets its own ``done`` flag at the cap. ``verify_action_replay`` checked the
verdict's steps and reward but never the word, so a truncated run could be
relabelled ``done`` while keeping its honest reason.

Measured: ``T3_navigate:15`` capped at 5, 8 and 10 steps each reported
``truncated``; rewriting only the word to ``done`` and keeping
``steps=<n> reward=0.0`` passed ``verify_action_replay(check_verdict=True)``
with ``ok: True`` and no findings.

These tests pin the word check. The honest side must stay clean: a run that
ends before its budget is ``done``, one that consumes the budget is
``truncated``.
"""

import os
import tempfile
import unittest

from agent import Agent
from episode_replay import verify_action_replay
from telemetry.log import Telemetry, verify_chain


def _write_log(directory, name, task="T3_navigate", seed=15, max_steps=200):
    path = os.path.join(directory, name)
    trace = Agent().run_task_logged(task, seed, max_steps=max_steps,
                                    log_path=path)
    return path, trace


def _rewrite_verdict(log_path, out_path, verdict, reason):
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


class TestVerdictWord(unittest.TestCase):
    def test_pre_cap_completion_is_done_and_clean(self):
        with tempfile.TemporaryDirectory() as d:
            path, trace = _write_log(d, "run.jsonl", max_steps=200)
            verdict = [r for r in Telemetry(path).read_all()
                       if r["type"] == "verdict"][0]
            result = verify_action_replay(path, check_verdict=True)
        self.assertEqual(verdict["verdict"], "done")
        self.assertLess(len(trace), 200)
        self.assertTrue(result["ok"], result["findings"])

    def test_budget_exhaustion_is_truncated_and_clean(self):
        for cap in (5, 8, 10):
            with tempfile.TemporaryDirectory() as d:
                path, trace = _write_log(d, "run.jsonl", max_steps=cap)
                verdict = [r for r in Telemetry(path).read_all()
                           if r["type"] == "verdict"][0]
                result = verify_action_replay(path, check_verdict=True)
            self.assertEqual(len(trace), cap)
            self.assertEqual(verdict["verdict"], "truncated",
                             "cap=%d" % cap)
            self.assertTrue(result["ok"], result["findings"])

    def test_truncated_run_relabelled_done_is_named(self):
        # Keep the honest reason; change only the word.
        with tempfile.TemporaryDirectory() as d:
            path, trace = _write_log(d, "run.jsonl", max_steps=5)
            honest = [r for r in Telemetry(path).read_all()
                      if r["type"] == "verdict"][0]["reason"]
            forged = _rewrite_verdict(path, os.path.join(d, "f.jsonl"),
                                      "done", honest)
            self.assertTrue(verify_chain(forged)["ok"])
            result = verify_action_replay(forged, check_verdict=True)
        self.assertFalse(result["ok"])
        self.assertIn("verdict-word-mismatch", result["findings"])

    def test_done_relabelled_truncated_is_named(self):
        with tempfile.TemporaryDirectory() as d:
            path, trace = _write_log(d, "run.jsonl", max_steps=200)
            honest = [r for r in Telemetry(path).read_all()
                      if r["type"] == "verdict"][0]["reason"]
            forged = _rewrite_verdict(path, os.path.join(d, "f.jsonl"),
                                      "truncated", honest)
            result = verify_action_replay(forged, check_verdict=True)
        self.assertFalse(result["ok"])
        self.assertIn("verdict-word-mismatch", result["findings"])

    def test_unknown_verdict_word_is_named(self):
        with tempfile.TemporaryDirectory() as d:
            path, trace = _write_log(d, "run.jsonl", max_steps=200)
            honest = [r for r in Telemetry(path).read_all()
                      if r["type"] == "verdict"][0]["reason"]
            forged = _rewrite_verdict(path, os.path.join(d, "f.jsonl"),
                                      "success", honest)
            result = verify_action_replay(forged, check_verdict=True)
        self.assertFalse(result["ok"])
        self.assertIn("verdict-word-mismatch", result["findings"])


if __name__ == "__main__":
    unittest.main()
