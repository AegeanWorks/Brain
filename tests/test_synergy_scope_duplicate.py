"""A duplicated scope pair cannot decide, and the scope must say so.

``syn_scope`` marks the scope sufficient when neither of its two columns is
constant. It never checked whether the two columns are *the same column*.
When they are, there is no independent second signal, so the pair cannot
support a claim about interaction.

The arithmetic is not uniform (cycle 142 corrected an earlier overclaim):
``tj = c0 * 8 + bins(c1)`` is injective, but ``mutual_info_discrete(tj, ...,
bins=64)`` re-bins a range of 8..127. Over ``c0 == c1`` on 1..15 the gap is
therefore **+0.054115** (``ij`` 0.50040 > ``i1`` 0.22314) — an artifact of
coarse joint binning, not integration. Over a 4-value column the codes stay
inside the 64 bins and the gap is exactly ``-MI``, with ``syn_n == -1.0``.
Both are pinned in ``test_synergy_duplicate_mechanism.py``.

This is a defect in the cycle-106 disclosure, not in ``synergy`` itself.
"""

import unittest

from evals.estimators import mutual_info_discrete, synergy, synergy_scope


class TestDuplicateScopeColumns(unittest.TestCase):
    def test_a_duplicated_pair_is_not_sufficient(self):
        trace = [[1.0, 1.0], [2.0, 2.0], [3.0, 3.0], [4.0, 4.0]]
        scope = synergy_scope(trace, [0.0, 1.0, 0.0, 1.0])
        self.assertFalse(scope["sufficient"])
        self.assertEqual(scope["reason"], "duplicate-scope-column")
        self.assertEqual(scope["duplicate_columns"], [0, 1])

    def test_a_small_range_duplicate_gives_the_exact_minus_mi_result(self):
        # On a 4-value column the joint codes stay inside the 64 bins, so the
        # pair collapses exactly: syn == -MI and syn_n == -1.0. (A wider
        # column does NOT collapse this way -- see the mechanism tests.)
        trace = [[float(i % 4), float(i % 4)] for i in range(40)]
        target = [float((i * 7) % 2) for i in range(40)]
        syn, syn_n = synergy(trace, target)
        self.assertAlmostEqual(syn, -mutual_info_discrete(
            [row[0] for row in trace], target), places=12)

    def test_syn_n_of_minus_one_marks_the_exact_collapse(self):
        # syn_n == -1.0 exactly when i1 == i2 == ij: the pair carried no
        # information the joint did not already have, twice over.
        trace = [[float(i % 4), float(i % 4)] for i in range(40)]
        target = [float((i * 7) % 2) for i in range(40)]
        _, syn_n = synergy(trace, target)
        self.assertEqual(syn_n, -1.0)
        self.assertFalse(synergy_scope(trace, target)["sufficient"])

    def test_an_independent_pair_stays_sufficient(self):
        trace = [[1.0, 2.0], [1.0, 3.0], [2.0, 2.0], [2.0, 3.0]]
        scope = synergy_scope(trace, [0.0, 1.0, 1.0, 0.0])
        self.assertTrue(scope["sufficient"])
        self.assertEqual(scope["duplicate_columns"], [])

    def test_a_constant_column_is_still_named_first(self):
        trace = [[1.0, 1.0], [1.0, 1.0], [1.0, 1.0]]
        scope = synergy_scope(trace, [0.0, 1.0, 0.0])
        self.assertFalse(scope["sufficient"])
        self.assertEqual(scope["reason"], "constant-scope-column")

    def test_a_single_column_trace_has_no_duplicate(self):
        scope = synergy_scope([[1.0], [2.0], [3.0]], [0.0, 1.0, 0.0])
        # Column 1 does not exist, so it counts as constant, not duplicate.
        self.assertFalse(scope["sufficient"])
        self.assertEqual(scope["reason"], "constant-scope-column")

    def test_empty_and_mismatched_inputs_still_degrade(self):
        self.assertEqual(synergy_scope([], [])["reason"], "empty-trace")
        self.assertEqual(synergy_scope([[1.0, 2.0]], [0.0, 1.0])["reason"],
                         "shape-mismatch")


if __name__ == "__main__":
    unittest.main()
