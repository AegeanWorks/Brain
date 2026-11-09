"""Every battery's trace slot must carry the synergy scope.

Cycle 103 added ``syn_scope`` to ``recompute`` so a reported ``syn`` of 0.0
could not be read as "no integration" when the estimator was blind. The
snapshot record picked it up; ``evals.coldstart._trace_slot`` — which six
batteries use — still emitted only ``syn``/``syn_n``/``phi``/``gain``/
``recovery``/``n_records``.

Measured: ``_trace_slot({"syn": 0.1, ..., "syn_scope": {...}})`` dropped the
scope entirely, so the cold-start, dead-pool, escape, trust and
manifest-binding batteries all printed a bare ``syn`` with no sufficiency
qualifier.

The slot now carries ``syn_scope`` (``None`` when the caller supplied none),
so every battery that reports a trace reports what the number measured.
"""

import unittest

from evals.coldstart import _trace_slot


BASE = {"syn": 0.1, "syn_n": 0.2, "phi": 0.0, "gain": 0.5,
        "recovery": 1.0, "n_records": 10}


class TestTraceSlotScope(unittest.TestCase):
    def test_slot_carries_the_scope(self):
        scope = {"columns": [0, 1], "sufficient": True, "reason": None}
        slot = _trace_slot(dict(BASE, syn_scope=scope))
        self.assertIn("syn_scope", slot)
        self.assertEqual(slot["syn_scope"], scope)

    def test_slot_keeps_every_existing_field(self):
        slot = _trace_slot(dict(BASE, syn_scope=None))
        for key in ("syn", "syn_n", "phi", "gain", "recovery", "n_records"):
            self.assertIn(key, slot)
            self.assertEqual(slot[key], BASE[key])

    def test_missing_scope_is_none_not_absent(self):
        slot = _trace_slot(dict(BASE))
        self.assertIn("syn_scope", slot)
        self.assertIsNone(slot["syn_scope"])

    def test_a_scope_insufficiency_survives_the_slot(self):
        # The cold-start case reports a bare 0.0; the slot must carry why.
        scope = {"columns": [0, 1], "sufficient": False,
                 "reason": "constant-scope-column", "constant_columns": [0]}
        slot = _trace_slot({"syn": 0.0, "syn_n": 0.0, "phi": 0.0,
                            "gain": 0.0, "recovery": 1.0, "n_records": 13,
                            "syn_scope": scope})
        self.assertEqual(slot["syn"], 0.0)
        self.assertFalse(slot["syn_scope"]["sufficient"])
        self.assertEqual(slot["syn_scope"]["reason"],
                         "constant-scope-column")

    def test_the_coldstart_battery_reports_the_scope(self):
        import tempfile

        from evals.coldstart import measure_case

        with tempfile.TemporaryDirectory() as d:
            case = measure_case("T3_navigate", 15, 13, 1.0, d)
        self.assertIn("syn_scope", case["trace"])
        self.assertFalse(case["trace"]["syn_scope"]["sufficient"],
                         "the cold-start case is blind to columns 2..5")


if __name__ == "__main__":
    unittest.main()
