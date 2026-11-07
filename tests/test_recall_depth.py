"""Recall depth: full-history recall for persistent hidden goals.

Failing-first harness: Agent passes last-5 memories to Planner, so a
goal visible only in the initial state falls out of the recall window
after step 5 and persistent-hidden runs truncate even with goal
recall. Full history keeps step 0 reachable.
"""

import unittest

from agent import Agent, Planner
from worlds.grid import GridWorld


class HiddenWorld(GridWorld):
    """GridWorld that omits the target after the initial state."""

    def __init__(self, task_id, seed):
        super().__init__(task_id, seed)
        self._calls = 0

    def _state(self):
        s = super()._state()
        self._calls += 1
        if self._calls > 1:
            s.pop("target", None)
        return s


def _persistent_hidden_steps(task, seed, window=None, max_steps=200):
    world = HiddenWorld(task, seed)
    planner = Planner()
    if window is not None:
        orig = planner.plan

        def _windowed(self, state, memories=None, _o=orig, _w=int(window)):
            mems = list(memories) if memories else []
            return _o(state, mems[-_w:] if _w > 0 else [])

        import types
        planner.plan = types.MethodType(_windowed, planner)
    agent = Agent(planner=planner, world=world)
    return agent.run(max_steps=max_steps)


class TestRecallDepth(unittest.TestCase):
    def test_persistent_hidden_target_recovered(self):
        for seed, want in ((15, 13), (65, 6)):
            trace = _persistent_hidden_steps("T3_navigate", seed)
            self.assertTrue(trace[-1]["done"], "seed %d not done" % seed)
            self.assertEqual(sum(r["reward"] for r in trace), 1.0)
            self.assertEqual(len(trace), want, "seed %d steps" % seed)

    def test_window_ablation_kills_persistent_recovery(self):
        intact = _persistent_hidden_steps("T3_navigate", 15, window=None)
        cut = _persistent_hidden_steps("T3_navigate", 15, window=5)
        self.assertEqual(len(intact), 13)
        self.assertEqual(len(cut), 200)
        self.assertEqual(sum(r["reward"] for r in cut), 0.0)


if __name__ == "__main__":
    unittest.main()
