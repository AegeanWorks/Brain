"""Repeated-position cycle escape: memory drives a BFS exit from a loop.

Failing-first: before the fix, both three-blocker configs consume the
200-step cap with 0.0 reward. After the fix, a fully remembered episode
detects the second visit to the same cell, takes one deterministic BFS
step toward the goal, and completes. The memory-blind cut and the
``cycle_escape=False`` ablation both restore the cap, so the property
and its probe readout die with the cut.
"""

import json
import os
import tempfile
import unittest

from agent import Agent, PLANNER_POLICY, Planner, policy_digest
from models.backend import ModelBackend
from telemetry.log import Telemetry
from worlds.grid import GridWorld

ESCAPE_CASES = (
    ((6, 5), [(6, 4), (5, 5), (3, 5)], 19),
    ((6, 4), [(5, 4), (6, 0), (6, 3)], 18),
)


class _ForcedWorld(GridWorld):
    def __init__(self, target, obstacles):
        self._forced_target = [int(target[0]), int(target[1])]
        self._forced_obstacles = [[int(o[0]), int(o[1])] for o in obstacles]
        super().__init__("T3_navigate", 0)

    def _build_layout(self, rng):
        self._target = list(self._forced_target)
        self._obstacles = [list(o) for o in self._forced_obstacles]
        self._initial_items = []
        self._remaining = []
        self._cue = 0


class BlindPlanner(Planner):
    def plan(self, state, memories=None):
        return super().plan(state, None)


class DeclineBackend(ModelBackend):
    """Record the model-seam observation and force the rule fallback."""

    def __init__(self):
        self.seen = []

    def generate(self, observation):
        self.seen.append(json.loads(json.dumps(observation, sort_keys=True)))
        return None


def _run(target, obstacles, planner=None, max_steps=200):
    world = _ForcedWorld(target, obstacles)
    agent = Agent(planner=planner if planner is not None else Planner(),
                  world=world)
    return agent.run(max_steps=max_steps)


class TestCycleEscape(unittest.TestCase):
    def test_repeated_position_escape_recovers(self):
        for target, obstacles, want_steps in ESCAPE_CASES:
            trace = _run(target, obstacles)
            self.assertTrue(trace[-1]["done"])
            self.assertEqual(sum(record["reward"] for record in trace), 1.0)
            self.assertEqual(len(trace), want_steps)

    def test_memory_cut_restores_cap(self):
        for target, obstacles, _want in ESCAPE_CASES:
            trace = _run(target, obstacles, planner=BlindPlanner())
            self.assertEqual(len(trace), 200)
            self.assertEqual(sum(record["reward"] for record in trace), 0.0)

    def test_escape_disabled_restores_cap(self):
        for target, obstacles, _want in ESCAPE_CASES:
            trace = _run(target, obstacles,
                         planner=Planner(cycle_escape=False))
            self.assertEqual(len(trace), 200)
            self.assertEqual(sum(record["reward"] for record in trace), 0.0)

    def test_probe_records_escape_at_the_model_seam(self):
        target, obstacles, _want = ESCAPE_CASES[0]
        backend = DeclineBackend()
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "run.jsonl")
            world = _ForcedWorld(target, obstacles)
            agent = Agent(planner=Planner(backend=backend), world=world)
            agent.telemetry_log = Telemetry(log_path)
            trace = agent.run(max_steps=200)
            records = Telemetry(log_path).read_all()
        self.assertEqual(len(trace), 19)
        steps = [record for record in records
                 if record.get("type") == "action"
                 and record.get("kind") == "step"]
        escapes = [record for record in steps
                   if isinstance(record.get("args", {}).get("probe", {})
                                 .get("cycle_escape"), dict)]
        self.assertEqual(len(escapes), 2)
        measured = [record["args"]["probe"]["cycle_escape"]
                    for record in escapes]
        self.assertEqual(measured,
                         [{"position": [5, 2], "visits": 2,
                           "distance": 6, "action": "down"},
                          {"position": [5, 3], "visits": 2,
                           "distance": 5, "action": "right"}])
        decision = escapes[1]["args"]["probe"]["model_decision"]
        self.assertEqual(decision["rule"], "right")
        self.assertFalse(decision["accepted"])
        self.assertEqual(decision["reason"], "invalid")
        self.assertEqual(len(backend.seen), len(trace))

    def test_escape_actions_deterministic(self):
        for target, obstacles, want_steps in ESCAPE_CASES:
            first = [record["action"] for record in _run(target, obstacles)]
            again = [record["action"] for record in _run(target, obstacles)]
            self.assertEqual(len(first), want_steps)
            self.assertEqual(first, again)

    def test_policy_declares_cycle_escape(self):
        self.assertEqual(PLANNER_POLICY.get("cycle_escape"),
                         "repeat>=2->bfs")
        legacy = dict(PLANNER_POLICY)
        legacy.pop("cycle_escape", None)
        self.assertNotEqual(policy_digest(), policy_digest(legacy))
        altered = dict(PLANNER_POLICY)
        altered["cycle_escape"] = "off"
        self.assertNotEqual(policy_digest(), policy_digest(altered))

    def test_invalid_cycle_escape_rejected(self):
        with self.assertRaises(ValueError):
            Planner(cycle_escape="yes")


if __name__ == "__main__":
    unittest.main()
