"""Obstacle-trap escape: planner avoids dead-end entries, pinned step totals."""

import unittest

from agent import Agent, Planner as RulePlanner


def _steps(task, seed, max_steps=200):
    agent = Agent()
    trace = agent.run_task(task, seed, max_steps=max_steps)
    return trace


class BlindPlanner(RulePlanner):
    """Integration cut: same rules, memory input severed."""

    def plan(self, state, memories=None):
        return super().plan(state, None)


class TestTrapEscape(unittest.TestCase):
    def test_seed15_takes_optimal_13(self):
        trace = _steps("T3_navigate", 15)
        self.assertGreater(len(trace), 0)
        self.assertTrue(trace[-1]["done"])
        self.assertEqual(sum(r["reward"] for r in trace), 1.0)
        self.assertEqual(len(trace), 13)

    def test_seed65_takes_optimal_6(self):
        trace = _steps("T3_navigate", 65)
        self.assertGreater(len(trace), 0)
        self.assertTrue(trace[-1]["done"])
        self.assertEqual(sum(r["reward"] for r in trace), 1.0)
        self.assertEqual(len(trace), 6)

    def test_ablation_blind_memory_truncates_trap(self):
        # Intact planner (2-ply lookahead + visit counts from memory)
        # completes seed 74 in 9 steps; severing memory leaves
        # lookahead-only routing that cycles until the step cap with zero
        # reward, proving the memory coupling.
        intact = Agent()
        trace = intact.run_task("T3_navigate", 74, max_steps=200)
        self.assertTrue(trace[-1]["done"])
        self.assertEqual(sum(r["reward"] for r in trace), 1.0)
        self.assertEqual(len(trace), 9)
        blind = Agent(planner=BlindPlanner())
        cut = blind.run_task("T3_navigate", 74, max_steps=200)
        self.assertEqual(len(cut), 200)
        self.assertEqual(sum(r["reward"] for r in cut), 0.0)

    def test_pinned_step_totals_no_regression(self):
        totals = {}
        for task in ("T1_forage", "T2_delayed_match", "T3_navigate"):
            total = 0
            for seed in range(30):
                trace = _steps(task, seed)
                self.assertTrue(trace[-1]["done"])
                self.assertGreater(sum(r["reward"] for r in trace), 0.0)
                total += len(trace)
            totals[task] = total
        self.assertEqual(totals["T1_forage"], 466)
        self.assertEqual(totals["T2_delayed_match"], 240)
        self.assertEqual(totals["T3_navigate"], 217)


if __name__ == "__main__":
    unittest.main()
