"""Persistent-hidden forage: episode recall goes stale after collects.

Failing-first harness: HiddenT1 omits items_positions after the
initial state, so full-history recall returns the initial 3-cell list
forever. After the first collect the recalled list still contains the
collected cell and the rule loops back, truncating at 200 steps with
1.0 reward vs 16/12/18 optimal with 3.0.
"""

import unittest

from agent import Agent, Planner
from worlds.grid import GridWorld


class HiddenT1(GridWorld):
    def __init__(self, task_id, seed):
        super().__init__(task_id, seed)
        self._calls = 0

    def _state(self):
        s = super()._state()
        self._calls += 1
        if self._calls > 1:
            s.pop("items_positions", None)
        return s


def _hidden_t1_steps(seed, max_steps=200, planner=None):
    world = HiddenT1("T1_forage", seed)
    agent = Agent(planner=planner if planner is not None else Planner(), world=world)
    return agent.run(max_steps=max_steps)


class TestPersistentHiddenForage(unittest.TestCase):
    def test_hidden_forage_recovered(self):
        expected = {71: 16, 74: 12, 78: 18}
        for seed, want in expected.items():
            trace = _hidden_t1_steps(seed)
            self.assertTrue(trace[-1]["done"], "seed %d not done" % seed)
            self.assertEqual(sum(r["reward"] for r in trace), 3.0, "seed %d reward" % seed)
            self.assertEqual(len(trace), want, "seed %d steps" % seed)

    def test_hub_lesion_kills_hidden_forage(self):
        intact = _hidden_t1_steps(71)
        blind_planner = Planner()
        blind_planner.read_hub = lambda: {}
        blind = _hidden_t1_steps(71, planner=blind_planner)
        self.assertEqual(len(intact), 16)
        self.assertEqual(sum(r["reward"] for r in intact), 3.0)
        self.assertEqual(len(blind), 200)
        self.assertEqual(sum(r["reward"] for r in blind), 1.0)

    def test_standing_forage_untouched(self):
        from worlds.grid import GridWorld as GW
        for seed, want in ((71, 16), (74, 12), (78, 18)):
            agent = Agent(planner=Planner(), world=GW("T1_forage", seed))
            trace = agent.run(max_steps=200)
            self.assertEqual(len(trace), want)


if __name__ == "__main__":
    unittest.main()
