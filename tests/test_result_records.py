"""Result records are self-reports and must be checked against the step.

Each step writes an action record (``args.action``, ``args.reward``,
``args.done``) and a paired result record (``ok``, ``output``, ``cost``).
``verify_action_replay`` replays the action records, but nothing compared
the result record with the step it describes. Measured: a log whose every
result was rewritten to ``(ok=True, output='TELEPORT', cost=999.0)`` kept a
valid chain and passed ``verify_action_replay`` with the verdict check on.

These tests pin the pairing check: for each step, ``result.output`` must be
that step's action, ``result.ok`` true, and ``result.cost`` the 1.0 the
loop charges. The check is opt-in so every existing caller is unchanged.
"""

import os
import tempfile
import unittest

from agent import Agent
from episode_replay import verify_result_records, verify_action_replay
from telemetry.log import Telemetry, verify_chain


def _write_log(directory, name="run.jsonl", task="T3_navigate", seed=15):
    path = os.path.join(directory, name)
    Agent().run_task_logged(task, seed, max_steps=200, log_path=path)
    return path


def _rewrite_results(log_path, out_path, ok=True, output="TELEPORT",
                     cost=999.0):
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
            tel.append_result(record["seq"], ok, output, cost,
                              M=record.get("M"), P=record.get("P"),
                              S=record.get("S"), hub=record.get("hub"))
        elif kind == "verdict":
            tel.write_verdict(record.get("verdict"), record.get("reason"))
    return out_path


class TestResultRecords(unittest.TestCase):
    def test_honest_log_pairs_cleanly(self):
        with tempfile.TemporaryDirectory() as d:
            path = _write_log(d)
            result = verify_result_records(path)
        self.assertTrue(result["ok"], result["findings"])
        self.assertEqual(result["pairs"], 13)

    def test_altered_output_is_named(self):
        with tempfile.TemporaryDirectory() as d:
            path = _write_log(d)
            forged = _rewrite_results(path, os.path.join(d, "f.jsonl"))
            # The forgery is chain-valid...
            self.assertTrue(verify_chain(forged)["ok"])
            # ...and the action records still replay, but the result pairing
            # is now part of the verdict check, so replay rejects it too.
            replay = verify_action_replay(forged, check_verdict=True)
            self.assertFalse(replay["ok"])
            self.assertTrue(any(f.startswith("output-mismatch")
                                for f in replay["findings"]), replay["findings"])
            result = verify_result_records(forged)
        self.assertFalse(result["ok"])
        self.assertTrue(any(f.startswith("output-mismatch")
                            for f in result["findings"]), result["findings"])

    def test_altered_cost_is_named(self):
        with tempfile.TemporaryDirectory() as d:
            path = _write_log(d)
            recs = Telemetry(path).read_all()
            honest_action = [r for r in recs
                             if r["type"] == "action" and r.get("kind") == "step"][0]
            forged = _rewrite_results(path, os.path.join(d, "f.jsonl"),
                                      output=honest_action["args"]["action"],
                                      cost=999.0)
            result = verify_result_records(forged)
        self.assertFalse(result["ok"])
        self.assertTrue(any(f.startswith("cost-mismatch")
                            for f in result["findings"]), result["findings"])

    def test_failed_ok_is_named(self):
        with tempfile.TemporaryDirectory() as d:
            path = _write_log(d)
            recs = Telemetry(path).read_all()
            honest_action = [r for r in recs
                             if r["type"] == "action" and r.get("kind") == "step"][0]
            forged = _rewrite_results(path, os.path.join(d, "f.jsonl"), ok=False,
                                      output=honest_action["args"]["action"],
                                      cost=1.0)
            result = verify_result_records(forged)
        self.assertFalse(result["ok"])
        self.assertIn("ok-mismatch:0", result["findings"])

    def test_unpaired_result_is_named(self):
        with tempfile.TemporaryDirectory() as d:
            path = _write_log(d)
            stripped = os.path.join(d, "nopair.jsonl")
            tel = Telemetry(stripped)
            seen_step = False
            for record in Telemetry(path).read_all():
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
                    seen_step = True
                elif kind == "result":
                    if seen_step:
                        # Drop the first result only.
                        seen_step = False
                        continue
                    tel.append_result(record["seq"], bool(record.get("ok")),
                                      record.get("output"), record.get("cost"),
                                      M=record.get("M"), P=record.get("P"),
                                      S=record.get("S"), hub=record.get("hub"))
                elif kind == "verdict":
                    tel.write_verdict(record.get("verdict"),
                                      record.get("reason"))
            result = verify_result_records(stripped)
        self.assertFalse(result["ok"])
        self.assertTrue(any(f.startswith("unpaired-step")
                            for f in result["findings"]), result["findings"])

    def test_no_result_records_is_named(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "empty.jsonl")
            with open(path, "w", encoding="utf-8"):
                pass
            result = verify_result_records(path)
        self.assertFalse(result["ok"])
        self.assertEqual(result["findings"], ["missing-header"])


if __name__ == "__main__":
    unittest.main()
