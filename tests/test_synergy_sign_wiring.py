"""The synergy sign must reach every place ``syn`` is reported.

Cycle 136 added ``syn_sign`` to ``recompute`` so a ``syn_n`` of ``-1.0``
cannot be read as the strongest positive interaction. Two other readouts
still carry a bare ``syn``:

  evals/coldstart._trace_slot  (six batteries)  -> no syn_sign
  snapshot.run_record          (the diff gate)  -> no syn_sign

Measured before the change: both dropped the field, so a battery printing
``syn -0.450561 syn_n -1.000000`` gave the reader no direction. These tests
pin the field in both, ``None`` when the caller supplied no sign, so the
report is unchanged where the value is unchanged.
"""

import os
import tempfile
import unittest

from evals.coldstart import _trace_slot
from snapshot import run_record

BASE = {"syn": -0.450561, "syn_n": -1.0, "phi": 0.0, "gain": 0.0,
        "recovery": 1.0, "n_records": 16}


class TestSynergySignWiring(unittest.TestCase):
    def test_trace_slot_carries_the_sign(self):
        slot = _trace_slot(dict(BASE, syn_sign="negative"))
        self.assertEqual(slot["syn_sign"], "negative")
        self.assertEqual(slot["syn"], BASE["syn"])

    def test_trace_slot_defaults_to_none(self):
        slot = _trace_slot(dict(BASE))
        self.assertIn("syn_sign", slot)
        self.assertIsNone(slot["syn_sign"])

    def test_trace_slot_keeps_every_existing_field(self):
        slot = _trace_slot(dict(BASE, syn_sign="negative"))
        for key in ("syn", "syn_n", "phi", "gain", "recovery", "n_records",
                    "syn_scope"):
            self.assertIn(key, slot)

    def test_run_record_carries_the_sign(self):
        record = run_record("T3_navigate", 65, [], dict(BASE,
                                                       syn_sign="negative"))
        self.assertEqual(record["syn_sign"], "negative")
        self.assertEqual(record["syn"], BASE["syn"])

    def test_run_record_defaults_to_none(self):
        record = run_record("T3_navigate", 65, [], dict(BASE))
        self.assertIn("syn_sign", record)
        self.assertIsNone(record["syn_sign"])

    def test_the_real_negative_case_reaches_the_slot(self):
        # T3:65 is one of the two pinned cases at syn_n = -1.0.
        from evals.recompute import recompute
        from agent import Agent

        with tempfile.TemporaryDirectory() as d:
            log = os.path.join(d, "run.jsonl")
            Agent().run_task_logged("T3_navigate", 65, max_steps=200,
                                    log_path=log)
            stats = recompute(log)
        slot = _trace_slot(stats)
        self.assertEqual(stats["syn_sign"], "negative")
        self.assertEqual(slot["syn_sign"], "negative")
        self.assertAlmostEqual(slot["syn_n"], -1.0)


if __name__ == "__main__":
    unittest.main()
