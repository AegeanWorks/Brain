"""A feature that determines the target is not an interaction partner.

The target-column gate catches a column identical to the target. It does not
catch a column that is a deterministic *function* of the target: a leak can
be binned differently in the joint code than in the marginal, so the
``bins=64`` joint / ``bins=8`` marginal mismatch can report a positive gap.

Measured fixture (n=256, seed=1, 16 interleaved leak levels): the leak
column maps every value to one target bit, ``_dependent(leak, noise)`` is
False, and ``pair_report(leak, noise)`` reads ``syn +0.0542`` at per-pair
``p_upper 0.010``; ``interactions`` returns ``[[0, 1]]``. The pair is a
target leak, not a module interaction.

``guard_target=False`` is the executable ablation and restores the leak
pair.
"""

import random
import unittest

from evals.pair_scan import _dependent, interactions, pair_report, scan_pairs


def _leak_fixture(n=256, seed=1, levels=16):
    """A leak column that determines the target, plus independent noise."""
    rng = random.Random(seed)
    rows, target = [], []
    for index in range(n):
        outcome = rng.randint(0, 1)
        leak = (index % levels) / 100.0 + outcome * 0.0005
        noise = rng.randint(0, 1)
        rows.append([leak, noise, outcome])
        target.append(outcome)
    return rows, target


def _planted(n=24, decoys=6, seed=28):
    """The non-leaky XOR pair that the family-wise scan keeps."""
    rng = random.Random(seed)
    rows, target = [], []
    for _ in range(n):
        first = rng.randint(0, 1)
        second = rng.randint(0, 1)
        outcome = first ^ second
        rows.append([first, second]
                    + [rng.randint(0, 1) for _ in range(decoys)]
                    + [outcome])
        target.append(outcome)
    return rows, target


class TestPairScanTargetLeak(unittest.TestCase):
    def test_the_leak_column_is_not_pairwise_dependent_on_noise(self):
        rows, target = _leak_fixture()
        self.assertFalse(_dependent([row[0] for row in rows],
                                    [row[1] for row in rows]))

    def test_the_leak_column_determines_the_target(self):
        rows, target = _leak_fixture()
        mapping = {}
        for row, outcome in zip(rows, target):
            self.assertEqual(mapping.setdefault(row[0], outcome), outcome)

    def test_the_leak_pair_is_returned_without_the_guard(self):
        rows, target = _leak_fixture()
        reports = interactions(rows, target, trials=200, guard_target=False)
        self.assertEqual([report["columns"] for report in reports], [[0, 1]])

    def test_the_leak_pair_is_refused_by_the_guard(self):
        rows, target = _leak_fixture()
        report = pair_report(rows, target, 0, 1, trials=200)
        self.assertFalse(report["ok"])
        self.assertEqual(report["reason"], "target-leak-column")
        self.assertNotIn("null", report)

    def test_the_guarded_scan_returns_no_interaction(self):
        rows, target = _leak_fixture()
        self.assertEqual(interactions(rows, target, trials=200), [])

    def test_a_non_leaky_planted_pair_still_survives(self):
        rows, target = _planted()
        reports = interactions(rows, target, trials=200)
        self.assertEqual([report["columns"] for report in reports], [[0, 1]])

    def test_the_family_is_empty_on_the_leaky_fixture(self):
        rows, target = _leak_fixture()
        reports = scan_pairs(rows, target, trials=80)
        self.assertEqual([report for report in reports if report["ok"]], [])


if __name__ == "__main__":
    unittest.main()
