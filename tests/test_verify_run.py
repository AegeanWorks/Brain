"""One aggregate verifier must compose every shipped check.

Six verifiers exist independently — chain, episode digest, action replay,
result pairing, the verdict claim and the model pin — and nothing composed
them. A consumer had to know to call each, so a forgotten check silently
weakened the verdict.

``run_verify.verify_run`` runs them all and returns the union of findings
with each layer's own result. These tests pin that it is a composition:
the honest log passes every layer, and a log that defeats one layer is
rejected by the aggregate even though the other layers still pass.
"""

import os
import tempfile
import unittest

from agent import Agent
from run_verify import LAYERS, verify_run
from telemetry.log import Telemetry, verify_chain


def _write_log(directory, name="run.jsonl", task="T3_navigate", seed=15):
    path = os.path.join(directory, name)
    Agent().run_task_logged(task, seed, max_steps=200, log_path=path)
    header = [r for r in Telemetry(path).read_all()
              if r["type"] == "header"][0]
    return path, header


def _rewrite(log_path, out_path, transform):
    """Re-emit a log through Telemetry, letting ``transform`` edit records."""
    tel = Telemetry(out_path)
    for record in Telemetry(log_path).read_all():
        kind = record.get("type")
        if kind == "header":
            header = dict(record)
            transform(kind, header)
            tel.write_header(
                header["task"], header["budget"], policy=header.get("policy"),
                policy_sha256=header.get("policy_sha256"),
                model=header.get("model"),
                episode_sha256=header.get("episode_sha256"),
                workspace_sha256=header.get("workspace_sha256"),
                seed=header.get("seed"),
                manifest_sha256=header.get("manifest_sha256"))
        elif kind == "action":
            args = dict(record.get("args") or {})
            transform(kind, args)
            tel.append_action(record["seq"], record.get("kind") or "exec",
                              args, M=record.get("M"), P=record.get("P"),
                              S=record.get("S"), hub=record.get("hub"))
        elif kind == "result":
            row = {"ok": record.get("ok"), "output": record.get("output"),
                   "cost": record.get("cost")}
            transform(kind, row)
            tel.append_result(record["seq"], row["ok"], row["output"],
                              row["cost"], M=record.get("M"),
                              P=record.get("P"), S=record.get("S"),
                              hub=record.get("hub"))
        elif kind == "verdict":
            row = {"verdict": record.get("verdict"),
                   "reason": record.get("reason")}
            transform(kind, row)
            tel.write_verdict(row["verdict"], row["reason"])
    return out_path


class TestVerifyRun(unittest.TestCase):
    def test_honest_log_passes_every_layer(self):
        with tempfile.TemporaryDirectory() as d:
            path, header = _write_log(d)
            result = verify_run(path, expected_model=header["model"])
        self.assertTrue(result["ok"], result["findings"])
        self.assertEqual(result["checked"], list(LAYERS))
        for layer in LAYERS:
            self.assertTrue(result["layers"][layer]["ok"], layer)

    def test_a_forged_action_is_rejected_by_the_aggregate(self):
        with tempfile.TemporaryDirectory() as d:
            path, _header = _write_log(d)

            def to_wait(kind, row):
                if kind == "action" and "action" in row:
                    row["action"] = "wait"

            forged = _rewrite(path, os.path.join(d, "f.jsonl"), to_wait)
            # The chain still verifies: this is the whole point.
            self.assertTrue(verify_chain(forged)["ok"])
            result = verify_run(forged)
        self.assertFalse(result["ok"])
        self.assertFalse(result["layers"]["replay"]["ok"])

    def test_a_rewritten_result_is_rejected_by_the_results_layer(self):
        with tempfile.TemporaryDirectory() as d:
            path, _header = _write_log(d)

            def bad_result(kind, row):
                if kind == "result":
                    row["cost"] = 999.0

            forged = _rewrite(path, os.path.join(d, "f.jsonl"), bad_result)
            result = verify_run(forged)
        self.assertFalse(result["ok"])
        self.assertFalse(result["layers"]["results"]["ok"])

    def test_a_wrong_model_pin_is_rejected_by_the_episode_layer(self):
        with tempfile.TemporaryDirectory() as d:
            path, _header = _write_log(d)
            result = verify_run(path, expected_model="some-other-model")
        self.assertFalse(result["ok"])
        self.assertFalse(result["layers"]["episode"]["ok"])
        self.assertIn("model-mismatch", result["layers"]["episode"]["findings"])

    def test_a_raising_layer_does_not_hide_the_others(self):
        with tempfile.TemporaryDirectory() as d:
            path, _header = _write_log(d)
            # A malformed pin makes the episode verifier raise; the other
            # layers must still run and report.
            result = verify_run(path, expected_policy_sha256="not-a-digest")
        self.assertFalse(result["ok"])
        self.assertTrue(any(f.startswith("episode:") for f in result["findings"]),
                        result["findings"])
        self.assertIn("chain", result["layers"])
        self.assertIn("replay", result["layers"])

    def test_a_missing_log_is_reported_not_raised(self):
        with tempfile.TemporaryDirectory() as d:
            result = verify_run(os.path.join(d, "nope.jsonl"))
        self.assertFalse(result["ok"])
        self.assertTrue(result["findings"])


if __name__ == "__main__":
    unittest.main()
