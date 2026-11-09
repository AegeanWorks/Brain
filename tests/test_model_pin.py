"""The header's model label must be pinnable, like the policy digest.

``verify_episode_header`` validates task/seed/budget/policy/episode and
optional policy/workspace pins. The ``model`` field — which backend
produced the trace — was stored verbatim and never checked. Measured: a
``T3_navigate:15`` log whose header ``model`` was rewritten to
``"totally-different-model-99b"`` passed ``verify_chain``,
``verify_episode_header`` and ``verify_action_replay``, so a log could
attribute an episode to any model.

``expected_model=`` adds the same kind of external pin the policy and
workspace already have. Without it nothing changes, so every existing
caller and pin is untouched.
"""

import os
import tempfile
import unittest

from agent import Agent
from episode_verify import verify_episode_header
from telemetry.log import Telemetry, verify_chain


def _write_log(directory, name="run.jsonl", task="T3_navigate", seed=15):
    path = os.path.join(directory, name)
    Agent().run_task_logged(task, seed, max_steps=200, log_path=path)
    header = [r for r in Telemetry(path).read_all()
              if r["type"] == "header"][0]
    return path, header


def _rewrite_model(log_path, out_path, model):
    tel = Telemetry(out_path)
    for record in Telemetry(log_path).read_all():
        kind = record.get("type")
        if kind == "header":
            tel.write_header(
                record["task"], record["budget"], policy=record.get("policy"),
                policy_sha256=record.get("policy_sha256"), model=model,
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
            tel.write_verdict(record.get("verdict"), record.get("reason"))
    return out_path


class TestModelPin(unittest.TestCase):
    def test_matching_model_pin_passes(self):
        with tempfile.TemporaryDirectory() as d:
            path, header = _write_log(d)
            result = verify_episode_header(path,
                                           expected_model=header["model"])
        self.assertTrue(result["ok"], result["findings"])
        self.assertEqual(result["expected_model"], header["model"])

    def test_wrong_model_pin_is_named(self):
        with tempfile.TemporaryDirectory() as d:
            path, header = _write_log(d)
            result = verify_episode_header(path,
                                           expected_model="some-other-model")
        self.assertFalse(result["ok"])
        self.assertIn("model-mismatch", result["findings"])
        # The digest still recomputes: only the pin disagrees.
        self.assertEqual(len(result["results"]), 1)

    def test_missing_model_is_named_when_pinned(self):
        with tempfile.TemporaryDirectory() as d:
            path, header = _write_log(d)
            stripped = _rewrite_model(path, os.path.join(d, "n.jsonl"), None)
            result = verify_episode_header(stripped, expected_model="rule")
        self.assertFalse(result["ok"])
        self.assertIn("missing-model", result["findings"])

    def test_pin_is_opt_in(self):
        with tempfile.TemporaryDirectory() as d:
            path, _header = _write_log(d)
            forged = _rewrite_model(path, os.path.join(d, "f.jsonl"),
                                    "totally-different-model-99b")
            self.assertTrue(verify_chain(forged)["ok"])
            # Unpinned: the swapped label is still accepted, as before.
            self.assertTrue(verify_episode_header(forged)["ok"])
            # Pinned: it is refused.
            pinned = verify_episode_header(forged, expected_model="rule")
        self.assertFalse(pinned["ok"])
        self.assertIn("model-mismatch", pinned["findings"])

    def test_invalid_model_pin_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path, _header = _write_log(d)
            with self.assertRaises(ValueError):
                verify_episode_header(path, expected_model="")


if __name__ == "__main__":
    unittest.main()
