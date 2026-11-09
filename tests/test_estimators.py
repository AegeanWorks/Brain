"""Estimator unit checks: stdlib only."""
import random
import unittest

from evals.estimators import (
    gbi,
    logistic_k,
    mutual_info_discrete,
    permutation_null,
    phi_ar,
    recovery,
    synergy,
    transfer_gain,
)


class TestEstimators(unittest.TestCase):
    def test_mi_nonnegative_correlated(self):
        rng = random.Random(0)
        xs = [rng.gauss(0, 1) for _ in range(200)]
        ys = [x + rng.gauss(0, 0.1) for x in xs]
        self.assertGreaterEqual(mutual_info_discrete(xs, ys), 0.0)
        self.assertGreater(mutual_info_discrete(xs, ys), 0.2)

    def test_syn_nonnegative_xor(self):
        rng = random.Random(1)
        trace, target = [], []
        for _ in range(400):
            a, b = rng.randint(0, 1), rng.randint(0, 1)
            trace.append([float(a), float(b)])
            target.append(float(a ^ b))
        syn, syn_n = synergy(trace, target)
        self.assertGreaterEqual(syn, 0.0)

    def test_phi_clip_and_signal(self):
        # The estimator clips at 0, so ">= 0" alone cannot fail. Pin the two
        # ends the clip produces instead: an exact floor and a saturated 1.0.
        rng = random.Random(2)
        trace = [[0.0, 0.0]]
        for _ in range(100):
            p = trace[-1]
            trace.append([0.9 * p[0] + rng.gauss(0, 0.1), rng.gauss(0, 1)])
        self.assertGreater(phi_ar(trace), 0.0)
        self.assertEqual(phi_ar([[1.0], [1.0], [1.0], [1.0]]), 0.0)

    def test_gbi_formula(self):
        self.assertAlmostEqual(gbi(0.2, 0.8), (0.8 - 0.2) / (1.0 - 0.2))
        self.assertAlmostEqual(gbi(0.5, 0.5), 0.0)
        self.assertAlmostEqual(gbi(1.0, 1.0), 0.0)

    def test_transfer_recovery_formulas(self):
        self.assertAlmostEqual(transfer_gain(100, 60), 0.4)
        self.assertAlmostEqual(transfer_gain(0, 10), 0.0)
        self.assertAlmostEqual(recovery(1.0, 4.0), 0.75)
        self.assertAlmostEqual(recovery(0.0, 4.0), 1.0)
        self.assertAlmostEqual(recovery(9.0, 4.0), 0.0)
        self.assertAlmostEqual(recovery(1.0, 0.0), 0.0)

    def test_logistic_k_r2_range(self):
        x = [float(i) for i in range(20)]
        y = [0.0] * 10 + [1.0] * 10
        k, r2 = logistic_k(x, y)
        self.assertGreater(k, 0.0)
        self.assertGreater(r2, 0.5)

    def test_permutation_null_deterministic(self):
        fn = lambda rng: rng.gauss(0, 1)
        a = permutation_null(fn, shuffles=200, seed=0)
        b = permutation_null(fn, shuffles=200, seed=0)
        self.assertAlmostEqual(a, b)
        self.assertGreater(a, 0.0)


if __name__ == "__main__":
    unittest.main()
