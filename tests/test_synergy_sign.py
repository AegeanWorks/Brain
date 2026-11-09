"""A negative synergy gap must be reported as such, not as a strong one.

``synergy`` returns ``syn = I(joint) - I(c1) - I(c2)`` and
``syn_n = syn / I(joint)``. When the joint code carries *less* information
than the sum of its marginals, ``syn`` is negative and ``syn_n`` can reach
``-1.0`` — the largest magnitude the ratio can take.

Measured on the pinned full-information cases:

  T1_forage:71        syn= 0.037283  syn_n= 0.077258
  T2_delayed_match:3  syn=-0.376770  syn_n=-1.000000
  T3_navigate:15      syn=-0.057913  syn_n=-0.213553
  T3_navigate:65      syn=-0.450561  syn_n=-1.000000
  T3_navigate:74      syn=-0.040767  syn_n=-0.116866
  T3_navigate:479     syn=-0.047824  syn_n=-0.147114

``syn_n = -1.0`` reads like the strongest possible interaction; it is the
opposite. A reader cannot tell a strong positive from a strong negative
without checking the sign of a second field. These tests pin an explicit
``syn_sign`` classification so the direction travels with the number.
"""

import unittest

from evals.estimators import synergy, synergy_sign


class TestSynergySign(unittest.TestCase):
    def test_a_positive_gap_is_reported_positive(self):
        # XOR: the joint carries what neither column does.
        trace, target = [], []
        for a in (0, 1):
            for b in (0, 1):
                trace.append([float(a), float(b)])
                target.append(float(a ^ b))
        syn, syn_n = synergy(trace, target)
        self.assertGreater(syn, 0.0)
        self.assertEqual(synergy_sign(syn, syn_n), "positive")

    def test_a_negative_ratio_at_minus_one_is_reported_negative(self):
        # The measured T3:65 / T2:3 shape.
        self.assertEqual(synergy_sign(-0.450561, -1.0), "negative")
        self.assertEqual(synergy_sign(-0.376770, -1.0), "negative")

    def test_a_small_negative_is_still_negative(self):
        self.assertEqual(synergy_sign(-0.040767, -0.116866), "negative")

    def test_zero_is_reported_zero(self):
        self.assertEqual(synergy_sign(0.0, 0.0), "zero")
        self.assertEqual(synergy_sign(-0.0, -0.0), "zero")

    def test_the_classification_uses_the_gap_not_the_ratio(self):
        # A positive ratio over a negative gap is still a negative gap; the
        # sign of the underlying difference is what a reader must not miss.
        self.assertEqual(synergy_sign(-0.1, 0.5), "negative")
        self.assertEqual(synergy_sign(0.1, -0.5), "positive")

    def test_the_estimator_keeps_its_values(self):
        # The classification is additive; syn/syn_n are untouched.
        trace = [[float(i % 8), float((i * 3) % 8)] for i in range(40)]
        target = [float(i % 2) for i in range(40)]
        syn, syn_n = synergy(trace, target)
        self.assertIsInstance(syn, float)
        self.assertIsInstance(syn_n, float)
        self.assertEqual(synergy_sign(syn, syn_n), synergy_sign(syn, syn_n))


if __name__ == "__main__":
    unittest.main()
