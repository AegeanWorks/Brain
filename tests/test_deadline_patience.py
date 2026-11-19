"""Failing-first harness for the patience boundary recorded in ADR-197.

The exact schedule wins at every measured item count, but its full sweep
stops at ten items. ADR-197 attributed that to DeadlineWorld's fixed ``+40``
patient-item slack rather than the planner. This module pins the claim by
varying the slack: the default keeps every standing pin, a longer patience
restores the full sweep, and the tour ablation still loses the urgent item.
"""

import unittest

from agent import Agent, Planner
from worlds.deadline import DeadlineWorld


def _reward(trace):
    return sum(float(step.get("reward", 0.0)) for step in trace)


class TestPatienceContract(unittest.TestCase):
    def test_default_deadlines_are_unchanged(self):
        world = DeadlineWorld(0)
        self.assertEqual([(item["cell"], item["deadline"])
                          for item in world.items],
                         [([1, 3], 44), ([1, 6], 47),
                          ([1, 7], 48), ([7, 6], 14)])

    def test_default_patience_keeps_the_twelve_item_result(self):
        trace = Agent(world=DeadlineWorld(0, items=12)).run(max_steps=200)
        self.assertEqual(_reward(trace), 11.0)

    def test_patience_is_validated(self):
        with self.assertRaises(ValueError):
            DeadlineWorld(0, patience=0)
        with self.assertRaises(TypeError):
            DeadlineWorld(0, patience="long")


class TestPatienceBoundary(unittest.TestCase):
    def test_longer_patience_restores_the_full_twelve_item_sweep(self):
        collected = 0.0
        for seed in range(3):
            trace = Agent(world=DeadlineWorld(seed, items=12,
                                              patience=120)).run(max_steps=200)
            collected += _reward(trace)
        self.assertEqual(collected, 36.0)

    def test_the_tour_ablation_still_loses_with_long_patience(self):
        trace = Agent(planner=Planner(deadline_ordering=False),
                      world=DeadlineWorld(0, items=12,
                                          patience=120)).run(max_steps=200)
        self.assertLess(_reward(trace), 12.0)


if __name__ == "__main__":
    unittest.main()
