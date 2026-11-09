"""Every step emits two identical vector rows, so every statistic is over n=2T.

Measured on `T3_navigate:15` (13 steps, 28 log records):

    record types   header 1, action 13, result 13, verdict 1
    vec rows       26  -- both the `action` record and its paired `result`
                   record produce the same 9-column row

    action  [1,1,0,0,0,1,1,0,0]
    result  [1,1,0,0,0,1,1,0,0]   <- identical

So the estimators see each step twice. That doubles n, duplicates every
observation in the contingency tables, and makes `_dependent` trivially true
for any monotone pair (each value appears exactly twice in both columns, in
the same order).

The collinearity itself is real — de-duplicating leaves the dependent-pair
count unchanged (22 defaults, 31 wired) — but the *sample size* every
statistic reports is wrong by a factor of two.
"""

import json
import os
import tempfile
import unittest
from collections import Counter

from agent import Agent
from evals.pair_scan import _dependent
from evals.recompute import _vec_row, dedupe_rows


def _episode(task="T3_navigate", seed=15):
    with tempfile.TemporaryDirectory() as d:
        log = os.path.join(d, "run.jsonl")
        Agent().run_task_logged(task, seed, max_steps=200, log_path=log)
        with open(log, encoding="utf-8") as handle:
            records = [json.loads(line) for line in handle]
    rows = [row for row in (_vec_row(rec) for rec in records) if row]
    return records, rows


def _dependent_count(rows):
    width = max(len(r) for r in rows)
    padded = [r + [0.0] * (width - len(r)) for r in rows]
    cols = [[r[j] for r in padded] for j in range(width)]
    return sum(1 for i in range(width) for j in range(i + 1, width)
               if _dependent(cols[i], cols[j]))


class TestDuplicateVectorRows(unittest.TestCase):
    def test_every_step_emits_two_identical_rows(self):
        records, rows = _episode()
        types = Counter(rec.get("type") for rec in records)
        self.assertEqual(types["action"], types["result"])
        self.assertEqual(len(rows), 2 * types["action"])

    def test_the_pair_is_byte_identical(self):
        _records, rows = _episode()
        for i in range(0, len(rows), 2):
            self.assertEqual(rows[i], rows[i + 1])

    def test_dedupe_halves_the_row_count(self):
        _records, rows = _episode()
        deduped = dedupe_rows(rows)
        self.assertEqual(len(deduped), len(rows) // 2)

    def test_dedupe_changes_no_header_record(self):
        records, rows = _episode()
        self.assertEqual(len(records), len(rows) + 2)  # header + verdict

    def test_the_collinearity_survives_dedupe(self):
        # The point of the fix is the sample size, not the finding.
        _records, rows = _episode()
        self.assertEqual(_dependent_count(dedupe_rows(rows)),
                         _dependent_count(rows))

    def test_dedupe_is_order_preserving(self):
        rows = [[1.0, 2.0], [1.0, 2.0], [3.0, 4.0], [3.0, 4.0], [5.0, 6.0]]
        self.assertEqual(dedupe_rows(rows),
                         [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])

    def test_dedupe_keeps_non_adjacent_repeats(self):
        # Two different steps may legitimately share a vector; only
        # adjacent duplicates are the action/result pair.
        rows = [[1.0], [2.0], [1.0]]
        self.assertEqual(dedupe_rows(rows), [[1.0], [2.0], [1.0]])

    def test_dedupe_degrades_on_empty_input(self):
        self.assertEqual(dedupe_rows([]), [])


if __name__ == "__main__":
    unittest.main()
