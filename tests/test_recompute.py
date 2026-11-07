"""Recompute check: log written via telemetry recomputes to direct estimates."""
import random
import tempfile
import unittest
from pathlib import Path

from evals.estimators import gbi, phi_ar, recovery, synergy, transfer_gain
from evals.recompute import recompute
from telemetry.log import Telemetry


def _xor_trace(seed=7, n=120):
    rng = random.Random(seed)
    trace, target = [], []
    for _ in range(n):
        a, b = rng.randint(0, 1), rng.randint(0, 1)
        trace.append([float(a), float(b)])
        target.append(float(a ^ b))
    return trace, target


class TestRecompute(unittest.TestCase):
    def test_recompute_matches_direct(self):
        trace, target = _xor_trace()
        with tempfile.TemporaryDirectory() as td:
            log = str(Path(td) / "eval.jsonl")
            tel = Telemetry(log)
            tel.write_header("T1_forage", 200)
            tel.append_action(1, "eval_samples", {"trace": trace, "target": target})
            tel.append_action(2, "eval_decodability",
                               {"pre": 0.25, "post": 0.75, "reported_gbi": 999.0})
            tel.append_action(3, "eval_transfer",
                               {"naive_steps": 100.0, "reuse_steps": 60.0, "gain": -1.0})
            tel.append_action(4, "eval_recovery",
                               {"time_outside": 1.0, "window": 4.0, "recovery": 0.0})
            tel.append_result(1, True, "ok", 1.0, M=[1.0], P=[0.0], S=[0.0], hub=[0.5])
            tel.write_verdict("UNKNOWN", "no claim drafted")
            got = recompute(log)
        self.assertEqual(got["n_records"], 7)
        syn, _ = synergy(trace, target)
        self.assertAlmostEqual(got["syn"], syn)
        self.assertAlmostEqual(got["phi"], phi_ar(trace))
        self.assertAlmostEqual(got["gbi"], gbi(0.25, 0.75))
        self.assertAlmostEqual(got["gain"], transfer_gain(100.0, 60.0))
        self.assertAlmostEqual(got["recovery"], recovery(1.0, 4.0))

    def test_self_report_scalars_ignored(self):
        with tempfile.TemporaryDirectory() as td:
            log = str(Path(td) / "eval.jsonl")
            tel = Telemetry(log)
            tel.write_header("T2_delayed_match", 200)
            tel.append_action(1, "run", {"syn": 123.0, "phi": 456.0, "gbi": 7.0})
            got = recompute(log)
        self.assertAlmostEqual(got["syn"], 0.0)
        self.assertAlmostEqual(got["gbi"], 0.0)
        self.assertAlmostEqual(got["gain"], 0.0)


if __name__ == "__main__":
    unittest.main()
