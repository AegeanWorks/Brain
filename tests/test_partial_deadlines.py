"""Failing-first harness for partial deadline observability.

ADR-195 and ADR-197 record that a world emitting deadlines for only some
items makes the planner abandon scheduling, even when the urgent item's
deadline is known. This module pins that the planner keeps the known
deadlines, treats the rest as patient, and names those assumptions.
"""

import unittest

from agent import Agent, Planner
from worlds.deadline import DeadlineWorld


def _reward(trace):
    return sum(float(step.get("reward", 0.0)) for step in trace)


class TestPartialWorld(unittest.TestCase):
    def test_full_visibility_deadlines_are_unchanged(self):
        world = DeadlineWorld(0)
        self.assertEqual([(item["cell"], item["deadline"])
                          for item in world.items],
                         [([1, 3], 44), ([1, 6], 47),
                          ([1, 7], 48), ([7, 6], 14)])
        self.assertEqual(len(world.reset()["deadlines"]), 4)

    def test_visibility_controls_the_emitted_map(self):
        world = DeadlineWorld(0, items=8, deadline_visibility=0.5)
        state = world.reset()
        self.assertEqual(len(state["deadlines"]), 4)
        self.assertEqual(len(world.items), 8)

    def test_visibility_is_validated(self):
        with self.assertRaises(ValueError):
            DeadlineWorld(0, deadline_visibility=1.5)
        with self.assertRaises(TypeError):
            DeadlineWorld(0, deadline_visibility="half")


class TestPartialScheduling(unittest.TestCase):
    def test_known_urgent_deadline_is_still_scheduled(self):
        collected = 0.0
        for seed in range(3):
            world = DeadlineWorld(seed, items=12, deadline_visibility=0.5)
            trace = Agent(world=world).run(max_steps=200)
            collected += _reward(trace)
        # Partial visibility loses the small full-knowledge edge (11.33 ->
        # 11.00) but never drops below the tour ablation (11.00).
        self.assertEqual(collected, 33.0)
        ablation = 0.0
        for seed in range(3):
            from agent import Planner as _Planner
            trace = Agent(planner=_Planner(deadline_ordering=False),
                          world=DeadlineWorld(seed, items=12,
                                              deadline_visibility=0.5)
                          ).run(max_steps=200)
            ablation += _reward(trace)
        self.assertGreaterEqual(collected, ablation)

    def test_hidden_deadlines_are_named_as_assumed(self):
        world = DeadlineWorld(0, items=8, deadline_visibility=0.5)
        state = world.reset()
        planner = Planner()
        planner.plan(state, [state])
        probe = planner.last_probe["deadline"]
        self.assertIn("assumed", probe)
        self.assertEqual(len(probe["assumed"]), 4)
        self.assertEqual(len(probe["schedule"]), 8)


if __name__ == "__main__":
    unittest.main()
