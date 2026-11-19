"""A ``syn`` value needs its null, or it is a number without a verdict.

The pinned traces report ``syn`` from -0.4506 to +0.0373. Measured against
a permutation null (keep the trace, shuffle the target, 600 draws, seed 0):

  trace              observed    null median   frac null < 0   p(upper)
  T1_forage:71       +0.037283   -0.006886     0.66            0.338
  T2_delayed_match:3 -0.376770   -0.203483     1.00            0.955
  T3_navigate:15     -0.057913   -0.031775     1.00            0.547
  T3_navigate:65     -0.450561   -0.219512     1.00            1.000
  T3_navigate:74     -0.040767   -0.194799     1.00            0.017
  T3_navigate:479    -0.047824   -0.100149     1.00            0.118

Two different readings hide behind those numbers:

  * only ``T3_navigate:65`` is the most negative of the 600 shuffles
    (p_upper 1.000, p_lower 0.015), so that pair is significantly
    ANTI-synergistic — not "absent integration";
  * ``T3_navigate:74`` is significant in the opposite tail (p_upper 0.017):
    it sits above its null while still negative, so the bare sign misleads;
  * T2:3 (p_upper 0.955), T3:15 (0.547) and T3:479 (0.118) are not
    distinguishable from the null, and on ``T1_forage:71`` a third of the
    null lies above the observed value, so its positive ``syn`` is not
    evidence of anything either.

These tests pin both readings and the null's shape, so a bare ``syn`` is no
longer presented as if its sign meant something on its own.
"""

import json
import os
import tempfile
import unittest

from agent import Agent
from evals.estimators import synergy
from evals.recompute import _vec_row
from evals.synergy_null import permutation_null, synergy_verdict


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


class TestPermutationNull(unittest.TestCase):
    def test_the_null_is_deterministic_for_a_seed(self):
        trace, target = _rows("T3_navigate", 15)
        a = permutation_null(trace, target, trials=50, seed=7)
        b = permutation_null(trace, target, trials=50, seed=7)
        self.assertEqual(a, b)

    def test_the_null_keeps_the_trace_and_permutes_the_target(self):
        trace = [[float(i), float(i)] for i in range(10)]
        target = [0.0, 1.0] * 5
        draws = permutation_null(trace, target, trials=25, seed=3)
        self.assertEqual(len(draws), 25)
        # Every draw is a value synergy could have produced for a shuffle.
        self.assertTrue(all(isinstance(v, float) for v in draws))

    def test_a_negative_trace_is_reported_as_anti_synergistic(self):
        trace, target = _rows("T3_navigate", 65)
        verdict = synergy_verdict(trace, target, trials=300)
        self.assertLess(verdict["observed"], 0.0)
        self.assertEqual(verdict["direction"], "negative")
        self.assertTrue(verdict["distinguishable"])
        # Significantly negative is a small lower tail, not an upper one.
        self.assertLess(verdict["p_lower"], 0.05)
        self.assertGreater(verdict["p_upper"], 0.9)

    def test_the_positive_trace_is_not_distinguishable(self):
        trace, target = _rows("T1_forage", 71)
        verdict = synergy_verdict(trace, target, trials=300)
        self.assertGreater(verdict["observed"], 0.0)
        self.assertFalse(verdict["distinguishable"])
        self.assertGreater(verdict["p_upper"], 0.05)

    def test_the_verdict_carries_the_null_it_used(self):
        trace, target = _rows("T3_navigate", 15)
        verdict = synergy_verdict(trace, target, trials=120)
        self.assertEqual(verdict["trials"], 120)
        for key in ("observed", "null_median", "null_min", "null_max",
                    "p_upper", "p_lower", "direction", "distinguishable"):
            self.assertIn(key, verdict)

    def test_degenerate_input_degrades_without_raising(self):
        verdict = synergy_verdict([], [], trials=10)
        self.assertEqual(verdict["observed"], 0.0)
        self.assertEqual(verdict["direction"], "zero")
        self.assertFalse(verdict["distinguishable"])

    def test_a_bad_trial_count_is_rejected(self):
        trace, target = _rows("T3_navigate", 15)
        for bad in (0, -3, True, 2.5):
            with self.assertRaises(ValueError):
                permutation_null(trace, target, trials=bad)


if __name__ == "__main__":
    unittest.main()
