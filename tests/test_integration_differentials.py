"""Integration-structure differentials: hub/M lesions kill syn, P/S change nothing."""

import os
import tempfile
import unittest

from agent import Agent
from evals import estimators as est
from evals.recompute import _vec_row, recompute
from memory.store import MemoryStore
from planner.plan import Planner as TrackerPlanner
from self_model.model import SelfModel as PersistentSelfModel
from telemetry.ablate import hub_zero_rows, lesion_m, lesion_p, lesion_s
from telemetry.log import Telemetry as FileTelemetry


def _pad(rows):
    width = max(len(r) for r in rows)
    return [list(r) + [0.0] * (width - len(r)) for r in rows]


def _stats(rows):
    vec = [row for row in (_vec_row(r) for r in rows) if row]
    padded = _pad(vec)
    phi = est.phi_ar(padded) if len(padded) >= 3 else 0.0
    trace = [r[:-1] for r in _pad(vec)]
    targets = [r[-1] for r in _pad(vec)]
    syn, syn_n = est.synergy(trace, targets)
    return phi, syn, syn_n


class TestIntegrationDifferentials(unittest.TestCase):
    def _fixed_steps(self, tmp):
        db_path = os.path.join(tmp, "mem.db")
        log_path = os.path.join(tmp, "run.jsonl")
        store = MemoryStore(db_path)
        try:
            tracker = TrackerPlanner([(f"s{i}", f"op{i}") for i in range(30)])
            sm = PersistentSelfModel()
            agent = Agent(memory_store=store, planner_tracker=tracker, self_model=sm)
            trace = agent.run_task_logged("T1_forage", 7, max_steps=30, log_path=log_path)
            self.assertEqual(len(trace), 15)
            records = FileTelemetry(log_path).read_all()
            steps = [r for r in records
                     if r.get("type") == "action" and r.get("kind") == "step"]
            self.assertEqual(len(steps), 15)
            got = recompute(log_path)
            return steps, got
        finally:
            store.close()

    def test_signal_present_and_phi_floor(self):
        with tempfile.TemporaryDirectory() as tmp:
            steps, got = self._fixed_steps(tmp)
            self.assertGreater(got["syn"], 0.05)
            self.assertAlmostEqual(got["phi"], 0.0)
            phi, syn, _ = _stats(steps)
            self.assertAlmostEqual(phi, 0.0)
            self.assertAlmostEqual(syn, got["syn"])

    def test_hub_and_memory_lesions_kill_synergy(self):
        with tempfile.TemporaryDirectory() as tmp:
            steps, got = self._fixed_steps(tmp)
            for lesioned in (hub_zero_rows(steps), lesion_m(steps)):
                phi, syn, syn_n = _stats(lesioned)
                self.assertAlmostEqual(phi, 0.0)
                self.assertAlmostEqual(syn, 0.0)
                self.assertAlmostEqual(syn_n, 0.0)
            self.assertGreater(got["syn"], 0.05)

    def test_planner_and_selfmodel_lesions_change_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            steps, got = self._fixed_steps(tmp)
            for lesioned in (lesion_p(steps), lesion_s(steps)):
                phi, syn, syn_n = _stats(lesioned)
                self.assertAlmostEqual(phi, got["phi"])
                self.assertAlmostEqual(syn, got["syn"])
                self.assertAlmostEqual(syn_n, got["syn_n"])


if __name__ == "__main__":
    unittest.main()
