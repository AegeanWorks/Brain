"""Model-backend seam: replay fidelity, invalid, raising, no-op and stall fallbacks."""

import unittest

from agent import PLANNER_POLICY, Agent, Planner as RulePlanner, policy_digest
from models.backend import ModelBackend, StubBackend
from worlds.grid import SIZE


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


class BlockedBackend(ModelBackend):
    """Propose a boundary/obstacle-blocked direction when one exists."""

    def __init__(self):
        self.calls = 0

    def generate(self, observation):
        self.calls += 1
        x, y = int(observation["x"]), int(observation["y"])
        obstacles = {tuple(cell) for cell in observation.get("obstacles", [])}
        for action, dx, dy in (("up", 0, -1), ("down", 0, 1),
                               ("left", -1, 0), ("right", 1, 0)):
            nx, ny = x + dx, y + dy
            if not (0 <= nx < SIZE and 0 <= ny < SIZE) or (nx, ny) in obstacles:
                return action
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
        planner = RulePlanner(backend=backend, noop_guard=False)
        trace = Agent(planner=planner).run_task("T3_navigate", 15, max_steps=200)
        self.assertTrue(trace[-1]["done"])
        self.assertEqual(len(trace), 33)
        self.assertEqual(sum(r["reward"] for r in trace), 1.0)
        self.assertLess(backend.calls, len(trace))
        self.assertEqual(backend.calls, 21)
        self.assertEqual(planner.fallbacks, 1)
        decision = planner.last_probe["model_decision"]
        self.assertFalse(decision["accepted"])
        self.assertIsNone(decision["proposed"])
        self.assertIn(decision["rule"],
                      ("up", "down", "left", "right", "wait", "collect"))
        self.assertEqual(decision["reason"], "skipped")
        self.assertTrue(decision["skipped"])
        self.assertTrue(decision["distrusted"])
        self.assertGreaterEqual(decision["steps_since_reward"], 20)

    def test_trust_window_none_restores_the_stall(self):
        backend = WaitingBackend()
        planner = RulePlanner(backend=backend, trust_window=None,
                              noop_guard=False)
        trace = Agent(planner=planner).run_task("T3_navigate", 15, max_steps=200)
        self.assertEqual(len(trace), 200)
        self.assertEqual(sum(r["reward"] for r in trace), 0.0)
        self.assertEqual(planner.fallbacks, 0)
        self.assertEqual(backend.calls, 200)
        self.assertTrue(planner.last_probe["model_decision"]["accepted"])
        self.assertFalse(planner.last_probe["model_decision"]["distrusted"])

    def test_noop_proposal_rejected_immediately(self):
        backend = WaitingBackend()
        planner = RulePlanner(backend=backend)
        trace = Agent(planner=planner).run_task("T3_navigate", 15, max_steps=200)
        self.assertTrue(trace[-1]["done"])
        self.assertEqual(len(trace), 13)
        self.assertEqual(sum(r["reward"] for r in trace), 1.0)
        self.assertEqual(planner.fallbacks, 13)
        self.assertEqual(backend.calls, 13)
        decision = planner.last_probe["model_decision"]
        self.assertFalse(decision["accepted"])
        self.assertEqual(decision["reason"], "no-op")
        self.assertFalse(decision["distrusted"])
        self.assertTrue(decision["noop_guard"])

    def test_blocked_movement_rejected_immediately(self):
        backend = BlockedBackend()
        planner = RulePlanner(backend=backend)
        trace = Agent(planner=planner).run_task("T3_navigate", 15, max_steps=200)
        self.assertTrue(trace[-1]["done"])
        self.assertEqual(len(trace), 13)
        self.assertEqual(sum(r["reward"] for r in trace), 1.0)
        self.assertEqual(planner.fallbacks, 13)
        self.assertEqual(backend.calls, 13)
        decision = planner.last_probe["model_decision"]
        self.assertFalse(decision["accepted"])
        self.assertEqual(decision["reason"], "no-op")
        self.assertFalse(decision["distrusted"])

    def test_blocked_movement_without_guard_uses_stall_window(self):
        backend = BlockedBackend()
        planner = RulePlanner(backend=backend, noop_guard=False)
        trace = Agent(planner=planner).run_task("T3_navigate", 15, max_steps=200)
        self.assertEqual(len(trace), 33)
        self.assertEqual(sum(r["reward"] for r in trace), 1.0)
        self.assertEqual(planner.fallbacks, 1)
        self.assertEqual(backend.calls, 21)
        decision = planner.last_probe["model_decision"]
        self.assertFalse(decision["accepted"])
        self.assertTrue(decision["distrusted"])
        self.assertTrue(decision["skipped"])
        self.assertEqual(decision["reason"], "skipped")

    def test_distrust_skip_disabled_calls_after_window(self):
        backend = WaitingBackend()
        planner = RulePlanner(backend=backend, noop_guard=False,
                              skip_after_distrust=False)
        trace = Agent(planner=planner).run_task("T3_navigate", 15, max_steps=200)
        self.assertEqual(len(trace), 33)
        self.assertEqual(sum(r["reward"] for r in trace), 1.0)
        self.assertEqual(planner.fallbacks, 13)
        self.assertEqual(backend.calls, 33)
        decision = planner.last_probe["model_decision"]
        self.assertEqual(decision["proposed"], "wait")
        self.assertEqual(decision["reason"], "distrusted")
        self.assertFalse(decision["skipped"])
        self.assertTrue(decision["distrusted"])

    def test_noop_guard_independent_of_trust_window(self):
        backend = WaitingBackend()
        planner = RulePlanner(backend=backend, trust_window=None)
        trace = Agent(planner=planner).run_task("T3_navigate", 15, max_steps=200)
        self.assertEqual(len(trace), 13)
        self.assertEqual(sum(r["reward"] for r in trace), 1.0)
        self.assertEqual(planner.fallbacks, 13)
        self.assertEqual(planner.last_probe["model_decision"]["reason"], "no-op")
        self.assertFalse(planner.last_probe["model_decision"]["accepted"])

    def test_good_backend_keeps_zero_fallbacks(self):
        actions = _rule_actions("T3_navigate", 15)
        planner = RulePlanner(backend=StubBackend(actions))
        trace = Agent(planner=planner).run_task("T3_navigate", 15, max_steps=200)
        self.assertEqual([r["action"] for r in trace], actions)
        self.assertEqual(planner.fallbacks, 0)
        decision = planner.last_probe["model_decision"]
        self.assertTrue(decision["accepted"])
        self.assertEqual(decision["reason"], "accepted")

    def test_policy_declares_backend_trust_and_noop_guard(self):
        self.assertEqual(PLANNER_POLICY.get("backend_trust"),
                         "stall>=20->match-only")
        self.assertEqual(PLANNER_POLICY.get("backend_noop_guard"), "on")
        self.assertEqual(PLANNER_POLICY.get("backend_distrust_skip"), "on")
        legacy_trust = dict(PLANNER_POLICY)
        legacy_trust.pop("backend_trust", None)
        self.assertNotEqual(policy_digest(), policy_digest(legacy_trust))
        legacy_noop = dict(PLANNER_POLICY)
        legacy_noop.pop("backend_noop_guard", None)
        self.assertNotEqual(policy_digest(), policy_digest(legacy_noop))
        legacy_skip = dict(PLANNER_POLICY)
        legacy_skip.pop("backend_distrust_skip", None)
        self.assertNotEqual(policy_digest(), policy_digest(legacy_skip))

    def test_invalid_trust_window_rejected(self):
        with self.assertRaises(ValueError):
            RulePlanner(trust_window=0)
        with self.assertRaises(ValueError):
            RulePlanner(trust_window=True)
        with self.assertRaises(ValueError):
            RulePlanner(trust_window=1.5)

    def test_invalid_noop_guard_rejected(self):
        with self.assertRaises(ValueError):
            RulePlanner(noop_guard="yes")

    def test_invalid_skip_after_distrust_rejected(self):
        with self.assertRaises(ValueError):
            RulePlanner(skip_after_distrust="yes")


if __name__ == "__main__":
    unittest.main()
