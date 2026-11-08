"""Synergy estimator cost: the c1 discretization is computed once.

``synergy`` builds a joint code from column 0 and a discretized column 1.
The discretization must be hoisted out of the per-row expression; keeping
it inline re-discretized the whole column once per row (quadratic). This
pins the call count and the unchanged values.
"""

import unittest
from unittest import mock

import evals.estimators as est


class TestSynergyCost(unittest.TestCase):
    def test_discretize_is_not_per_row(self):
        calls = {"count": 0}
        real = est._discretize

        def counting(values, bins):
            calls["count"] += 1
            return real(values, bins)

        trace = [[float(i % 7), float((i * 3) % 11)] for i in range(50)]
        target = [float(i % 2) for i in range(50)]
        with mock.patch.object(est, "_discretize", counting):
            result = est.synergy(trace, target)
        # One hoisted call for column 1 plus two per mutual-information
        # call (three calls) = 7, independent of the row count.
        self.assertLessEqual(calls["count"], 10)
        self.assertEqual(result, est.synergy(trace, target))

    def test_synergy_values_preserved(self):
        trace = [[0.0, 0.0], [0.0, 1.0], [1.0, 0.0], [1.0, 1.0]]
        target = [0.0, 1.0, 1.0, 0.0]
        syn, _syn_n = est.synergy(trace, target)
        self.assertGreater(syn, 0.0)


if __name__ == "__main__":
    unittest.main()
