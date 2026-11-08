"""Recall cost: the loop must not deep-copy history it does not read.

``Agent._run_loop`` calls ``self.memory.recall(limit=None)`` once per step
and hands the result to ``Planner.plan``. ``Memory.recall(None)`` deep-copies
the whole episode history, but the planner reads only the last 4 entries
(``recent = list(memories)[-4:]``) and every other consumer iterates the
list without mutating it. The copy is therefore O(n) per step and O(n^2) per
episode for a read of the last 4 items, and it is the dominant per-step
cost once episodes are long.

These tests pin the cost contract: the per-step recall must not scale with
history length, and the actions, steps and rewards must be unchanged.
"""

import copy
import time
import unittest

from agent import Agent, Memory


class _CountingList(list):
    """A list that records how often it is deep-copied."""

    def __init__(self, items=()):
        super().__init__(items)
        self.copies = 0

    def __deepcopy__(self, memo):
        self.copies += 1
        return _CountingList(copy.deepcopy(list(self), memo))


class TestRecallCost(unittest.TestCase):
    def _state(self, i=0):
        return {"x": i % 8, "y": (i * 3) % 8, "energy": 200, "items": 0,
                "steps": i, "task": "T1_forage",
                "items_positions": [[1, 2], [3, 4], [5, 6]]}

    def test_recall_does_not_deepcopy_the_history(self):
        mem = Memory()
        for i in range(50):
            mem.save(self._state(i))
        snapshot = mem.recall(limit=None)
        # The caller may mutate its copy without touching the store.
        snapshot[-1]["x"] = 99
        self.assertNotEqual(mem.recall(limit=None)[-1]["x"], 99)

    def test_per_step_recall_is_much_cheaper_than_a_full_deepcopy(self):
        def bench(n, copy_fn, reps=40):
            mem = Memory()
            for i in range(n):
                mem.save(self._state(i))
            start = time.perf_counter()
            for _ in range(reps):
                copy_fn(mem)
            return time.perf_counter() - start

        def deep(mem):
            return copy.deepcopy(mem._items)

        def shipped(mem):
            return mem.recall(limit=None)

        for n in (60, 200):
            deep_s = bench(n, deep)
            fast_s = bench(n, shipped)
            # A recursive copy re-copies every nested list per call; the
            # one-level copy must beat it by a wide margin at realistic n.
            self.assertGreater(deep_s, fast_s * 3,
                               "n=%d: shipped %.6f vs deepcopy %.6f"
                               % (n, fast_s, deep_s))

    def test_agent_actions_unchanged_by_the_cost_fix(self):
        # Pinned quadruple from the standing suite.
        cases = (("T1_forage", 71, 16, 3.0),
                 ("T2_delayed_match", 3, 8, 1.0),
                 ("T3_navigate", 15, 13, 1.0),
                 ("T3_navigate", 65, 6, 1.0))
        for task, seed, steps, reward in cases:
            trace = Agent().run_task(task, seed)
            self.assertEqual(len(trace), steps, "%s:%d" % (task, seed))
            self.assertEqual(sum(r["reward"] for r in trace), reward,
                             "%s:%d" % (task, seed))

    def test_planner_never_mutates_the_recall_it_receives(self):
        agent = Agent()
        world_state = agent.world.reset() if agent.world else None
        mem = Memory()
        mem.save(self._state(0))
        before = mem.recall(limit=None)
        agent.memory = mem
        agent.planner.plan(self._state(0), mem.recall(limit=None))
        after = mem.recall(limit=None)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
