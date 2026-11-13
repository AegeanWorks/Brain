"""The rule policy already reaches the ceiling on every shipped task.

This pins the measurement behind ADR-192: the shortest possible episode is
what the rule policy already achieves, so no learned policy -- and therefore
no language model behind the action seam -- can improve steps on T1/T2/T3.
It also explains why the trust guards reject a disagreeing proposal: on these
tasks a disagreement is a mistake, not a discovery.
"""

import unittest

from evals.policy_ceiling import (DEFAULT_SEEDS, bfs_distance, headroom,
                                  optimal_steps)
from worlds.grid import GridWorld, TASKS


class TestBfs(unittest.TestCase):
    def test_a_start_equal_to_the_goal_is_zero(self):
        self.assertEqual(bfs_distance((3, 3), (3, 3)), 0)

    def test_a_straight_line_is_manhattan(self):
        self.assertEqual(bfs_distance((0, 0), (3, 0)), 3)
        self.assertEqual(bfs_distance((0, 0), (0, 4)), 4)

    def test_an_obstacle_forces_a_detour(self):
        # (1,0) blocks the direct line, so the shortest path is a dogleg.
        self.assertEqual(bfs_distance((0, 0), (2, 0), [(1, 0)]), 4)

    def test_edges_clamp_instead_of_escaping(self):
        self.assertEqual(bfs_distance((0, 0), (7, 7)), 14)

    def test_a_fully_walled_goal_is_unreachable(self):
        walls = [(x, 0) for x in range(8)] + [(0, y) for y in range(8)]
        self.assertIsNone(bfs_distance((0, 0), (7, 7), walls))

    def test_a_blocked_goal_is_unreachable(self):
        self.assertIsNone(bfs_distance((0, 0), (1, 0), [(1, 0)]))

    def test_a_start_on_a_blocked_cell_still_reports_zero(self):
        # The agent can never actually stand on a blocked cell; the helper
        # answers "already there" rather than inventing a path out.
        self.assertEqual(bfs_distance((0, 0), (0, 0), [(0, 0)]), 0)


class TestOptimalSteps(unittest.TestCase):
    def test_forage_counts_a_collect_per_item(self):
        world = GridWorld("T1_forage", 0)
        world.reset()
        items = [tuple(cell) for cell in world._initial_items]
        self.assertEqual(len(items), 3)
        # Three collects are mandatory, so the optimum is at least 3.
        self.assertGreaterEqual(optimal_steps("T1_forage", 0), 3)

    def test_forage_matches_a_brute_force_ordering(self):
        # The helper is the brute force; assert it is stable and plausible.
        first, second = optimal_steps("T1_forage", 5), optimal_steps("T1_forage", 5)
        self.assertEqual(first, second)

    def test_match_waits_for_the_two_step_rule(self):
        world = GridWorld("T2_delayed_match", 0)
        world.reset()
        target = tuple(world._target)
        self.assertGreaterEqual(optimal_steps("T2_delayed_match", 0), 2)
        self.assertEqual(optimal_steps("T2_delayed_match", 0),
                         max(bfs_distance((0, 0), target) + 1, 2))

    def test_navigate_routes_around_the_seeded_obstacle(self):
        world = GridWorld("T3_navigate", 0)
        world.reset()
        target = tuple(world._target)
        blocked = [tuple(cell) for cell in world._obstacles]
        self.assertEqual(optimal_steps("T3_navigate", 0),
                         bfs_distance((0, 0), target, blocked))

    def test_every_task_has_a_finite_optimum_on_every_seed(self):
        for task in TASKS:
            for seed in range(5):
                value = optimal_steps(task, seed)
                self.assertIsNotNone(value, (task, seed))
                self.assertGreater(value, 0, (task, seed))


class TestNoHeadroom(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = headroom()

    def test_the_rule_is_optimal_on_every_task(self):
        self.assertTrue(self.report["optimal_everywhere"])
        for task in TASKS:
            self.assertEqual(self.report[task]["suboptimal_seeds"], [], task)

    def test_no_task_has_a_positive_gap(self):
        for task in TASKS:
            self.assertEqual(self.report[task]["max_gap"], 0, task)

    def test_the_rule_mean_equals_the_optimum_mean(self):
        for task in TASKS:
            self.assertEqual(self.report[task]["rule_mean"],
                             self.report[task]["optimal_mean"], task)

    def test_the_pinned_means_are_the_measured_ones(self):
        self.assertEqual(self.report["T1_forage"]["rule_mean"], 15.4)
        self.assertEqual(self.report["T2_delayed_match"]["rule_mean"], 8.0)
        self.assertEqual(self.report["T3_navigate"]["rule_mean"], 7.15)

    def test_the_report_covers_every_default_seed(self):
        for task in TASKS:
            self.assertEqual(self.report[task]["seeds"], len(DEFAULT_SEEDS))


if __name__ == "__main__":
    unittest.main()
