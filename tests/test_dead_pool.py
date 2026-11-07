"""Dead-pool guard: drop a dead goal step only when a live path is closer.

The two-blocker pin (target [7,5], obstacles [6,1],[7,2]) enters the
dead goal step [7,1] even though the live backup [6,0] is closer. The
guard compares BFS distances and drops the dead step only when a live
candidate is at least as close; the ablation restores the 18-step
detour while the blind memory cut still truncates.
"""

import json
import os
import tempfile
import unittest

from agent import Agent, PLANNER_POLICY, Planner, policy_digest
from models.backend import ModelBackend
from telemetry.log import Telemetry
from tests.test_multi_obstacle import (BlindPlanner, _ForcedMultiWorld,
                                       _multi_steps)

TARGET = (7, 5)
OBSTACLES = [(6, 1), (7, 2)]


class DeclineBackend(ModelBackend):
    def __init__(self):
        self.seen = []

    def generate(self, observation):
        self.seen.append(json.loads(json.dumps(observation, sort_keys=True)))
        return None


class TestDeadPool(unittest.TestCase):
    def test_probe_records_excluded_dead_step(self):
        backend = DeclineBackend()
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "run.jsonl")
            agent = Agent(
                planner=Planner(backend=backend),
                world=_ForcedMultiWorld(TARGET, OBSTACLES),
                telemetry_log=Telemetry(log_path))
            trace = agent.run(max_steps=200)
            steps = [record for record in Telemetry(log_path).read_all()
                     if record.get("type") == "action"
                     and record.get("kind") == "step"]
        self.assertEqual(len(trace), 16)
        probes = [record for record in steps
                  if isinstance(record.get("args", {}).get("probe", {})
                                .get("dead_pool"), dict)]
        self.assertEqual(len(probes), 1)
        first = probes[0]["args"]["probe"]
        self.assertEqual(first["dead_pool"],
                         {"position": [7, 0],
                          "excluded": [["down", [7, 1]]],
                          "live_distance": 8, "dead_distance": 10})
        self.assertEqual(probes[0]["args"]["action"], "left")
        decision = first["model_decision"]
        self.assertEqual(decision["rule"], "left")
        self.assertFalse(decision["accepted"])
        self.assertEqual(decision["reason"], "invalid")
        self.assertEqual(len(backend.seen), len(trace))

    def test_ablation_restores_detour(self):
        trace = _multi_steps(TARGET, OBSTACLES,
                             planner=Planner(dead_pool_filter=False))
        self.assertEqual(len(trace), 18)
        self.assertEqual(sum(record["reward"] for record in trace), 1.0)

    def test_blind_still_truncates(self):
        trace = _multi_steps(TARGET, OBSTACLES, planner=BlindPlanner())
        self.assertEqual(len(trace), 200)
        self.assertEqual(sum(record["reward"] for record in trace), 0.0)

    def test_guard_deterministic(self):
        first = [record["action"] for record in _multi_steps(TARGET, OBSTACLES)]
        again = [record["action"] for record in _multi_steps(TARGET, OBSTACLES)]
        self.assertEqual(first, again)

    def test_policy_declares_dead_pool_filter(self):
        self.assertEqual(PLANNER_POLICY.get("dead_pool_filter"),
                         "2-blockers:live<=dead-bfs")
        legacy = dict(PLANNER_POLICY)
        legacy.pop("dead_pool_filter", None)
        self.assertNotEqual(policy_digest(), policy_digest(legacy))
        altered = dict(PLANNER_POLICY)
        altered["dead_pool_filter"] = "off"
        self.assertNotEqual(policy_digest(), policy_digest(altered))

    def test_invalid_dead_pool_filter_rejected(self):
        with self.assertRaises(ValueError):
            Planner(dead_pool_filter="yes")


if __name__ == "__main__":
    unittest.main()
