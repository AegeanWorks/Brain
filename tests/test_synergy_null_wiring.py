"""The synergy null must reach every place ``syn`` is reported.

``recompute`` now returns ``syn_null`` beside ``syn``, but the two other
readouts still drop it unless they are wired:

  evals/coldstart._trace_slot  (six batteries)  -> dropped
  snapshot.run_record          (the diff gate)  -> dropped

Measured before the change: 0 of 17 battery slots carried ``syn_null``, so
every battery printed a gap whose significance was unknown. After: 17 of 17,
and only 3 of the 17 are distinguishable from a permutation null.
"""

import os
import tempfile
import unittest

from evals.coldstart import _trace_slot
from evals.synergy_null import synergy_verdict, permutation_null
from snapshot import run_record

BASE = {"syn": -0.450561, "syn_n": -1.0, "phi": 0.0, "gain": 0.0,
        "recovery": 1.0, "n_records": 12,
        "syn_null": {"observed": -0.450561, "trials": 200,
                     "distinguishable": True, "direction": "negative"}}


class TestSynergyNullWiring(unittest.TestCase):
    def test_trace_slot_carries_the_null(self):
        slot = _trace_slot(dict(BASE))
        self.assertEqual(slot["syn_null"]["trials"], 200)
        self.assertTrue(slot["syn_null"]["distinguishable"])

    def test_trace_slot_defaults_to_none(self):
        slot = _trace_slot({k: v for k, v in BASE.items()
                            if k != "syn_null"})
        self.assertIn("syn_null", slot)
        self.assertIsNone(slot["syn_null"])

    def test_trace_slot_keeps_every_existing_field(self):
        slot = _trace_slot(dict(BASE))
        for key in ("syn", "syn_n", "syn_sign", "syn_scope", "syn_null",
                    "phi", "gain", "recovery", "n_records"):
            self.assertIn(key, slot)

    def test_run_record_carries_the_null(self):
        record = run_record("T3_navigate", 65, [], dict(BASE))
        self.assertEqual(record["syn_null"]["direction"], "negative")

    def test_run_record_defaults_to_none(self):
        record = run_record("T3_navigate", 65, [],
                            {k: v for k, v in BASE.items()
                             if k != "syn_null"})
        self.assertIn("syn_null", record)
        self.assertIsNone(record["syn_null"])

    def test_the_real_run_reaches_the_slot_with_a_verdict(self):
        from agent import Agent
        from evals.recompute import recompute

        with tempfile.TemporaryDirectory() as d:
            log = os.path.join(d, "run.jsonl")
            Agent().run_task_logged("T3_navigate", 65, max_steps=200,
                                    log_path=log)
            stats = recompute(log)
        slot = _trace_slot(stats)
        self.assertEqual(slot["syn_null"]["trials"], 200)
        self.assertEqual(slot["syn_null"]["observed"], stats["syn"])
        self.assertTrue(slot["syn_null"]["distinguishable"])


if __name__ == "__main__":
    unittest.main()
