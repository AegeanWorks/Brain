"""Model-backend seam: replay fidelity, invalid-token, raising and stall fallbacks."""

import unittest

from agent import PLANNER_POLICY, Agent, Planner as RulePlanner, policy_digest
from models.backend import ModelBackend, StubBackend


class RaisingBackend(ModelBackend):
    def generate(self, observation):
        raise RuntimeError("injected backend failure")


class WaitingBackend(ModelBackend):
    """Legal but stalled proposal: never moves or rewards."""

    def __init__(self):
        self.calls = 0

    def generate(self, observation):
        self.calls += 1
        return "wait"


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

    def test_stalled_legal_backend_falls_back_after_window(self):
        backend = WaitingBackend()
        planner = RulePlanner(backend=backend)
        trace = Agent(planner=planner).run_task("T3_navigate", 15, max_steps=200)
        self.assertTrue(trace[-1]["done"])
        self.assertEqual(len(trace), 33)
        self.assertEqual(sum(r["reward"] for r in trace), 1.0)
        self.assertEqual(planner.fallbacks, 13)
        self.assertEqual(backend.calls, 33)
        decision = planner.last_probe["model_decision"]
        self.assertFalse(decision["accepted"])
        self.assertEqual(decision["proposed"], "wait")
        self.assertEqual(decision["rule"], "down")
        self.assertGreaterEqual(decision["steps_since_reward"], 20)
        self.assertTrue(decision["distrusted"])

    def test_trust_window_none_restores_the_stall(self):
        backend = WaitingBackend()
        planner = RulePlanner(backend=backend, trust_window=None)
        trace = Agent(planner=planner).run_task("T3_navigate", 15, max_steps=200)
        self.assertEqual(len(trace), 200)
        self.assertEqual(sum(r["reward"] for r in trace), 0.0)
        self.assertEqual(planner.fallbacks, 0)
        self.assertEqual(backend.calls, 200)
        self.assertTrue(planner.last_probe["model_decision"]["accepted"])
        self.assertFalse(planner.last_probe["model_decision"]["distrusted"])

    def test_good_backend_keeps_zero_fallbacks(self):
        actions = _rule_actions("T3_navigate", 15)
        planner = RulePlanner(backend=StubBackend(actions))
        trace = Agent(planner=planner).run_task("T3_navigate", 15, max_steps=200)
        self.assertEqual([r["action"] for r in trace], actions)
        self.assertEqual(planner.fallbacks, 0)
        self.assertTrue(planner.last_probe["model_decision"]["accepted"])

    def test_policy_declares_backend_trust(self):
        self.assertEqual(PLANNER_POLICY.get("backend_trust"),
                         "stall>=20->match-only")
        legacy = dict(PLANNER_POLICY)
        legacy.pop("backend_trust", None)
        self.assertNotEqual(policy_digest(), policy_digest(legacy))

    def test_invalid_trust_window_rejected(self):
        with self.assertRaises(ValueError):
            RulePlanner(trust_window=0)
        with self.assertRaises(ValueError):
            RulePlanner(trust_window=True)
        with self.assertRaises(ValueError):
            RulePlanner(trust_window=1.5)


if __name__ == "__main__":
    unittest.main()
