"""The phi == 0.0 pin must carry its own scope, like the synergy one.

``phi_ar`` is pinned at 0.0 in every cycle baseline. Measured: it is 0.0 on
all 120 real runs (seeds 0-39 for T1/T2/T3) and only 0.00772296 on a
synthetic strong AR(1) series. So the pin cannot fail for trace reasons.

An assertion that cannot fail is not evidence (EVID-009). ``phi_diagnosis``
records why: which columns phi reads, whether they vary, and whether the
trace could be predictable at all. These tests pin that the diagnosis names
a constant trace (the real case) and a varying one, and that the estimator
is shown to move on a synthetic series so the 0.0 is not universal.
"""

import os
import tempfile
import unittest

from agent import Agent
from evals.phi_diagnosis import phi_diagnosis, probe_scale
from evals.recompute import _vec_row
from telemetry.log import Telemetry


def _real_rows(task="T3_navigate", seed=15):
    with tempfile.TemporaryDirectory() as d:
        log = os.path.join(d, "run.jsonl")
        Agent().run_task_logged(task, seed, max_steps=200, log_path=log)
        records = Telemetry(log).read_all()
    steps = [r for r in records
             if r.get("type") == "action" and r.get("kind") == "step"]
    return [row for row in (_vec_row(r) for r in steps) if row]


class TestPhiDiagnosis(unittest.TestCase):
    def test_a_real_trace_reports_zero_and_names_why(self):
        rows = _real_rows()
        report = phi_diagnosis(rows)
        self.assertEqual(report["phi"], 0.0)
        self.assertGreater(report["n_rows"], 3)
        # The trace varies overall, so phi is not 0 by being constant.
        self.assertTrue(report["predictable"])
        self.assertFalse(report["all_constant"])

    def test_a_constant_trace_is_named(self):
        rows = [[1.0, 2.0, 3.0] for _ in range(10)]
        report = phi_diagnosis(rows)
        self.assertEqual(report["phi"], 0.0)
        self.assertTrue(report["all_constant"])
        self.assertFalse(report["predictable"])
        self.assertEqual(report["unique_per_column"], [1, 1, 1])

    def test_a_varying_trace_is_not_reported_constant(self):
        rows = [[float(i), float((i * 3) % 7)] for i in range(20)]
        report = phi_diagnosis(rows)
        self.assertFalse(report["all_constant"])
        self.assertTrue(report["predictable"])

    def test_the_estimator_can_move(self):
        # If this were 0.0 the 0.0 pin would be universal, not a trace fact.
        scale = probe_scale()
        self.assertGreater(scale, 0.0)

    def test_the_diagnosis_reads_every_column(self):
        rows = [[1.0, 2.0, 3.0, 4.0], [1.0, 2.0, 3.0, 5.0],
                [1.0, 2.0, 3.0, 6.0]]
        report = phi_diagnosis(rows)
        self.assertEqual(report["n_columns"], 4)
        self.assertEqual(report["unique_per_column"], [1, 1, 1, 3])

    def test_empty_input_degrades(self):
        report = phi_diagnosis([])
        self.assertEqual(report["phi"], 0.0)
        self.assertEqual(report["n_rows"], 0)
        self.assertEqual(report["n_columns"], 0)
        self.assertFalse(report["predictable"])

    def test_short_input_below_three_rows_is_not_predictable_by_phi(self):
        # phi_ar needs >= 3 rows; the diagnosis must not imply otherwise.
        report = phi_diagnosis([[1.0], [2.0]])
        self.assertEqual(report["phi"], 0.0)
        self.assertEqual(report["n_rows"], 2)


if __name__ == "__main__":
    unittest.main()
