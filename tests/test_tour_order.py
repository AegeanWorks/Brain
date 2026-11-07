"""Forage tour ordering: optimal 3-item tour beats nearest-greedy traps."""

import unittest

from agent import Agent


def _steps(task, seed, max_steps=200):
    return Agent().run_task(task, seed, max_steps=max_steps)


class TestTourOrder(unittest.TestCase):
    def test_greedy_trap_seeds_optimal(self):
        expected = {71: 16, 74: 12, 78: 18}
        for seed, want in expected.items():
            trace = _steps("T1_forage", seed)
            self.assertTrue(trace[-1]["done"])
            self.assertEqual(sum(r["reward"] for r in trace), 3.0)
            self.assertEqual(len(trace), want)

    def test_t1_100_seed_total(self):
        total = 0
        for seed in range(100):
            trace = _steps("T1_forage", seed)
            self.assertTrue(trace[-1]["done"])
            total += len(trace)
        self.assertEqual(total, 1581)


if __name__ == "__main__":
    unittest.main()
