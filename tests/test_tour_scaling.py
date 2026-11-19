"""Failing-first harness for the factorial shortest-tour helpers.

Cycle 202 capped the exact deadline schedule at twelve items, but the
shortest-tour ablation still enumerated every permutation of the remaining
items. At ten or more items that stalls for minutes. This module pins that
the helpers keep their exact verdicts while scaling polynomially.
"""

import itertools
import random
import time
import unittest

from agent import _first_of_best_tour, _tour_audit


def _tour_length(pos, perm):
    total = abs(perm[0][0] - pos[0]) + abs(perm[0][1] - pos[1])
    for a, b in zip(perm, perm[1:]):
        total += abs(a[0] - b[0]) + abs(a[1] - b[1])
    return total


def _brute_first(pos, cells):
    uniq = sorted({tuple(cell) for cell in cells})
    best, best_len = None, None
    for perm in itertools.permutations(uniq):
        length = _tour_length(pos, perm)
        if best_len is None or length < best_len:
            best_len, best = length, perm
    return list(best[0]), best_len


def _brute_audit(pos, cells):
    uniq = sorted({tuple(cell) for cell in cells})
    first_lengths = {}
    for perm in itertools.permutations(uniq):
        length = _tour_length(pos, perm)
        first = perm[0]
        if first not in first_lengths or length < first_lengths[first]:
            first_lengths[first] = length
    best_len = min(first_lengths.values())
    tied = sorted([list(f) for f, length in first_lengths.items()
                   if length == best_len])
    return first_lengths, best_len, tied


def _layout(seed, count):
    rng = random.Random(seed)
    cells = rng.sample([[x, y] for y in range(5) for x in range(5)
                        if [x, y] != [0, 0]], count)
    return cells


class TestTourExactness(unittest.TestCase):
    def test_first_of_best_tour_matches_brute_force(self):
        for count in range(2, 5):
            for seed in range(3):
                cells = _layout(seed, count)
                goal, length = _brute_first((0, 0), cells)
                self.assertEqual(_first_of_best_tour((0, 0), cells), goal,
                                 (count, seed))

    def test_tour_audit_matches_brute_force(self):
        for count in range(2, 5):
            for seed in range(3):
                cells = _layout(seed, count)
                lengths, best_len, tied = _brute_audit((0, 0), cells)
                report = _tour_audit((0, 0), cells)
                self.assertEqual(report["best_length"], best_len, (count, seed))
                self.assertEqual(report["chosen"], tied[0], (count, seed))
                self.assertEqual(report["tied_firsts"], tied, (count, seed))
                self.assertEqual(report["chosen_length"],
                                 lengths[tuple(tied[0])], (count, seed))
                self.assertEqual(report["tie_count"], len(tied), (count, seed))
                self.assertTrue(report["optimal"])


class TestTourScaling(unittest.TestCase):
    def test_ten_items_do_not_stall(self):
        cells = _layout(0, 10)
        start = time.perf_counter()
        goal = _first_of_best_tour((0, 0), cells)
        audit = _tour_audit((0, 0), cells)
        elapsed = time.perf_counter() - start
        self.assertIsNotNone(goal)
        self.assertEqual(len(audit["items"]), 10)
        # A factorial tour takes minutes even idle; a generous bound keeps
        # the polynomial-vs-factorial guard without flaking under host load.
        self.assertLess(elapsed, 20.0, "%.2fs for 10 items" % elapsed)

    def test_twelve_items_do_not_stall(self):
        cells = [[x, 0] for x in range(1, 8)] + [[x, 1] for x in range(0, 5)]
        start = time.perf_counter()
        goal = _first_of_best_tour((0, 0), cells)
        audit = _tour_audit((0, 0), cells)
        elapsed = time.perf_counter() - start
        self.assertIsNotNone(goal)
        self.assertEqual(len(audit["items"]), 12)
        self.assertLess(elapsed, 30.0, "%.2fs for 12 items" % elapsed)


if __name__ == "__main__":
    unittest.main()
