"""A pair search must refuse artifacts before it reports a gap.

Scanning all column pairs with `synergy` alone finds confident positives
that are artifacts of a constant partner column plus re-binning:

    T1_forage:71
      cols(1,2) syn +0.2599  p_upper 0.000
      cols(1,3) syn +0.2599  p_upper 0.000
      cols(1,4) syn +0.2599  p_upper 0.000

All three are identical because column 2 is constant (`[0.0]`), so
`i2 == 0` and the joint is a relabelling of column 1: `ij` rises 0.222647 ->
0.482578 purely from `bins=64` re-binning a 16-code joint. A permutation
null does **not** catch this — the artifact survives it, which is why the
gate has to be structural.

These tests pin the gate, the artifact it rejects, and the honest answer
(`interactions` returns nothing when no pair both varies and beats its null).
"""

import json
import os
import tempfile
import unittest

from agent import Agent
from evals.pair_scan import (anti_interactions, interactions, pair_report,
                             scan_pairs)
from evals.recompute import _vec_row
from evals.estimators import mutual_info_discrete


def _shipped(task, seed):
    with tempfile.TemporaryDirectory() as d:
        log = os.path.join(d, "run.jsonl")
        Agent().run_task_logged(task, seed, max_steps=200, log_path=log)
        with open(log, encoding="utf-8") as handle:
            vec = [r for r in (_vec_row(json.loads(line))
                               for line in handle) if r]
    width = max(len(r) for r in vec)
    padded = [r + [0.0] * (width - len(r)) for r in vec]
    return padded, [r[-1] for r in padded]


class TestPairScan(unittest.TestCase):
    def test_a_constant_partner_is_refused(self):
        rows, target = _shipped("T1_forage", 71)
        # Column 2 is constant on this trace.
        report = pair_report(rows, target, 1, 2, trials=50)
        self.assertFalse(report["ok"])
        self.assertEqual(report["reason"], "constant-scope-column")
        self.assertNotIn("null", report)

    def test_the_artifact_has_a_large_gap_and_no_mi(self):
        # The trap: a big syn that carries no second signal at all.
        rows, target = _shipped("T1_forage", 71)
        col1 = [r[1] for r in rows]
        col2 = [r[2] for r in rows]
        self.assertEqual(len(set(col2)), 1)
        self.assertGreater(mutual_info_discrete(col1, target), 0.2)
        self.assertEqual(mutual_info_discrete(col2, target), 0.0)
        report = pair_report(rows, target, 1, 2, trials=50)
        self.assertGreater(report["syn"], 0.2)

    def test_identical_partners_give_identical_gaps(self):
        # cols(1,2), (1,3), (1,4) all pair col1 with a constant, so all three
        # gaps are the same number — the signature of the artifact.
        rows, target = _shipped("T1_forage", 71)
        gaps = [pair_report(rows, target, 1, other, trials=25)["syn"]
                for other in (2, 3, 4)]
        self.assertEqual(len(set(gaps)), 1, gaps)

    def test_the_scan_sorts_refused_pairs_last(self):
        rows, target = _shipped("T1_forage", 71)
        reports = scan_pairs(rows, target, trials=25)
        ok_flags = [r["ok"] for r in reports]
        # Once a refused pair appears, none may follow it.
        first_refused = (ok_flags.index(False) if False in ok_flags
                         else len(ok_flags))
        self.assertTrue(all(flag is False
                            for flag in ok_flags[first_refused:]))

    def test_no_shipped_pair_is_a_positive_interaction(self):
        # The honest answer for the shipped substrate: nothing interacts
        # upward. A pair distinguishable only below its null is an
        # anti-interaction and is reported separately.
        for task, seed in (("T3_navigate", 15), ("T1_forage", 71),
                           ("T2_delayed_match", 3)):
            rows, target = _shipped(task, seed)
            self.assertEqual(interactions(rows, target, trials=100), [],
                             "%s:%d" % (task, seed))

    def test_anti_interactions_are_never_counted_as_interactions(self):
        rows, target = _shipped("T3_navigate", 15)
        anti = anti_interactions(rows, target, trials=100)
        positives = [r for r in anti if r["syn"] > 0.0]
        self.assertEqual(positives, [])
        for report in anti:
            self.assertLess(report["syn"], 0.0)

    def test_functionally_dependent_columns_are_refused(self):
        # col6 is a coarsening of col0: (0,6) is one variable counted twice.
        rows, target = _shipped("T3_navigate", 15)
        report = pair_report(rows, target, 0, 6, trials=50)
        self.assertFalse(report["ok"])
        self.assertEqual(report["reason"], "dependent-columns")
        self.assertNotIn("null", report)

    def test_an_empty_trace_degrades(self):
        self.assertEqual(scan_pairs([], []), [])
        self.assertEqual(interactions([], []), [])


if __name__ == "__main__":
    unittest.main()
