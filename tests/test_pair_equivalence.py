"""Equivalent pairs are one piece of evidence, not two.

P0 and P1 are functionally dependent on the signal rows, so `(2,4)` and
`(3,4)` carry the same joint; likewise `(2,5)` and `(3,5)`. The signed
replication gate selected four negative P-S entries for two unique pieces
of evidence. `column_classes` groups dependent columns, `unique_pairs`
collapses reports that name the same class pair, and `scan_with_holdout`
uses them for `selected`/`rejected` by default. `unique=False` is the
executable ablation and restores the four entries.
"""

import unittest

from agent import Agent
from evals.module_state import signals_from_trace
from evals.pair_scan import column_classes, unique_pairs
from evals.replication import scan_with_holdout


def _rows(seeds):
    rows = []
    for seed in seeds:
        rows.extend(signals_from_trace(
            Agent(module_signals=True).run_task("T3_navigate", seed)))
    return rows, [row[-1] for row in rows]


def _planted(seed, n=64):
    import random
    rng = random.Random(seed)
    rows, target = [], []
    for _ in range(n):
        first = rng.randint(0, 1)
        second = rng.randint(0, 1)
        outcome = first ^ second
        rows.append([first, rng.randint(0, 1), second, rng.randint(0, 1),
                     rng.randint(0, 1), rng.randint(0, 1),
                     rng.randint(0, 1), rng.randint(0, 1), outcome])
        target.append(outcome)
    return rows, target


class TestPairEquivalence(unittest.TestCase):
    def test_dependent_planner_columns_share_a_class(self):
        rows, _ = _rows(range(10))
        classes = column_classes(rows)
        self.assertEqual(len(classes), 6)
        self.assertEqual(classes[2], classes[3])
        self.assertNotEqual(classes[4], classes[5])

    def test_unique_pairs_collapses_equivalent_reports(self):
        reports = [
            {"columns": [2, 5]},
            {"columns": [3, 5]},
            {"columns": [2, 4]},
            {"columns": [3, 4]},
        ]
        classes = [0, 0, 1, 1, 2, 3]
        unique = unique_pairs(reports, classes)
        self.assertEqual([report["columns"] for report in unique],
                         [[2, 5], [2, 4]])

    def test_signed_selection_collapses_to_two_evidence_pairs(self):
        train_rows, train_target = _rows(range(10))
        holdout_rows, holdout_target = _rows(range(10, 20))
        result = scan_with_holdout(train_rows, train_target,
                                   holdout_rows, holdout_target, trials=100,
                                   direction="both")
        selected = [item["candidate"]["columns"]
                    for item in result["selected"]]
        self.assertEqual(len(selected), 2)
        self.assertEqual({tuple(columns) for columns in selected},
                         {(2, 5), (2, 4)})

    def test_the_ablation_restores_the_four_entries(self):
        train_rows, train_target = _rows(range(10))
        holdout_rows, holdout_target = _rows(range(10, 20))
        result = scan_with_holdout(train_rows, train_target,
                                   holdout_rows, holdout_target, trials=100,
                                   direction="both", unique=False)
        selected = [item["candidate"]["columns"]
                    for item in result["selected"]]
        self.assertEqual(len(selected), 4)
        self.assertEqual({tuple(columns) for columns in selected},
                         {(2, 5), (3, 5), (2, 4), (3, 4)})

    def test_a_planted_independent_pair_is_not_collapsed(self):
        train_rows, train_target = _planted(1)
        holdout_rows, holdout_target = _planted(2)
        result = scan_with_holdout(train_rows, train_target,
                                   holdout_rows, holdout_target, trials=100)
        self.assertEqual([item["candidate"]["columns"]
                          for item in result["selected"]], [[0, 2]])


if __name__ == "__main__":
    unittest.main()
