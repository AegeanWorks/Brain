"""Three-blocker snapshot matrix: pin the audited two-detour family.

Audit extension of the two-blocker matrix: five three-obstacle configs
verified deterministic 3x identical on the intact tree. All five now
complete with 1.0 reward (four detours, one pool-sufficient); the
former (6,5) truncation is recovered by the repeated-position BFS
escape (cycle 54), which needs full episode memory. The pin locks the
current behavior against silent drift in either direction until a
reviewed routing change updates it.

Regeneration rule (deliberately manual, no auto-update flag): after a
reviewed planner change, re-audit the five configs on the intact tree
and replace THREE_CONFIGS in one reviewed edit. Never update pins to
make a red tree green.
"""

import unittest

from agent import Agent, Planner
from worlds.grid import GridWorld


class _ForcedThreeWorld(GridWorld):
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


THREE_CONFIGS = [
    ((6, 7), [(2, 7), (5, 4), (6, 3)], 15, 1.0),
    ((7, 3), [(5, 2), (7, 0), (6, 1)], 12, 1.0),
    ((6, 0), [(5, 0), (2, 1), (7, 1)], 10, 1.0),
    ((4, 7), [(4, 4), (7, 7), (3, 1)], 13, 1.0),
    ((6, 5), [(6, 4), (5, 5), (3, 5)], 19, 1.0),
]


def _three_steps(target, obstacles, planner=None, max_steps=200):
    world = _ForcedThreeWorld(target, obstacles)
    agent = Agent(planner=planner if planner is not None else Planner(), world=world)
    return agent.run(max_steps=max_steps)


class BlindPlanner(Planner):
    def plan(self, state, memories=None):
        return super().plan(state, None)


class TestThreeBlocker(unittest.TestCase):
    def test_three_blocker_pins(self):
        for target, obstacles, want_steps, want_reward in THREE_CONFIGS:
            trace = _three_steps(target, obstacles)
            self.assertTrue(trace[-1]["done"], "%r %r not done" % (target, obstacles))
            self.assertEqual(sum(r["reward"] for r in trace), want_reward)
            self.assertEqual(len(trace), want_steps, "%r %r" % (target, obstacles))

    def test_blind_kills_three_blocker(self):
        # Visit-coupled killing configs: (6,0) 10/1.0 is pool-sufficient
        # (honest exception) and stays unpinned here. (6,5) is now a
        # killing config too: the intact escape completes in 19 steps
        # while the memory-blind cut still truncates at 200/0.
        for target, obstacles, want in (((6, 7), [(2, 7), (5, 4), (6, 3)], 15),
                                         ((7, 3), [(5, 2), (7, 0), (6, 1)], 12),
                                         ((4, 7), [(4, 4), (7, 7), (3, 1)], 13),
                                         ((6, 5), [(6, 4), (5, 5), (3, 5)], 19)):
            intact = _three_steps(target, obstacles)
            self.assertEqual(len(intact), want)
            self.assertEqual(sum(r["reward"] for r in intact), 1.0)
            blind = _three_steps(target, obstacles, planner=BlindPlanner())
            self.assertEqual(len(blind), 200, "%r %r" % (target, obstacles))
            self.assertEqual(sum(r["reward"] for r in blind), 0.0)


if __name__ == "__main__":
    unittest.main()
