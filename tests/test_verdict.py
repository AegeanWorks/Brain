"""Verdict facts: a step-cap run is truncated, not a success.

Failing-first harness: the world sets done when the 200-step/energy cap
is reached, so a store-blind or stalled run used to be written with
verdict "done" and reason "steps=200" despite 0.0 reward. The verdict
must distinguish genuine pre-cap completion from cap exhaustion.
"""

import os
import tempfile
import unittest
from unittest import mock

from agent import Agent, Planner
from models.backend import ModelBackend
from telemetry.log import Telemetry


class WaitingBackend(ModelBackend):
    def generate(self, observation):
        return "wait"


def _run_logged(trust_window=20, noop_guard=True, waiting=True,
                task="T3_navigate", seed=15):
    planner = None
    if waiting:
        planner = Planner(backend=WaitingBackend(),
                          trust_window=trust_window,
                          noop_guard=noop_guard)
    agent = Agent(planner=planner)
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "run.jsonl")
        trace = agent.run_task_logged(task, seed, log_path=path)
        records = Telemetry(path).read_all()
        verdict = [record for record in records
                   if record.get("type") == "verdict"][-1]
        return trace, verdict


class TestVerdictFacts(unittest.TestCase):
    def test_success_before_cap_is_done(self):
        trace, verdict = _run_logged(waiting=False)
        self.assertTrue(trace[-1]["done"])
        self.assertEqual(len(trace), 13)
        self.assertEqual(verdict["verdict"], "done")
        self.assertIn("steps=13", verdict["reason"])
        self.assertIn("reward=1.0", verdict["reason"])

    def test_cap_is_truncated_not_done(self):
        trace, verdict = _run_logged(trust_window=None, noop_guard=False)
        self.assertEqual(len(trace), 200)
        self.assertEqual(sum(record["reward"] for record in trace), 0.0)
        self.assertEqual(verdict["verdict"], "truncated")
        self.assertIn("steps=200", verdict["reason"])
        self.assertIn("reward=0.0", verdict["reason"])

    def test_legacy_predicate_ablation_labels_cap_done(self):
        legacy = lambda trace, max_steps: ("done", "steps=%d" % len(trace))
        with mock.patch.object(Agent, "_episode_verdict", side_effect=legacy):
            _trace, verdict = _run_logged(trust_window=None, noop_guard=False)
        self.assertEqual(verdict["verdict"], "done")
        self.assertEqual(verdict["reason"], "steps=200")


if __name__ == "__main__":
    unittest.main()
