"""Wiring the modules makes them independent, and then anti-synchronous.

Rung 3's prerequisite was "modules must emit genuinely independent state".
Tested: they can, but only when the modules are actually supplied.

    configuration        distinct per column                    dependent pairs
    defaults             [13,13, 1, 1, 1,13, 6, 8, 2]          22 of 36
    fully wired          [13,13,13,13,12,13, 6, 8, 2]          31 of 36

The wired counters advance with the step, so more columns vary while *more*
pairs are dependent (22 -> 31). The five pairs that are not dependent are:

    cols(4,5) syn -0.1243  p_upper 0.860  not distinguishable
    cols(4,7) syn -0.2309  p_upper 0.975  distinguishable
    cols(4,8) syn -0.1243  p_upper 1.000  distinguishable
    cols(6,7) syn -0.0632  p_upper 0.915  not distinguishable
    cols(6,8) syn -0.0632  p_upper 1.000  distinguishable

Every one is **negative**, and three are significantly below their null: the
joint carries *less* than its marginals. `interactions` returns nothing on
either configuration. So the honest rung-3 answer is not "no data" — it is
"independent modules exist and they are anti-synchronous", which is itself a
measurement of the substrate.
"""

import json
import os
import tempfile
import unittest

from agent import Agent
from evals.pair_scan import (_dependent, anti_interactions, interactions,
                             pair_report)
from evals.recompute import _vec_row
from memory.store import MemoryStore
from planner.plan import Planner as TrackerPlanner
from self_model.model import SelfModel as PersistentSelfModel


def _vectors(full_wiring):
    with tempfile.TemporaryDirectory() as d:
        log = os.path.join(d, "run.jsonl")
        if not full_wiring:
            Agent().run_task_logged("T3_navigate", 15, max_steps=200,
                                    log_path=log)
        else:
            store = MemoryStore(os.path.join(d, "m.db"))
            try:
                Agent(
                    memory_store=store,
                    planner_tracker=TrackerPlanner(
                        [("s%d" % i, "op%d" % i) for i in range(30)]),
                    self_model=PersistentSelfModel(),
                ).run_task_logged("T3_navigate", 15, max_steps=200,
                                  log_path=log)
            finally:
                store.close()
        with open(log, encoding="utf-8") as handle:
            vec = [r for r in (_vec_row(json.loads(line))
                               for line in handle) if r]
    width = max(len(r) for r in vec)
    padded = [r + [0.0] * (width - len(r)) for r in vec]
    return padded, [r[-1] for r in padded]


class TestWiringIndependence(unittest.TestCase):
    def test_the_defaults_leave_columns_constant(self):
        padded, _ = _vectors(False)
        width = len(padded[0])
        cols = [[r[j] for r in padded] for j in range(width)]
        self.assertEqual(len(set(cols[2])), 1)
        self.assertEqual(len(set(cols[3])), 1)

    def test_wiring_makes_every_column_vary(self):
        padded, _ = _vectors(True)
        cols = [[r[j] for r in padded] for j in range(len(padded[0]))]
        self.assertTrue(all(len(set(c)) > 1 for c in cols),
                        [len(set(c)) for c in cols])

    def test_wiring_does_not_reduce_dependence(self):
        # More distinct values, same collinearity: dependence rises, it does
        # not fall. This is the counter-intuitive result worth pinning.
        def count(padded):
            width = len(padded[0])
            cols = [[r[j] for r in padded] for j in range(width)]
            return sum(1 for i in range(width) for j in range(i + 1, width)
                       if _dependent(cols[i], cols[j]))

        self.assertGreater(count(_vectors(True)[0]),
                           count(_vectors(False)[0]))

    def test_wiring_produces_independent_pairs(self):
        padded, _ = _vectors(True)
        width = len(padded[0])
        cols = [[r[j] for r in padded] for j in range(width)]
        independent = [(i, j) for i in range(width) for j in range(i + 1, width)
                       if not _dependent(cols[i], cols[j])]
        self.assertEqual(independent, [(4, 5), (4, 7), (4, 8), (6, 7), (6, 8)])

    def test_every_independent_pair_is_anti_synchronous(self):
        padded, target = _vectors(True)
        for first, second in ((4, 5), (4, 7), (4, 8), (6, 7), (6, 8)):
            report = pair_report(padded, target, first, second, trials=200)
            self.assertTrue(report["ok"])
            self.assertLess(report["syn"], 0.0,
                            "cols(%d,%d)" % (first, second))

    def test_the_strong_anti_correlations_are_distinguishable(self):
        padded, target = _vectors(True)
        strong = {(4, 7), (4, 8), (6, 8)}
        for first, second in strong:
            report = pair_report(padded, target, first, second, trials=200)
            self.assertTrue(report["null"]["distinguishable"],
                            "cols(%d,%d)" % (first, second))
            self.assertGreater(report["null"]["p_upper"], 0.9)

    def test_no_interaction_under_either_configuration(self):
        for wired in (False, True):
            padded, target = _vectors(wired)
            self.assertEqual(interactions(padded, target, trials=150), [],
                             "wired=%s" % wired)

    def test_anti_interactions_are_reported_separately(self):
        # Five independent pairs exist; three are distinguishable below the
        # null and are the ones anti_interactions returns.
        padded, target = _vectors(True)
        anti = anti_interactions(padded, target, trials=150)
        self.assertEqual(len(anti), 3)
        self.assertTrue(all(r["syn"] < 0.0 for r in anti))
        self.assertEqual({tuple(r["columns"]) for r in anti},
                         {(4, 7), (4, 8), (6, 8)})


if __name__ == "__main__":
    unittest.main()
