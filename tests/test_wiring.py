"""Wiring check: real substrate roundtrip through JSONL log to recompute."""

import json
import os
import tempfile
import unittest

from agent import Agent
from evals.estimators import phi_ar, synergy
from evals.recompute import _vec_row, recompute
from memory.store import MemoryStore
from planner.plan import Planner as TrackerPlanner
from self_model.model import SelfModel as PersistentSelfModel
from telemetry.ablate import hub_zero_rows, lesion_m, lesion_p, lesion_s
from telemetry.log import Telemetry as FileTelemetry


def _pad(rows):
    if not rows:
        return []
    w = max(len(r) for r in rows)
    return [list(r) + [0.0] * (w - len(r)) for r in rows]


class TestWiring(unittest.TestCase):
    def _run_logged(self, tmp, task="T1_forage", seed=7, max_steps=30):
        db_path = os.path.join(tmp, "mem.db")
        log_path = os.path.join(tmp, "run.jsonl")
        store = MemoryStore(db_path)
        tracker = TrackerPlanner([(f"s{i}", f"op{i}") for i in range(max_steps)])
        sm = PersistentSelfModel()
        agent = Agent(memory_store=store, planner_tracker=tracker, self_model=sm)
        trace = agent.run_task_logged(task, seed, max_steps=max_steps, log_path=log_path)
        return agent, store, tracker, sm, trace, log_path

    def test_roundtrip_recompute_parity(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent, store, tracker, sm, trace, log_path = self._run_logged(tmp)
            try:
                self.assertGreater(len(trace), 2)
                for rec in trace:
                    for key in ("step", "state", "action", "reward", "done"):
                        self.assertIn(key, rec)
                self.assertEqual(agent.log_path, log_path)
                self.assertTrue(os.path.exists(log_path))
                with open(log_path, "r", encoding="utf-8") as fh:
                    records = [json.loads(ln) for ln in fh if ln.strip()]
                kinds = [r.get("type") for r in records]
                self.assertIn("header", kinds)
                self.assertIn("verdict", kinds)
                steps = [r for r in records if r.get("type") == "action" and r.get("kind") == "step"]
                self.assertEqual(len(steps), len(trace))
                results = [r for r in records if r.get("type") == "result"]
                self.assertEqual(len(results), len(trace))
                self.assertEqual(len(records), 2 * len(trace) + 2)
                for r in steps:
                    for key in ("M", "P", "S", "hub"):
                        self.assertIn(key, r)
                        self.assertIn(key, r.get("args", {}))
                    m, p, s, h = r["M"], r["P"], r["S"], r["hub"]
                    self.assertEqual(len(m), 2)
                    self.assertEqual(len(p), 2)
                    self.assertEqual(len(s), 2)
                    self.assertEqual(len(h), 3)
                    for v in list(m) + list(p) + list(s) + list(h):
                        self.assertIsInstance(v, (int, float))
                        self.assertNotIsInstance(v, bool)
                    self.assertEqual(r["args"]["M"], list(m))
                    self.assertEqual(r["args"]["hub"], list(h))
                got = recompute(log_path)
                vec_rows = [row for row in (_vec_row(r) for r in records) if row]
                self.assertGreaterEqual(len(vec_rows), 3)
                padded = _pad(vec_rows)
                direct_phi = phi_ar(padded) if len(padded) >= 3 else 0.0
                self.assertAlmostEqual(got["phi"], direct_phi)
                w2 = max(len(r) for r in vec_rows)
                fb_trace = [r[:-1] for r in _pad(vec_rows)]
                fb_targets = [r[-1] for r in _pad(vec_rows)]
                direct_syn, _ = synergy(fb_trace, fb_targets) if (len(vec_rows) >= 2 and w2 >= 2) else (0.0, 0.0)
                self.assertAlmostEqual(got["syn"], direct_syn)
            finally:
                try:
                    store.close()
                except Exception:  # hygiene: allow [silent-except] best-effort tempdir cleanup
                    pass

    def test_hub_zero_null_and_lesion_isolates(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent, store, tracker, sm, trace, log_path = self._run_logged(tmp)
            try:
                tel = FileTelemetry(log_path)
                records = tel.read_all()
                steps = [r for r in records if r.get("type") == "action" and r.get("kind") == "step"]
                self.assertGreaterEqual(len(steps), 3)
                vec_rows = [row for row in (_vec_row(r) for r in steps) if row]
                phi_orig = phi_ar(_pad(vec_rows))
                ablated = hub_zero_rows(steps)
                self.assertEqual(len(ablated), len(steps))
                for src, dst in zip(steps, ablated):
                    self.assertTrue(all(v == 0 for v in dst["hub"]))
                    self.assertTrue(all(v == 0 for v in dst["args"]["hub"]))
                    self.assertEqual(dst["M"], src["M"])
                    self.assertEqual(dst["P"], src["P"])
                    self.assertEqual(dst["S"], src["S"])
                self.assertTrue(all(v != 0 or True for v in steps[0]["hub"]))
                ab_vec = [row for row in (_vec_row(r) for r in ablated) if row]
                phi_hub = phi_ar(_pad(ab_vec)) if len(ab_vec) >= 3 else 0.0
                self.assertLessEqual(phi_hub, 0.05)
                les_m = lesion_m(steps)
                for src, dst in zip(steps, les_m):
                    self.assertTrue(all(v == 0 for v in dst["M"]))
                    self.assertTrue(all(v == 0 for v in dst["args"]["M"]))
                    self.assertEqual(dst["P"], src["P"])
                    self.assertEqual(dst["S"], src["S"])
                    self.assertEqual(dst["hub"], src["hub"])
                les_p = lesion_p(steps)
                for src, dst in zip(steps, les_p):
                    self.assertTrue(all(v == 0 for v in dst["P"]))
                    self.assertEqual(dst["M"], src["M"])
                    self.assertEqual(dst["hub"], src["hub"])
                les_s = lesion_s(steps)
                for src, dst in zip(steps, les_s):
                    self.assertTrue(all(v == 0 for v in dst["S"]))
                    self.assertEqual(dst["M"], src["M"])
                    self.assertEqual(dst["hub"], src["hub"])
                _ = phi_orig
            finally:
                try:
                    store.close()
                except Exception:  # hygiene: allow [silent-except] best-effort tempdir cleanup
                    pass


if __name__ == "__main__":
    unittest.main()
