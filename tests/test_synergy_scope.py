"""Synergy scope: the criterion must report which trace columns it reads.

``synergy`` builds its joint code from trace columns 0 and 1 only. That is
a real limit, not an implementation detail: with trailing columns present
and column 0 constant, the estimator returns a structural 0.0 even when
other columns carry mutual information with the target. A reported 0.0
therefore cannot distinguish "no integration" from "integration outside
the measured columns", which makes the number unfalsifiable at the point
of reading.

These tests pin the scope as data, so a reader of ``recompute`` output can
see the limit instead of inferring a negative from it. They change no
measured value; ``syn``/``syn_n``/``phi`` stay byte-identical.
"""

import unittest

from evals.estimators import SYNERGY_COLUMNS, synergy, synergy_scope


def _rows(width, n=6):
    return [[float(i), float((i * 2) % 3)] + [0.0] * (width - 2)
            for i in range(n)]


class TestSynergyScope(unittest.TestCase):
    def test_scope_pins_the_two_columns_the_estimator_reads(self):
        self.assertEqual(SYNERGY_COLUMNS, (0, 1))

    def test_scope_names_the_columns_it_ignores(self):
        trace = _rows(8)
        scope = synergy_scope(trace, [0.0, 1.0] * 3)
        self.assertEqual(scope["columns"], [0, 1])
        self.assertEqual(scope["ignored_columns"], [2, 3, 4, 5, 6, 7])
        self.assertEqual(scope["n_rows"], 6)
        self.assertEqual(scope["n_columns"], 8)

    def test_appending_a_column_cannot_change_the_estimate(self):
        trace = _rows(8)
        target = [0.0, 1.0, 1.0, 0.0, 1.0, 0.0]
        two = synergy([row[:2] for row in trace], target)
        eight = synergy(trace, target)
        self.assertEqual(two, eight)
        self.assertEqual(synergy_scope(trace, target)["ignored_columns"],
                         list(range(2, 8)))

    def test_constant_leading_column_is_flagged_insufficient(self):
        # Column 0 constant => the joint code is a bijection of column 1's
        # bins, so syn is structurally 0.0 whatever the other columns say.
        trace = [[5.0, float(i % 4)] + [float(i % 3)] * 6 for i in range(8)]
        target = [1.0, 0.0, 0.0, 1.0, 1.0, 0.0, 0.0, 1.0]
        self.assertEqual(synergy(trace, target), (0.0, 0.0))
        scope = synergy_scope(trace, target)
        self.assertFalse(scope["sufficient"])
        self.assertEqual(scope["reason"], "constant-scope-column")
        self.assertIn(0, scope["constant_columns"])

    def test_sufficient_scope_is_reported_for_a_varying_pair(self):
        trace = _rows(8)
        target = [0.0, 1.0, 1.0, 0.0, 1.0, 0.0]
        scope = synergy_scope(trace, target)
        self.assertTrue(scope["sufficient"])
        self.assertIsNone(scope["reason"])

    def test_empty_trace_degrades_without_raising(self):
        scope = synergy_scope([], [])
        self.assertEqual(scope["n_rows"], 0)
        self.assertEqual(scope["columns"], list(SYNERGY_COLUMNS))
        self.assertFalse(scope["sufficient"])
        self.assertEqual(scope["reason"], "empty-trace")

    def test_recompute_reports_scope_with_the_estimate(self):
        import json
        import os
        import tempfile

        from evals.recompute import recompute
        from telemetry.log import Telemetry

        with tempfile.TemporaryDirectory() as td:
            log = os.path.join(td, "run.jsonl")
            tel = Telemetry(log)
            tel.write_header("T3_navigate", 200)
            for seq in range(1, 7):
                tel.append_action(
                    seq, "step", {}, M=[5.0, float(seq % 4)],
                    P=[0.0, 0.0], S=[0.0, float(seq)],
                    hub=[float(seq), float(seq % 3), 0.0])
            got = recompute(log)
        self.assertEqual(got["syn"], 0.0)
        self.assertEqual(got["syn_scope"]["reason"], "constant-scope-column")
        self.assertEqual(got["syn_scope"]["columns"], [0, 1])
        self.assertIn(6, got["syn_scope"]["ignored_columns"])
        json.dumps(got)  # the scope must stay JSON-serialisable


if __name__ == "__main__":
    unittest.main()
