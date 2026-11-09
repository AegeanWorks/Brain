"""Pin the estimator edge cases their docstrings promise.

``evals/estimators.py`` states conventions per function: degenerate inputs
return a neutral value rather than raising, and clipped statistics stay in
range. The existing suite checks the happy path (correlated MI, XOR
synergy, a non-negative phi); the edge conventions were unverified, so a
refactor could have made one of them raise or return a sentinel without any
test noticing.

Every case here was measured against the shipped code before being pinned.
"""

import unittest

from evals.estimators import (
    gbi,
    logistic_k,
    mutual_info_discrete,
    phi_ar,
    recovery,
    synergy,
    transfer_gain,
)


class TestEstimatorEdges(unittest.TestCase):
    def test_transfer_gain_neutral_on_nonpositive_naive(self):
        self.assertEqual(transfer_gain(0, 10), 0.0)
        self.assertEqual(transfer_gain(-5, 3), 0.0)
        self.assertAlmostEqual(transfer_gain(10, 10), 0.0)

    def test_recovery_is_clipped_to_unit_interval(self):
        self.assertEqual(recovery(9, 4), 0.0)
        self.assertEqual(recovery(-9, 4), 1.0)
        self.assertEqual(recovery(0, 0), 0.0)

    def test_phi_neutral_below_three_rows_and_on_constant_input(self):
        # Exact floor values, which the clip produces and can fail to.
        self.assertEqual(phi_ar([]), 0.0)
        self.assertEqual(phi_ar([[1.0], [2.0]]), 0.0)
        self.assertEqual(phi_ar([[1.0], [1.0], [1.0], [1.0]]), 0.0)

    def test_synergy_neutral_on_empty_or_mismatched_input(self):
        self.assertEqual(synergy([], []), (0.0, 0.0))
        self.assertEqual(synergy([[1.0, 2.0]], []), (0.0, 0.0))
        self.assertEqual(synergy([[1.0, 2.0], [3.0, 4.0]], [1.0]),
                         (0.0, 0.0))

    def test_mutual_information_neutral_without_variation(self):
        self.assertEqual(mutual_info_discrete([], []), 0.0)
        self.assertEqual(mutual_info_discrete([1.0], [1.0]), 0.0)
        self.assertEqual(mutual_info_discrete([1.0, 1.0], [0.0, 1.0]), 0.0)
        self.assertEqual(mutual_info_discrete([0.0, 1.0], [0.0]), 0.0)

    def test_gbi_saturates_at_and_above_one(self):
        self.assertEqual(gbi(0.5, 0.5), 0.0)
        self.assertEqual(gbi(1.0, 1.0), 0.0)
        # pre >= 1 falls back to the raw difference, not a division.
        self.assertEqual(gbi(1.0, 0.5), -0.5)

    def test_logistic_k_neutral_on_empty_or_mismatched_input(self):
        self.assertEqual(logistic_k([], []), (0.0, 0.0))
        self.assertEqual(logistic_k([1.0], [1.0, 0.0]), (0.0, 0.0))

    def test_no_estimator_raises_on_degenerate_input(self):
        # The documented convention is a neutral value, never an exception.
        calls = [
            lambda: transfer_gain(0, 0),
            lambda: recovery(0, 0),
            lambda: phi_ar([]),
            lambda: synergy([], []),
            lambda: mutual_info_discrete([], []),
            lambda: gbi(1.0, 1.0),
            lambda: logistic_k([], []),
        ]
        for call in calls:
            call()


if __name__ == "__main__":
    unittest.main()
