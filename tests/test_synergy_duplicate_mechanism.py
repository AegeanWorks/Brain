"""Equal scope columns: state the real mechanism, not the wrong one.

Cycle 141 (ADR-135) claimed a duplicated scope pair gives ``syn == -MI``
exactly, and that the joint code is "a bijection of one column". Verified
false. ``tj = c0 * 8 + bins(c1)``; when ``c0 == c1`` the codes are distinct,
but ``mutual_info_discrete(tj, ..., bins=64)`` re-bins a range of 8..127, so
the joint is *not* a bijection of ``c0`` after discretisation.

Measured on the pinned fixture (``T1_forage:7``, 15 steps, c0 == c1 = 1..15):

    i1  (c0 raw)       = 0.22314355131420976
    ij  (tj, bins=64)  = 0.5004024235381878
    syn                = +0.05411532090976823   (positive!)

and on a 4-value column, ``ij == i1 == i2`` so ``syn == -MI``:

    c0 = i % 4, bins(c1) covers 8..39, all inside the 64 bins -> exact.

So both outcomes occur. What is true in both cases is the one that matters:
the pair carries no *independent* second signal, so any positive gap is an
artifact of coarse joint binning, not evidence of interaction. These tests
pin that reasoning and the two numeric regimes, replacing the false claim.
"""

import unittest

from evals.estimators import _discretize, mutual_info_discrete, synergy


def _fixture_15():
    # The pinned T1_forage:7 shape: c0 == c1 == 1..15, target = task reward.
    c0 = [float(i) for i in range(1, 16)]
    target = [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0,
              0.0, 0.0, 0.0, 0.0, 0.0, 1.0]
    return [[v, v] for v in c0], target


def _fixture_4():
    c0 = [float(i % 4) for i in range(40)]
    target = [float((i * 7) % 2) for i in range(40)]
    return [[v, v] for v in c0], target


class TestEqualColumnsMechanism(unittest.TestCase):
    def test_the_joint_code_is_injective_in_the_column(self):
        trace, _ = _fixture_15()
        c0 = [r[0] for r in trace]
        bins = _discretize(c0, 8)
        codes = [c0[i] * 8.0 + bins[i] for i in range(len(c0))]
        self.assertEqual(len(set(codes)), len(codes))

    def test_coarse_joint_binning_inflates_the_joint(self):
        # The mechanism behind a positive gap: bins=64 over a 8..127 range.
        trace, target = _fixture_15()
        c0 = [r[0] for r in trace]
        bins = _discretize(c0, 8)
        codes = [c0[i] * 8.0 + bins[i] for i in range(len(c0))]
        i1 = mutual_info_discrete(c0, target)
        ij = mutual_info_discrete(codes, target, bins=64)
        self.assertGreater(ij, i1)
        self.assertAlmostEqual(ij, 0.5004024235381878, places=12)

    def test_a_positive_gap_is_an_artifact_not_integration(self):
        trace, target = _fixture_15()
        syn, syn_n = synergy(trace, target)
        self.assertGreater(syn, 0.0)
        self.assertAlmostEqual(syn, 0.05411532090976823, places=12)

    def test_a_small_range_gives_the_exact_minus_mi_result(self):
        trace, target = _fixture_4()
        syn, syn_n = synergy(trace, target)
        self.assertAlmostEqual(syn, -mutual_info_discrete(
            [r[0] for r in trace], target), places=12)
        self.assertEqual(syn_n, -1.0)

    def test_both_regimes_exist_so_the_claim_must_be_about_independence(self):
        a, ta = _fixture_15()
        b, tb = _fixture_4()
        self.assertGreater(synergy(a, ta)[0], 0.0)
        self.assertLess(synergy(b, tb)[0], 0.0)


if __name__ == "__main__":
    unittest.main()
