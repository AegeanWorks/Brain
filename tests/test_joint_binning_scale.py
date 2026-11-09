"""The joint MI must not be the coarsest of the three scalings.

``synergy`` computes ``ij = mutual_info_discrete(tj, target, bins=64)`` but
``i1``/``i2`` at the default ``bins=8``. ``tj = c0 * 8 + bins(c1)`` therefore
spans ~16x the range of ``c0``, and one ``bins`` value cannot be right for
both: at 8 the joint codes collide, at 64 the marginals are finer than the
joint they are subtracted from.

Measured on the pinned traces (joint codes distinct -> how many survive a
pass at each bin count):

  T1_forage:71    16 codes  bins=8 -> ij 0.222647  syn -0.222647
                            bins=64 -> ij 0.482578  syn +0.037283
  T3_navigate:15  13 codes  bins=8 -> ij 0.164551  syn -0.164551
                            bins=64 -> ij 0.271189  syn -0.057913

The gap changes by up to 0.26 nats, and for T1:71 it changes *sign*: the
same trace is "no synergy" or "positive synergy" depending only on a bin
constant. These tests pin the mechanism and the exact values, so any change
to the scaling is deliberate rather than incidental.
"""

import json
import os
import tempfile
import unittest

from agent import Agent
from evals.estimators import (SYNERGY_COLUMNS, _discretize,
                              mutual_info_discrete, synergy)
from evals.recompute import _vec_row


def _rows(task, seed):
    with tempfile.TemporaryDirectory() as d:
        log = os.path.join(d, "run.jsonl")
        Agent().run_task_logged(task, seed, max_steps=200, log_path=log)
        with open(log, encoding="utf-8") as handle:
            rows = [r for r in (_vec_row(json.loads(line))
                                for line in handle) if r]
    width = max(len(r) for r in rows)
    padded = [r + [0.0] * (width - len(r)) for r in rows]
    return [r[:-1] for r in padded], [r[-1] for r in padded]


def _codes(trace):
    c0 = [r[0] for r in trace]
    c1 = [r[1] for r in trace]
    b1 = _discretize(c1, 8)
    return c0, [c0[i] * 8.0 + float(b1[i]) for i in range(len(c0))]


class TestJointBinningScale(unittest.TestCase):
    def test_the_joint_range_is_eight_times_the_column_range(self):
        trace, _ = _rows("T1_forage", 71)
        c0, tj = _codes(trace)
        self.assertAlmostEqual((max(tj) - min(tj)) / (max(c0) - min(c0)),
                               8.0, delta=0.5)

    def test_a_single_bin_count_cannot_serve_both_scales(self):
        trace, target = _rows("T1_forage", 71)
        _c0, tj = _codes(trace)
        coarse = mutual_info_discrete(tj, target, bins=8)
        fine = mutual_info_discrete(tj, target, bins=64)
        self.assertNotAlmostEqual(coarse, fine, places=6)
        self.assertLess(coarse, fine)

    def test_the_pinned_gap_changes_sign_with_the_bin_count(self):
        # The consequence a reader would care about: same trace, opposite
        # conclusion, from a bin constant alone.
        trace, target = _rows("T1_forage", 71)
        _c0, tj = _codes(trace)
        i1 = mutual_info_discrete([r[0] for r in trace], target)
        i2 = mutual_info_discrete([r[1] for r in trace], target)
        coarse = mutual_info_discrete(tj, target, bins=8) - i1 - i2
        fine = mutual_info_discrete(tj, target, bins=64) - i1 - i2
        self.assertLess(coarse, 0.0)
        self.assertGreater(fine, 0.0)

    def test_the_shipped_value_is_the_fine_one(self):
        trace, target = _rows("T1_forage", 71)
        syn, syn_n = synergy(trace, target)
        self.assertAlmostEqual(syn, 0.0372826, places=6)
        self.assertGreater(syn, 0.0)

    def test_the_scope_columns_are_the_pair_the_joint_uses(self):
        trace, _ = _rows("T1_forage", 71)
        self.assertEqual(list(SYNERGY_COLUMNS), [0, 1])
        self.assertEqual(len(trace[0]), 8)


if __name__ == "__main__":
    unittest.main()
