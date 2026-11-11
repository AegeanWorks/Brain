"""Scanning every pair needs a family-wise null, not per-pair tails.

``synergy_verdict`` is a valid test for one pre-registered pair. ``scan_pairs``
runs it for every pair and ``interactions`` returned every pair outside its
own 5% tail, so a 28-pair scan expects roughly one false positive by
construction. Measured on a synthetic trace with a planted XOR pair and six
independent binary decoys (n=24, seed=28, 200 trials):

  pair (0,1)  planted XOR   syn +0.6337  per-pair p_upper 0.000
  pair (0,6)  decoy noise   syn +0.1368  per-pair p_upper 0.020

The second pair is a family-wise false positive: 28 tests at alpha=0.05.
A max-statistic null (Westfall-Young) compares each observed gap with the
largest gap in each *same* target permutation across every valid pair, so the
correction is paid by the scan, not by an arbitrary Bonferroni divisor.
With it (0,1) survives at p_upper 0.005 and (0,6) is refused at 0.552.

``family_wise=False`` is the executable ablation and restores (0,6).
"""

import os
import random
import tempfile
import unittest

from agent import Agent
from evals.pair_scan import (anti_interactions, interactions, scan_pairs)
from evals.recompute import _vec_row, dedupe_rows


def _planted(n=24, decoys=6, seed=28):
    """One XOR pair plus independent binary decoys; no world, no agent."""
    rng = random.Random(seed)
    rows, target = [], []
    for _ in range(n):
        first = rng.randint(0, 1)
        second = rng.randint(0, 1)
        rows.append([first, second] + [rng.randint(0, 1)
                                       for _ in range(decoys)])
        target.append(first ^ second)
    return rows, target


def _shipped(task, seed):
    with tempfile.TemporaryDirectory() as directory:
        log = os.path.join(directory, "run.jsonl")
        Agent().run_task_logged(task, seed, max_steps=200, log_path=log)
        with open(log, encoding="utf-8") as handle:
            rows = dedupe_rows(
                [row for row in (_vec_row(__import__("json").loads(line))
                                 for line in handle) if row])
    width = max(len(row) for row in rows)
    padded = [row + [0.0] * (width - len(row)) for row in rows]
    return padded, [row[-1] for row in padded]


class TestPairScanFamilyWise(unittest.TestCase):
    def test_uncorrected_scan_flags_a_decoy_pair(self):
        rows, target = _planted()
        reports = interactions(rows, target, trials=200, family_wise=False)
        columns = [report["columns"] for report in reports]
        self.assertIn([0, 1], columns)
        self.assertIn([0, 6], columns)

    def test_corrected_scan_keeps_the_planted_pair(self):
        rows, target = _planted()
        reports = interactions(rows, target, trials=200, family_wise=True)
        self.assertIn([0, 1], [report["columns"] for report in reports])

    def test_corrected_scan_refuses_the_decoy_pair(self):
        rows, target = _planted()
        reports = interactions(rows, target, trials=200, family_wise=True)
        self.assertNotIn([0, 6], [report["columns"] for report in reports])

    def test_correction_reduces_the_selected_set(self):
        rows, target = _planted()
        uncorrected = interactions(rows, target, trials=200,
                                   family_wise=False)
        corrected = interactions(rows, target, trials=200,
                                 family_wise=True)
        self.assertLess(len(corrected), len(uncorrected))

    def test_anti_interactions_use_the_same_correction(self):
        rows, target = _planted()
        uncorrected = anti_interactions(rows, target, trials=200,
                                        family_wise=False)
        corrected = anti_interactions(rows, target, trials=200,
                                      family_wise=True)
        self.assertLessEqual(len(corrected), len(uncorrected))
        for report in corrected:
            self.assertLess(report["syn"], 0.0)

    def test_family_size_is_the_valid_pair_count(self):
        rows, target = _planted()
        reports = scan_pairs(rows, target, trials=80, family_wise=True)
        valid = [report for report in reports if report["ok"]]
        self.assertTrue(valid)
        for report in valid:
            self.assertIn("family", report)
            self.assertEqual(report["family"]["family_size"], len(valid))
            self.assertGreaterEqual(report["family"]["p_upper"],
                                    1.0 / 81.0)
            self.assertLessEqual(report["family"]["p_upper"], 1.0)

    def test_the_correction_is_deterministic(self):
        rows, target = _planted()
        first = scan_pairs(rows, target, trials=120, family_wise=True)
        second = scan_pairs(rows, target, trials=120, family_wise=True)
        self.assertEqual(
            [(r["columns"], r["family"]["p_upper"],
              r["family"]["p_lower"]) for r in first if r["ok"]],
            [(r["columns"], r["family"]["p_upper"],
              r["family"]["p_lower"]) for r in second if r["ok"]])

    def test_no_shipped_pair_survives_the_correction(self):
        for task, seed in (("T3_navigate", 15), ("T1_forage", 71),
                           ("T2_delayed_match", 3)):
            rows, target = _shipped(task, seed)
            self.assertEqual(interactions(rows, target, trials=100,
                                          family_wise=True), [],
                             "%s:%d" % (task, seed))


if __name__ == "__main__":
    unittest.main()
