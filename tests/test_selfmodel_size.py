"""Self-model history size must be readable without copying the history.

``Agent._step_vectors`` builds the S vector once per step. With the default
``Agent()`` (no persistent self-model) it takes the ``self.selfmodel`` path
and calls ``len(self.selfmodel.history())``. ``SelfModel.history`` returns
``copy.deepcopy(self._history)``, so the loop deep-copies the entire
episode history once per step merely to measure the array length: O(n) work
inside an O(n) loop for an O(1) answer.

These tests pin the size readout as O(1) and unchanged, plus the fact that
the default Agent path still uses it.
"""

import copy
import time
import unittest

from agent import Agent, SelfModel


def _state(i=0):
    return {"x": i % 8, "y": (i * 3) % 8, "energy": 200 - i, "items": 0,
            "steps": i, "task": "T1_forage",
            "items_positions": [[1, 2], [3, 4], [5, 6]],
            "visits": {"0:0": i, "1:1": i + 1}}


class TestSelfModelSize(unittest.TestCase):
    def test_size_matches_history_length(self):
        sm = SelfModel()
        self.assertEqual(sm.size(), 0)
        for i in range(5):
            sm.record(_state(i), "wait", 0.0, False)
        self.assertEqual(sm.size(), 5)
        self.assertEqual(sm.size(), len(sm.history()))

    def test_size_does_not_copy_the_history(self):
        sm = SelfModel()
        for i in range(50):
            sm.record(_state(i), "wait", 0.0, False)

        copies = {"n": 0}
        real = copy.deepcopy

        def counting(value, *a, **kw):
            copies["n"] += 1
            return real(value, *a, **kw)

        import agent as agent_module
        original = agent_module.copy.deepcopy
        agent_module.copy.deepcopy = counting
        try:
            sm.size()
        finally:
            agent_module.copy.deepcopy = original
        self.assertEqual(copies["n"], 0,
                         "size() deep-copied %d times" % copies["n"])

    def test_size_is_constant_time_relative_to_history(self):
        def bench(n, reps=60):
            sm = SelfModel()
            for i in range(n):
                sm.record(_state(i), "wait", 0.0, False)
            start = time.perf_counter()
            for _ in range(reps):
                sm.size()
            return time.perf_counter() - start

        def bench_history(n, reps=60):
            sm = SelfModel()
            for i in range(n):
                sm.record(_state(i), "wait", 0.0, False)
            start = time.perf_counter()
            for _ in range(reps):
                len(sm.history())
            return time.perf_counter() - start

        fast = bench(200)
        slow = bench_history(200)
        self.assertGreater(slow, fast * 3,
                           "size %.6f vs len(history()) %.6f" % (fast, slow))

    def test_default_agent_uses_the_cheap_path(self):
        agent = Agent()
        self.assertIsNone(agent.self_model)
        calls = {"history": 0, "size": 0}
        real_history = agent.selfmodel.history
        real_size = agent.selfmodel.size

        def counting_history():
            calls["history"] += 1
            return real_history()

        def counting_size():
            calls["size"] += 1
            return real_size()

        agent.selfmodel.history = counting_history
        agent.selfmodel.size = counting_size
        trace = agent.run_task("T3_navigate", 15)
        self.assertEqual(len(trace), 13)
        self.assertEqual(calls["history"], 0,
                         "the loop deep-copied history %d times" % calls["history"])
        self.assertEqual(calls["size"], len(trace))

    def test_actions_and_rewards_unchanged(self):
        cases = (("T1_forage", 71, 16, 3.0),
                 ("T2_delayed_match", 3, 8, 1.0),
                 ("T3_navigate", 15, 13, 1.0),
                 ("T3_navigate", 65, 6, 1.0))
        for task, seed, steps, reward in cases:
            trace = Agent().run_task(task, seed)
            self.assertEqual(len(trace), steps, "%s:%d" % (task, seed))
            self.assertEqual(sum(r["reward"] for r in trace), reward,
                             "%s:%d" % (task, seed))


if __name__ == "__main__":
    unittest.main()
