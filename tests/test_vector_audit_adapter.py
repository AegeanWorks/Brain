"""The vector-audit adapter must agree with the row-level audit.

``evals/vector_audit.py`` has two entry points: ``audit_rows`` over flat
9-column rows and ``audit_vectors`` over the ``(M, P, S, hub)`` tuples the
agent actually emits. The tuple adapter had no test, so it was a code path
nothing exercised: a change to the block layout or the flattening order
would have gone unnoticed until someone called it.

These tests pin that the adapter is exactly the row audit of the flattened
blocks, for a degenerate matrix, an independent one, and the empty case.
"""

import unittest

from evals.vector_audit import (
    BLOCK_LABELS,
    audit_rows,
    audit_vectors,
    distinct_columns,
)


def _flat(vectors):
    return [list(m) + list(p) + list(s) + list(h) for m, p, s, h in vectors]


class TestAuditVectors(unittest.TestCase):
    def test_adapter_equals_the_row_audit(self):
        vectors = [
            ((1, 2), (0, 4), (0, 1.0), (5, 7, 3.0)),
            ((2, 0), (1, 3), (0, 1.0), (6, 6, 5.0)),
            ((3, 5), (2, 2), (1, 2.0), (7, 5, 4.0)),
        ]
        self.assertEqual(audit_vectors(vectors), audit_rows(_flat(vectors)))

    def test_adapter_flattens_in_block_order(self):
        vectors = [((1, 2), (3, 4), (5, 6), (7, 8, 9))]
        report = audit_vectors(vectors)
        self.assertEqual(report["n_columns"], len(BLOCK_LABELS))
        self.assertEqual(report["n_rows"], 1)
        # One row makes every column trivially constant.
        self.assertEqual(report["constant"], BLOCK_LABELS)

    def test_block_order_is_observable(self):
        # Only M's first component is constant. A correct flatten reports
        # M0; an S-first flatten would report S0, so this fixture pins the
        # order the adapter is contracted to use.
        vectors = [
            ((9, 1), (2, 3), (4, 5), (6, 7, 8)),
            ((9, 2), (3, 4), (5, 6), (7, 8, 9)),
            ((9, 3), (4, 5), (6, 7), (8, 9, 1)),
        ]
        self.assertEqual(audit_vectors(vectors)["constant"], ["M0"])
        # And the constant it names must be the column that is actually
        # constant in the flattened row.
        flat = _flat(vectors)
        for index, label in enumerate(BLOCK_LABELS):
            values = {row[index] for row in flat}
            if label == "M0":
                self.assertEqual(len(values), 1, label)
            else:
                self.assertGreater(len(values), 1, label)

    def test_a_degenerate_matrix_is_reported_through_the_adapter(self):
        # Every counter advances with the step: the M/P/S blocks collapse.
        vectors = [
            ((1, 1), (1, 1), (1, 1), (0, 0, 0)),
            ((2, 2), (2, 2), (2, 2), (0, 0, 0)),
            ((3, 3), (3, 3), (3, 3), (0, 0, 0)),
        ]
        report = audit_vectors(vectors)
        self.assertEqual(distinct_columns(_flat(vectors)), 1)
        self.assertEqual(report["distinct"], 1)
        self.assertFalse(report["sufficient"])
        self.assertIn(("M0", "M1"), report["duplicates"])

    def test_an_independent_matrix_is_sufficient_through_the_adapter(self):
        vectors = [
            ((1, 2), (0, 4), (0, 1.0), (5, 7, 3.0)),
            ((2, 0), (1, 3), (0, 1.0), (6, 6, 5.0)),
            ((3, 5), (2, 2), (1, 2.0), (7, 5, 4.0)),
        ]
        report = audit_vectors(vectors)
        self.assertTrue(report["sufficient"])
        self.assertEqual(report["duplicates"], [])

    def test_empty_degrades_without_raising(self):
        report = audit_vectors([])
        self.assertEqual(report["n_rows"], 0)
        self.assertEqual(report["n_columns"], 0)
        self.assertFalse(report["sufficient"])
        self.assertEqual(report["duplicates"], [])

    def test_tuples_and_lists_flatten_identically(self):
        as_tuples = [((1, 2), (3, 4), (5, 6), (7, 8, 9)),
                     ((2, 3), (4, 5), (6, 7), (8, 9, 1))]
        as_lists = [[[1, 2], [3, 4], [5, 6], [7, 8, 9]],
                    [[2, 3], [4, 5], [6, 7], [8, 9, 1]]]
        self.assertEqual(audit_vectors(as_tuples), audit_vectors(as_lists))


if __name__ == "__main__":
    unittest.main()
