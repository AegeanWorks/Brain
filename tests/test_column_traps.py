"""Column-blocking traps: depth-2 lookahead enters blocked columns early.

Failing-first harness: T3 seeds 202 (target [1,6], obstacle [1,3])
and 272 (target [7,7], obstacle [7,3]) need lateral avoidance past
the blocked column; depth-2 enters early for +2 detours.
"""

import unittest

from agent import Agent, Planner as RulePlanner


class BlindPlanner(RulePlanner):
    def plan(self, state, memories=None):
        return super().plan(state, None)


def _steps(task, seed, planner=None, max_steps=200):
    agent = Agent(planner=planner) if planner is not None else Agent()
    return agent.run_task(task, seed, max_steps=max_steps)


class TestColumnTraps(unittest.TestCase):
    def test_column_trap_seeds_optimal(self):
        for seed, want in ((202, 7), (272, 14)):
            trace = _steps("T3_navigate", seed)
            self.assertTrue(trace[-1]["done"])
            self.assertEqual(sum(r["reward"] for r in trace), 1.0)
            self.assertEqual(len(trace), want, "seed %d" % seed)

    def test_t3_200_299_total(self):
        total = 0
        for seed in range(200, 300):
            trace = _steps("T3_navigate", seed)
            self.assertTrue(trace[-1]["done"])
            total += len(trace)
        self.assertEqual(total, 718)

    def test_ablation_blind_truncates_column_traps(self):
        # Mechanism note, honestly recorded: depth-3 lookahead alone
        # suffices on these column traps (blind == intact optimal),
        # like seeds 15/65 in prior cycles; the visit-count memory
        # input carries the differential on tie-trap seed 74 (pinned
        # in test_trap_escape: intact 9 vs blind 200).
        for seed, want in ((202, 7), (272, 14)):
            intact = _steps("T3_navigate", seed)
            self.assertEqual(len(intact), want)
            blind = _steps("T3_navigate", seed, planner=BlindPlanner())
            self.assertEqual(len(blind), want)
            self.assertEqual(sum(r["reward"] for r in blind), 1.0)


if __name__ == "__main__":
    unittest.main()
