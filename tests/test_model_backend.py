"""Model-backend seam: replay fidelity, invalid-token and raising fallbacks."""

import unittest

from agent import Agent, Planner as RulePlanner
from models.backend import ModelBackend, StubBackend


class RaisingBackend(ModelBackend):
    def generate(self, observation):
        raise RuntimeError("injected backend failure")


def _rule_actions(task, seed, max_steps=200):
    return [r["action"] for r in Agent().run_task(task, seed, max_steps=max_steps)]


class TestModelBackendSeam(unittest.TestCase):
    def test_stub_replays_rule_trace_exactly(self):
        actions = _rule_actions("T3_navigate", 15)
        self.assertEqual(len(actions), 13)
        planner = RulePlanner(backend=StubBackend(actions))
        trace = Agent(planner=planner).run_task("T3_navigate", 15, max_steps=200)
        self.assertEqual([r["action"] for r in trace], actions)
        self.assertEqual(planner.fallbacks, 0)
        self.assertTrue(trace[-1]["done"])

    def test_invalid_tokens_fall_back_to_rule(self):
        rule = _rule_actions("T3_navigate", 15)
        planner = RulePlanner(backend=StubBackend(["north"]))
        trace = Agent(planner=planner).run_task("T3_navigate", 15, max_steps=200)
        self.assertEqual([r["action"] for r in trace], rule)
        self.assertEqual(planner.fallbacks, len(trace))
        self.assertTrue(trace[-1]["done"])

    def test_raising_backend_falls_back_to_rule(self):
        rule = _rule_actions("T3_navigate", 15)
        planner = RulePlanner(backend=RaisingBackend())
        trace = Agent(planner=planner).run_task("T3_navigate", 15, max_steps=200)
        self.assertEqual([r["action"] for r in trace], rule)
        self.assertEqual(planner.fallbacks, len(trace))
        self.assertTrue(trace[-1]["done"])


if __name__ == "__main__":
    unittest.main()
