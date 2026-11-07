"""Multi-obstacle recovery: leaf viability alone truncates with two blockers.

Failing-first harness: single-obstacle exhaustive proof (3906/3906)
does not cover two-obstacle layouts. _ForcedMultiWorld pins five
two-blocker configs where leaf viable-first routing truncates three
times (200/0.0) and detours twice (13 vs 11, 14 vs 12), while standing
totals and the single-obstacle exhaustive battery stay optimal.
"""

import unittest

from agent import Agent, Planner
from worlds.grid import GridWorld


class _ForcedMultiWorld(GridWorld):
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


MULTI_CONFIGS = [
    ((5, 0), [(2, 0), (1, 1)], 9),
    ((7, 5), [(6, 1), (7, 2)], 18),
    ((3, 6), [(2, 2), (3, 2)], 11),
    ((5, 6), [(4, 4), (5, 5)], 13),
    ((5, 7), [(5, 6), (4, 2)], 14),
]


def _multi_steps(target, obstacles, planner=None, max_steps=200):
    world = _ForcedMultiWorld(target, obstacles)
    agent = Agent(planner=planner if planner is not None else Planner(), world=world)
    return agent.run(max_steps=max_steps)


class BlindPlanner(Planner):
    def plan(self, state, memories=None):
        return super().plan(state, None)


class TestMultiObstacle(unittest.TestCase):
    def test_multi_obstacle_recovery(self):
        for target, obstacles, want in MULTI_CONFIGS:
            trace = _multi_steps(target, obstacles)
            self.assertTrue(trace[-1]["done"], "%r %r not done" % (target, obstacles))
            self.assertEqual(sum(r["reward"] for r in trace), 1.0)
            self.assertEqual(len(trace), want, "%r %r steps" % (target, obstacles))

    def test_blind_kills_multi_recovery(self):
        # Visit-coupled killing configs: (5,0) 9/1.0 is pool-sufficient
        # (honest exception, like seeds 15/65) and stays unpinned here.
        for target, obstacles, want in MULTI_CONFIGS[1:]:
            intact = _multi_steps(target, obstacles)
            self.assertEqual(len(intact), want)
            self.assertEqual(sum(r["reward"] for r in intact), 1.0)
            blind = _multi_steps(target, obstacles, planner=BlindPlanner())
            self.assertEqual(len(blind), 200, "%r %r" % (target, obstacles))
            self.assertEqual(sum(r["reward"] for r in blind), 0.0)

    def test_standing_totals_untouched(self):
        totals = {}
        for task in ("T1_forage", "T2_delayed_match", "T3_navigate"):
            total = 0
            for seed in range(30):
                trace = Agent().run_task(task, seed)
                total += len(trace)
            totals[task] = total
        self.assertEqual(totals["T1_forage"], 466)
        self.assertEqual(totals["T2_delayed_match"], 240)
        self.assertEqual(totals["T3_navigate"], 217)


if __name__ == "__main__":
    unittest.main()
