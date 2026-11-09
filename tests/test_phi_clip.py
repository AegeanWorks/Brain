"""A non-negativity assertion must test the clip, not restate it.

``phi_ar`` ends in ``max(0.0, 1.0 - mse_w / mse_p)``, so its return value is
non-negative by construction. Two shipped tests assert ``phi >= 0.0`` and
nothing else:

  test_estimators.test_phi_nonnegative
  test_estimator_edges.test_phi_neutral_below_three_rows_and_on_constant_input

Measured: across 3000 random trace shapes (1-4 columns, 1-12 rows) the
estimator returned 0 negatives, 1399 zeros and 1601 positives — so the
``>= 0.0`` half cannot fail and is not evidence (EVID-009).

What *can* fail is the value the clip produces at each end: exactly 0.0 for
a degenerate shape, and 1.0 for a shape the single-regressor partition
cannot model at all. These tests pin both ends, so the clip is what is
asserted rather than restated.
"""

import math
import random
import unittest

from evals.estimators import phi_ar


def _sin_cos(rows=120):
    return [[math.sin(i / 5.0), math.cos(i / 5.0)] for i in range(rows)]


def _ar1(rows=61, seed=1):
    rng = random.Random(seed)
    series = [[0.0, 0.0]]
    for _ in range(rows - 1):
        previous = series[-1]
        series.append([0.95 * previous[0] + rng.gauss(0, 0.1),
                       0.90 * previous[1] + rng.gauss(0, 0.2)])
    return series


class TestPhiClipIsWhatIsPinned(unittest.TestCase):
    def test_the_clip_floor_is_exactly_zero(self):
        # Degenerate shapes take the floor, not a small negative float.
        self.assertEqual(phi_ar([]), 0.0)
        self.assertEqual(phi_ar([[1.0], [2.0]]), 0.0)
        self.assertEqual(phi_ar([[1.0], [1.0], [1.0], [1.0]]), 0.0)
        self.assertIsInstance(phi_ar([]), float)

    def test_the_clip_ceiling_is_reached_by_an_unmodellable_partition(self):
        # sin/cos: each column is linear-predictable, but the partitioned
        # single-regressor fit is exhausted, so the ratio saturates at 1.0.
        # This half can fail if the partition or the ratio breaks.
        self.assertEqual(phi_ar(_sin_cos()), 1.0)

    def test_a_partially_predictable_trace_sits_between_the_ends(self):
        value = phi_ar(_ar1())
        self.assertGreater(value, 0.0)
        self.assertLess(value, 1.0)

    def test_the_floor_and_the_signal_are_distinguishable(self):
        self.assertNotEqual(phi_ar([[1.0], [1.0], [1.0]]), phi_ar(_sin_cos()))

    def test_no_shape_returns_a_negative(self):
        # Documents the structural fact: the clip means a negative cannot
        # escape, and the estimator is not clip-only.
        rng = random.Random(0)
        counts = {"negative": 0, "zero": 0, "positive": 0}
        for _ in range(400):
            rows = [[rng.gauss(0, 1) for _ in range(rng.randint(2, 4))]
                    for _ in range(rng.randint(3, 30))]
            value = phi_ar(rows)
            counts["negative" if value < 0.0 else
                   "zero" if value == 0.0 else "positive"] += 1
        self.assertEqual(counts["negative"], 0)
        self.assertEqual(phi_ar(_sin_cos()), 1.0)


if __name__ == "__main__":
    unittest.main()
