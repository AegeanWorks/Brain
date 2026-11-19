"""Failing-first harness for scaling the deadline schedule past seven items.

ADR-195 shipped an exact schedule built from ``itertools.permutations``;
it is correct but factorial, and above ``MAX_DEADLINE_ITEMS`` it falls back
to the shortest tour and loses items. This module pins the replacement:

* an exact bitmask dynamic program must agree with brute force up to seven
  items (the standing behaviour stays byte-identical);
* eight through twelve items must be scheduled rather than abandoned;
* the cap moves to twelve and the shortest-tour ablation still loses items.
"""

import itertools
import random
import unittest

from agent import Agent, Planner, _first_of_deadline_tour
from worlds.deadline import DeadlineWorld


def _brute(pos, cells, deadlines, steps=0):
    """Independent reference: enumerate orders with the shipped objective."""
    origin = tuple(pos)
    uniq = sorted({tuple(cell) for cell in cells})
    clock = int(steps)

    def dist(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    best = None
    for order in itertools.permutations(uniq):
        current, time, path = origin, clock, []
        for cell in order:
            arrival = time + dist(current, cell) + 1
            if arrival <= deadlines[cell]:
                time, current = arrival, cell
                path.append(cell)
        if path:
            key = (-len(path), time, tuple(path))
            if best is None or key < best[0]:
                best = (key, path, time)
    return best


def _layout(seed, count):
    rng = random.Random(seed)
    cells = rng.sample([[x, y] for y in range(6) for x in range(6)
                        if [x, y] != [0, 0]], count)
    cells.sort(key=lambda cell: (abs(cell[0]) + abs(cell[1]), cell[0], cell[1]))
    deadlines = {}
    for index, cell in enumerate(cells):
        distance = abs(cell[0]) + abs(cell[1])
        deadlines[tuple(cell)] = distance + (1 if index == count - 1 else 30)
    return cells, deadlines


class TestExactness(unittest.TestCase):
    def test_dp_agrees_with_brute_force_up_to_seven_items(self):
        for count in range(2, 8):
            for seed in range(3):
                cells, deadlines = _layout(seed, count)
                goal, info = _first_of_deadline_tour((0, 0), cells, deadlines)
                best = _brute((0, 0), cells, deadlines)
                self.assertIsNotNone(best, (count, seed))
                _key, path, finish = best
                self.assertEqual(list(goal), list(path[0]), (count, seed))
                self.assertEqual(info["collectible"], len(path), (count, seed))
                self.assertEqual(info["schedule"],
                                 [[c[0], c[1]] for c in path], (count, seed))
                self.assertEqual(info["finish"], finish, (count, seed))


class TestScaledSchedule(unittest.TestCase):
    def test_eight_items_are_scheduled_instead_of_abandoned(self):
        cells = [[x, 0] for x in range(1, 8)] + [[0, 1]]
        deadlines = {(x, 0): 200 for x in range(1, 8)}
        deadlines[(0, 1)] = 200
        goal, info = _first_of_deadline_tour((0, 0), cells, deadlines)
        self.assertIsNotNone(goal)
        self.assertEqual(info["order"], "max-collected-then-shortest")
        self.assertEqual(info["collectible"], 8)
        self.assertEqual(info["total"], 8)

    def test_twelve_items_are_scheduled(self):
        cells = [[x, 0] for x in range(1, 8)] + [[x, 1] for x in range(0, 5)]
        deadlines = {(x, y): 200 for x, y in cells}
        goal, info = _first_of_deadline_tour((0, 0), cells, deadlines)
        self.assertIsNotNone(goal)
        self.assertEqual(info["collectible"], 12)
        self.assertEqual(len(info["schedule"]), 12)

    def test_the_cap_moves_to_twelve(self):
        cells = [[x, 0] for x in range(1, 8)] + [[x, 1] for x in range(0, 6)]
        deadlines = {(x, y): 200 for x, y in cells}
        goal, info = _first_of_deadline_tour((0, 0), cells, deadlines)
        self.assertIsNone(goal)
        self.assertEqual(info["reason"], "item-limit")
        self.assertEqual(info["limit"], 12)

    def test_the_shipped_planner_collects_eight_items(self):
        collected = 0.0
        for seed in range(5):
            world = DeadlineWorld(seed, items=8)
            trace = Agent(planner=Planner(),
                          world=world).run(max_steps=200)
            collected += sum(float(step.get("reward", 0.0)) for step in trace)
        self.assertEqual(collected, 40.0)

    def test_the_tour_ablation_still_loses_items_at_eight(self):
        world = DeadlineWorld(0, items=8)
        trace = Agent(planner=Planner(deadline_ordering=False),
                      world=world).run(max_steps=200)
        self.assertLess(sum(float(step.get("reward", 0.0)) for step in trace), 8.0)


if __name__ == "__main__":
    unittest.main()
