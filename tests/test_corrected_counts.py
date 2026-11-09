"""The corrected distinguishability counts, at one observation per step.

Cycle 144 reported 2 of 6 pinned traces and 3 of 17 battery slots as
distinguishable from their permutation null. Both numbers were computed on
duplicated rows: every step emits an `action` record and a paired `result`
record with the same vector, so n was 2T and each observation entered every
contingency table twice.

With `dedupe_rows` (ADR-144) the correct counts are **0 of 6** and **0 of
17**. Every one of cycle 144's "significant" verdicts was an artifact.

These tests pin the corrected counts, so a future change that re-introduces
duplicated observations fails here rather than silently restoring the
inflated significance.
"""

import json
import os
import tempfile
import unittest

from agent import Agent
from evals.recompute import dedupe_rows, recompute

PINNED = [("T1_forage", 71), ("T2_delayed_match", 3), ("T3_navigate", 15),
          ("T3_navigate", 65), ("T3_navigate", 74), ("T3_navigate", 479)]


class TestCorrectedDistinguishability(unittest.TestCase):
    def test_no_pinned_trace_is_distinguishable(self):
        with tempfile.TemporaryDirectory() as d:
            for task, seed in PINNED:
                log = os.path.join(d, "%s-%d.jsonl" % (task, seed))
                Agent().run_task_logged(task, seed, max_steps=200,
                                        log_path=log)
                stats = recompute(log)
                self.assertFalse(stats["syn_null"]["distinguishable"],
                                 "%s:%d" % (task, seed))

    def test_the_scope_reports_one_row_per_step(self):
        with tempfile.TemporaryDirectory() as d:
            log = os.path.join(d, "run.jsonl")
            trace = Agent().run_task_logged("T3_navigate", 15, max_steps=200,
                                            log_path=log)
            stats = recompute(log)
        self.assertEqual(stats["syn_scope"]["n_rows"], len(trace))

    def test_the_syn_value_is_unchanged_by_dedupe(self):
        # Uniform duplication scales every count equally, so the ratio does
        # not move; only n and the null's spread change.
        with tempfile.TemporaryDirectory() as d:
            log = os.path.join(d, "run.jsonl")
            Agent().run_task_logged("T3_navigate", 15, max_steps=200,
                                    log_path=log)
            stats = recompute(log)
        self.assertAlmostEqual(stats["syn"], -0.05791331748493783, places=12)

    def test_a_degenerate_null_reports_no_spread(self):
        # At n=6 every shuffle of this target gives the identical gap, so
        # the null has zero variance and nothing can be distinguishable.
        with tempfile.TemporaryDirectory() as d:
            log = os.path.join(d, "run.jsonl")
            Agent().run_task_logged("T3_navigate", 65, max_steps=200,
                                    log_path=log)
            stats = recompute(log)
        null = stats["syn_null"]
        self.assertAlmostEqual(null["null_min"], null["null_max"], places=12)
        self.assertFalse(null["distinguishable"])

    def test_dedupe_is_idempotent(self):
        rows = [[1.0], [1.0], [2.0], [2.0]]
        once = dedupe_rows(rows)
        self.assertEqual(dedupe_rows(once), once)


if __name__ == "__main__":
    unittest.main()
