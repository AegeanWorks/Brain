"""The target column is not a feature.

``evals.recompute`` builds full block rows with the target in the last
column. ``scan_pairs`` iterated ``range(width)`` and therefore paired the
target column with every other column. Those pairs are not module pairs:
the target's own marginal entropy makes them read anti-synchronous, and
they inflated the "independent pairs" set from three to five on
``T3_navigate:15`` wired.

Measured on that trace: column 8 equals the target; ``pair_report(...,
4, 8)`` reads ``syn -0.1243``; the feature-only independent pairs are
``(4,5)``, ``(4,7)`` and ``(6,7)``.

``guard_target=False`` is the executable ablation and restores the target
pairs.
"""

import json
import os
import tempfile
import unittest

from agent import Agent
from evals.pair_scan import pair_report, scan_pairs
from evals.recompute import _vec_row, dedupe_rows
from memory.store import MemoryStore
from planner.plan import Planner as TrackerPlanner
from self_model.model import SelfModel as PersistentSelfModel


def _wired(task="T3_navigate", seed=15):
    with tempfile.TemporaryDirectory() as directory:
        log = os.path.join(directory, "run.jsonl")
        store = MemoryStore(os.path.join(directory, "m.db"))
        try:
            Agent(
                memory_store=store,
                planner_tracker=TrackerPlanner(
                    [("s%d" % i, "op%d" % i) for i in range(30)]),
                self_model=PersistentSelfModel(),
            ).run_task_logged(task, seed, max_steps=200, log_path=log)
        finally:
            store.close()
        with open(log, encoding="utf-8") as handle:
            rows = dedupe_rows(
                [row for row in (_vec_row(json.loads(line))
                                 for line in handle) if row])
    width = max(len(row) for row in rows)
    padded = [row + [0.0] * (width - len(row)) for row in rows]
    return padded, [row[-1] for row in padded]


class TestPairScanTargetColumn(unittest.TestCase):
    def test_the_last_column_is_the_target(self):
        rows, target = _wired()
        self.assertEqual([row[-1] for row in rows], target)

    def test_scan_pairs_never_returns_the_target_column(self):
        rows, target = _wired()
        last = len(rows[0]) - 1
        reports = scan_pairs(rows, target, trials=60, family_wise=True)
        for report in reports:
            self.assertNotIn(last, report["columns"])

    def test_pair_report_refuses_the_target_column(self):
        rows, target = _wired()
        report = pair_report(rows, target, 4, 8, trials=60)
        self.assertFalse(report["ok"])
        self.assertEqual(report["reason"], "target-column")
        self.assertNotIn("null", report)

    def test_a_feature_pair_still_passes(self):
        rows, target = _wired()
        report = pair_report(rows, target, 4, 7, trials=60)
        self.assertTrue(report["ok"])

    def test_ablation_restores_the_target_pairs(self):
        rows, target = _wired()
        last = len(rows[0]) - 1
        reports = scan_pairs(rows, target, trials=60, family_wise=True,
                             guard_target=False)
        self.assertTrue(any(last in report["columns"] for report in reports))

    def test_the_family_contains_only_feature_pairs(self):
        rows, target = _wired()
        last = len(rows[0]) - 1
        reports = scan_pairs(rows, target, trials=60, family_wise=True)
        valid = [report for report in reports if report["ok"]]
        self.assertTrue(valid)
        for report in valid:
            self.assertNotIn(last, report["columns"])
            self.assertEqual(report["family"]["family_size"], len(valid))


if __name__ == "__main__":
    unittest.main()
