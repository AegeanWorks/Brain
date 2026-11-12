"""Wiring the modules makes them independent, and then anti-synchronous.

Rung 3's prerequisite was "modules must emit genuinely independent state".
Tested: they can, but only when the modules are actually supplied.

    configuration        distinct per column                    dependent pairs
    defaults             [13,13, 1, 1, 1,13, 6, 8, 2]          34 of 36
    fully wired          [13,13,13,13,12,13, 6, 8, 2]          32 of 36

The default constants make every pair containing one of them dependent; wiring
varies those columns and *reduces* dependence (34 -> 32). The two feature pairs
that are not dependent are:

    cols(4,7) syn -0.2309  p_upper 0.890  not distinguishable
    cols(6,7) syn -0.0632  p_upper 0.640  not distinguishable

Every one is **negative**, so the joint carries *less* than its marginals —
but at one observation per step *none* is distinguishable from its null.
The earlier "three significantly below" reading (cycle 148) was computed
on duplicated rows; see cycle 150. `interactions` and
`anti_interactions` both return nothing on either configuration.
"""

import json
import os
import tempfile
import unittest

from agent import Agent
from evals.pair_scan import (_dependent, anti_interactions, interactions,
                             pair_report)
from evals.recompute import _vec_row, dedupe_rows
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
            vec = dedupe_rows(
                [r for r in (_vec_row(json.loads(line))
                             for line in handle) if r])
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

    def test_wiring_reduces_constant_dependence(self):
        # Defaults have constant columns, which are dependent with every
        # other column; wiring varies them and lowers the dependence count.
        def count(padded):
            width = len(padded[0])
            cols = [[r[j] for r in padded] for j in range(width)]
            return sum(1 for i in range(width) for j in range(i + 1, width)
                       if _dependent(cols[i], cols[j]))

        self.assertLess(count(_vectors(True)[0]),
                        count(_vectors(False)[0]))

    def test_wiring_produces_independent_pairs(self):
        padded, _ = _vectors(True)
        width = len(padded[0]) - 1
        cols = [[r[j] for r in padded] for j in range(width)]
        independent = [(i, j) for i in range(width) for j in range(i + 1, width)
                       if not _dependent(cols[i], cols[j])]
        self.assertEqual(independent, [(4, 7), (6, 7)])

    def test_every_independent_pair_is_refused_as_a_target_leak(self):
        padded, target = _vectors(True)
        for first, second in ((4, 7), (6, 7)):
            report = pair_report(padded, target, first, second, trials=200)
            self.assertFalse(report["ok"])
            self.assertEqual(report["reason"], "target-leak-column")
            self.assertLess(report["syn"], 0.0,
                            "cols(%d,%d)" % (first, second))

    def test_every_independent_pair_has_no_single_pair_null(self):
        # A refused pair cannot carry a null; the three gaps are unchanged,
        # but none is a testable anti-correlation at this sample size.
        padded, target = _vectors(True)
        for first, second in ((4, 7), (6, 7)):
            report = pair_report(padded, target, first, second, trials=200)
            self.assertNotIn("null", report,
                             "cols(%d,%d)" % (first, second))

    def test_no_interaction_under_either_configuration(self):
        for wired in (False, True):
            padded, target = _vectors(wired)
            self.assertEqual(interactions(padded, target, trials=150), [],
                             "wired=%s" % wired)

    def test_anti_interactions_are_empty_at_correct_n(self):
        # Every independent pair is negative, but none clears its null, so
        # anti_interactions returns nothing. The negative gaps are real;
        # the significance was not.
        padded, target = _vectors(True)
        self.assertEqual(anti_interactions(padded, target, trials=150), [])


if __name__ == "__main__":
    unittest.main()
