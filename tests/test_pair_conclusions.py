"""Pair-level conclusions must be re-derived at one observation per step.

Cycle 149 fixed `recompute` to de-duplicate rows, but the pair-level tests
in `test_pair_scan` and `test_wiring_independence` build their rows straight
from `_vec_row` over the log, so they still see `n = 2T`.

Re-measured with and without dedupe:

  T1_forage:71, gate verdicts — UNCHANGED
    cols(1,2)/(1,3)/(1,4)  refused, `constant-scope-column`, syn +0.2599
    cols(0,6)              refused, `dependent-columns`,      syn +0.2062

  T3_navigate:15 fully wired — gaps UNCHANGED, significance NOT
    pair       syn       p_upper @2T   p_upper @T   distinguishable @T
    (4,5)     -0.1243     0.860          0.610      False
    (4,7)     -0.2309     0.975          0.890      False
    (4,8)     -0.1243     1.000          1.000      False
    (6,7)     -0.0632     0.915          0.640      False
    (6,8)     -0.0632     1.000          1.000      False

    anti_interactions: 3 -> 0

The reason the gaps are identical is exact: MI is a function of the joint
probabilities, and uniform duplication is a 2x copy, so `syn` is invariant
(measured: n=8 and n=16 both give -0.6931471805599453). Only n-dependent
quantities — the permutation null's spread and any tail — change. So cycle
147/148's *point estimates* were right and their *significance* was not.
"""

import json
import os
import tempfile
import unittest

from agent import Agent
from evals.pair_scan import (_dependent, anti_interactions, interactions,
                             pair_report)
from evals.recompute import _vec_row, dedupe_rows
from evals.estimators import synergy
from memory.store import MemoryStore
from planner.plan import Planner as TrackerPlanner
from self_model.model import SelfModel as PersistentSelfModel


def _raw(task, seed, wired=False):
    with tempfile.TemporaryDirectory() as d:
        log = os.path.join(d, "run.jsonl")
        if not wired:
            Agent().run_task_logged(task, seed, max_steps=200, log_path=log)
        else:
            store = MemoryStore(os.path.join(d, "m.db"))
            try:
                Agent(
                    memory_store=store,
                    planner_tracker=TrackerPlanner(
                        [("s%d" % i, "op%d" % i) for i in range(30)]),
                    self_model=PersistentSelfModel(),
                ).run_task_logged(task, seed, max_steps=200, log_path=log)
            finally:
                store.close()
        with open(log, encoding="utf-8") as handle:
            return [r for r in (_vec_row(json.loads(line))
                                for line in handle) if r]


def _split(rows):
    width = max(len(r) for r in rows)
    padded = [r + [0.0] * (width - len(r)) for r in rows]
    return padded, [r[-1] for r in padded]


class TestPairConclusionsAtCorrectN(unittest.TestCase):
    def test_uniform_duplication_leaves_syn_unchanged(self):
        rows = [[float(i), float(i % 3)] for i in range(8)]
        target = [float(i % 2) for i in range(8)]
        doubled = [row for row in rows for _ in (0, 1)]
        doubled_target = [t for t in target for _ in (0, 1)]
        self.assertEqual(synergy(rows, target), synergy(doubled, doubled_target))

    def test_the_artifact_gate_verdicts_survive_dedupe(self):
        for rows in (_raw("T1_forage", 71), dedupe_rows(_raw("T1_forage", 71))):
            padded, target = _split(rows)
            for first, second in ((1, 2), (1, 3), (1, 4)):
                report = pair_report(padded, target, first, second, trials=50)
                self.assertEqual(report["reason"], "constant-scope-column")
            report = pair_report(padded, target, 0, 6, trials=50)
            self.assertEqual(report["reason"], "dependent-columns")

    def test_the_independent_pairs_are_the_same_at_correct_n(self):
        rows = dedupe_rows(_raw("T3_navigate", 15, wired=True))
        width = len(rows[0])
        cols = [[r[j] for r in rows] for j in range(width)]
        independent = [(i, j) for i in range(width) for j in range(i + 1, width)
                       if not _dependent(cols[i], cols[j])]
        self.assertEqual(independent, [(4, 5), (4, 7), (4, 8), (6, 7), (6, 8)])

    def test_the_gaps_are_unchanged_by_dedupe(self):
        raw, deduped = _raw("T3_navigate", 15, wired=True), None
        deduped = dedupe_rows(raw)
        p_raw, t_raw = _split(raw)
        p_ded, t_ded = _split(deduped)
        for first, second in ((4, 5), (4, 7), (4, 8), (6, 7), (6, 8)):
            a = pair_report(p_raw, t_raw, first, second, trials=25)["syn"]
            b = pair_report(p_ded, t_ded, first, second, trials=25)["syn"]
            self.assertAlmostEqual(a, b, places=12)

    def test_no_pair_is_distinguishable_at_correct_n(self):
        padded, target = _split(dedupe_rows(_raw("T3_navigate", 15, True)))
        for first, second in ((4, 5), (4, 7), (4, 8), (6, 7), (6, 8)):
            report = pair_report(padded, target, first, second, trials=150)
            self.assertFalse(report["null"]["distinguishable"],
                             "cols(%d,%d)" % (first, second))

    def test_anti_interactions_are_empty_at_correct_n(self):
        padded, target = _split(dedupe_rows(_raw("T3_navigate", 15, True)))
        self.assertEqual(anti_interactions(padded, target, trials=150), [])

    def test_interactions_remain_empty(self):
        for wired in (False, True):
            padded, target = _split(dedupe_rows(_raw("T3_navigate", 15, wired)))
            self.assertEqual(interactions(padded, target, trials=100), [])


if __name__ == "__main__":
    unittest.main()
