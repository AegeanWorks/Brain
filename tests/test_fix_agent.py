"""Failing-first pins for genuine review findings on agent.py.

Each test targets one still-live finding at HEAD. The two findings that were
already fixed by later commits (partial-deadline-map-discards-all and
discarded-preaction-prediction) are not re-tested here; see
reports/reforge/genuine/fix-agent.md for the skip evidence.
"""

import json
import unittest
from unittest import mock

from agent import Agent, Planner, _tour_audit
from models.backend import ModelBackend


class _RaisingContextWorld:
    def signal_context(self, state):
        raise RuntimeError("context read failed")


class _BadValuesWorld:
    def signal_context(self, state):
        return ["not-a-number"]


class _WaitBackend(ModelBackend):
    """Legal but stalled proposal that differs from the rule move."""

    def generate(self, observation):
        return "wait"


class _BadGetHub:
    def get(self, *args, **kwargs):
        raise OSError("collect hub read failure")


class _FailingCollectAgent(Agent):
    """Fail only the collected_positions persistence write, nothing else."""

    def hub_write(self, content):
        if "collected_positions" in content:
            raise OSError("collect persistence failure")
        return super().hub_write(content)


class _FpErrorStore:
    """Store with a complete stored layout but a failing fingerprint read."""

    def __init__(self, row):
        self._row = row
        self.saves = []

    def get_layout(self, task, seed, fingerprint=None):
        return None if fingerprint is not None else self._row

    def layout_fingerprint(self, task, seed):
        raise OSError("fingerprint read failed")

    def save_layout(self, task, seed, content, replace=False, fingerprint=None):
        self.saves.append((task, seed, content, replace, fingerprint))


class _FpWorld:
    task_id = "T3_navigate"
    seed = 0

    def layout_fingerprint(self):
        return "current-geometry"


class TestFixAgent(unittest.TestCase):
    # -- S10 context-error-misattributed-to-bind -----------------------
    def test_context_hook_raise_not_counted_as_bind(self):
        agent = Agent()
        agent.world = _RaisingContextWorld()
        out = agent._world_context({"x": 0, "y": 0})
        self.assertEqual(out, {})
        self.assertEqual(agent._substrate_errors["bind"], 0)
        self.assertEqual(agent._substrate_errors.get("world_context"), 1)

    def test_context_non_numeric_not_counted_as_bind(self):
        agent = Agent()
        agent.world = _BadValuesWorld()
        out = agent._world_context({"x": 0, "y": 0})
        self.assertEqual(out, {})
        self.assertEqual(agent._substrate_errors["bind"], 0)
        self.assertEqual(agent._substrate_errors.get("world_context"), 1)

    # -- S25 discard-prediction-basis ----------------------------------
    def test_prediction_basis_is_recorded(self):
        agent = Agent()
        agent.run_task("T1_forage", 7, max_steps=3)
        events = agent.telemetry.events()
        self.assertGreater(len(events), 0)
        self.assertIn("prediction_basis", events[0])
        self.assertIsInstance(events[0]["prediction_basis"], str)
        self.assertTrue(events[0]["prediction_basis"])

    # -- S41 fingerprint-read-error-overwrites-layout ------------------
    def test_fingerprint_read_error_does_not_overwrite_layout(self):
        row = json.dumps({"target": [6, 7], "obstacles": [[6, 1]],
                          "task": "T3_navigate", "x": 0, "y": 0})
        store = _FpErrorStore(row)
        agent = Agent(memory_store=store, world=_FpWorld())
        with mock.patch.object(Agent, "_layout_complete", return_value=True):
            agent._remember_layout({"task": "T3_navigate", "x": 0, "y": 0})
        self.assertEqual(store.saves, [])

    # -- S49 tour-optimal-always-true ----------------------------------
    def test_tour_optimal_uses_actual_chosen_goal(self):
        # [0,1] is the optimal first item (length 4); [2,0] is suboptimal
        # (length 5). A planner that picked [2,0] must read optimal=False.
        report = _tour_audit((0, 0), [[2, 0], [0, 1]], rule_goal=[2, 0])
        self.assertEqual(report["chosen"], [2, 0])
        self.assertEqual(report["best_length"], 4)
        self.assertEqual(report["chosen_length"], 5)
        self.assertFalse(report["optimal"])

    def test_tour_optimal_true_when_actual_goal_is_optimal(self):
        report = _tour_audit((0, 0), [[2, 0], [0, 1]], rule_goal=[0, 1])
        self.assertEqual(report["chosen"], [0, 1])
        self.assertEqual(report["chosen_length"], 4)
        self.assertTrue(report["optimal"])

    # -- S62 trust-gate-fails-open -------------------------------------
    def test_hub_read_failure_fails_closed(self):
        planner = Planner(backend=_WaitBackend(), trust_window=20,
                          noop_guard=False)

        # plan() reads the hub twice: once unwrapped near the top, once inside
        # the trust-gate try/except. Fail only the second (trust-gate) read.
        calls = {"n": 0}

        def flaky():
            calls["n"] += 1
            if calls["n"] >= 2:
                raise OSError("hub read failure")
            return {}

        planner.read_hub = flaky
        state = {"task": "T3_navigate", "x": 0, "y": 0,
                 "target": [2, 0], "steps": 0}
        planner.plan(state, [])
        decision = planner.last_probe["model_decision"]
        self.assertTrue(decision["distrusted"])
        self.assertFalse(decision["accepted"])
        self.assertGreaterEqual(decision["steps_since_reward"], 20)

    # -- S66 collect-error-mislabeled ----------------------------------
    def test_collect_persistence_error_not_counted_as_bind(self):
        agent = _FailingCollectAgent()
        trace = agent.run_task("T1_forage", 7, max_steps=30)
        self.assertGreater(len(trace), 0)
        self.assertEqual(agent._substrate_errors["bind"], 0)
        self.assertGreaterEqual(agent._substrate_errors.get("hub_collect", 0), 1)


if __name__ == "__main__":
    unittest.main()
