"""A duplicated scope pair cannot decide, and the scope must say so.

``syn_scope`` marks the scope sufficient when neither of its two columns is
constant. It never checks whether the two columns are *the same column*.
When they are, the joint code ``c0 * 8 + bins(c1)`` is a bijection of one
column, so ``I(joint) == I(c0) == I(c1)`` and the gap is exactly 0.0 — the
same structural collapse as a constant column.

Measured:
  * 500 random traces with ``col0 == col1`` -> 0 strictly positive gaps,
    largest gap exactly 0.0;
  * ``syn_scope([[1,1],[2,2],[3,3]], ...)`` -> ``sufficient True``;
  * the shipped traces have exactly this shape: columns 0, 1 and 5 are all
    the step index (verified byte-identical for six pinned cases), so every
    reported ``syn`` on them is a structural 0.0 the scope does not name.

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

    def test_a_duplicated_pair_cannot_produce_a_positive_gap(self):
        # With c1 == c0 the joint code is a bijection of c0, so i1 == i2 == ij
        # and syn == ij - ij - ij == -ij == -MI. It is never positive.
        trace = [[float(i % 4), float(i % 4)] for i in range(40)]
        target = [float((i * 7) % 2) for i in range(40)]
        syn, syn_n = synergy(trace, target)
        self.assertEqual(syn, -mutual_info_discrete(
            [row[0] for row in trace], target))
        self.assertLessEqual(syn, 0.0)

    def test_syn_n_of_minus_one_is_the_duplicate_signature(self):
        # syn_n == -1.0 exactly when i1 == i2 == ij, which is the duplicate
        # (or constant-collapse) case: the pair could not have shown synergy.
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
