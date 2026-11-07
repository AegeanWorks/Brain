"""Cold-start recovery: restart re-reads the persisted task layout.

Failing-first harness: a warm run saves the full initial state, the
process closes and reopens the store, and the cold world omits goal
fields from every observation. Under a store-blind planner the cold
run waits at the cap (200 steps, 0.0 reward); with the persisted layout
read back it must reproduce the warm action outcomes. The probe names
which substrate supplied each recalled field, and the ablation cuts the
recall source to prove the coupling.
"""

import json
import os
import tempfile
import unittest

from agent import Agent
from evals.coldstart import CASES, cold_run, warm_run
from memory.store import MemoryStore
from telemetry.log import Telemetry


def _steps(log_path):
    return [record for record in Telemetry(log_path).read_all()
            if record.get("type") == "action" and record.get("kind") == "step"]


class TestColdStartRecovery(unittest.TestCase):
    def test_restart_recovers_layout_from_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "mem.db")
            warm = MemoryStore(path)
            try:
                for task, seed, _want_steps, _want_reward in CASES:
                    warm_run(warm, task, seed)
            finally:
                warm.close()
            cold = MemoryStore(path)
            try:
                for task, seed, want_steps, want_reward in CASES:
                    agent, trace, _backend = cold_run(cold, task, seed)
                    self.assertTrue(trace[-1]["done"], "%s:%d" % (task, seed))
                    self.assertEqual(len(trace), want_steps, "%s:%d" % (task, seed))
                    self.assertEqual(sum(r["reward"] for r in trace), want_reward,
                                     "%s:%d" % (task, seed))
                    probe = agent.planner.last_probe
                    self.assertGreaterEqual(probe["store_reads"], 1)
                    self.assertIn("persistent", probe)
            finally:
                cold.close()

    def test_layout_ablation_truncates_at_cap(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "mem.db")
            warm = MemoryStore(path)
            try:
                for task, seed, _want_steps, _want_reward in CASES:
                    warm_run(warm, task, seed)
            finally:
                warm.close()
            cold = MemoryStore(path)
            try:
                for task, seed, _want_steps, _want_reward in CASES:
                    _agent, trace, _backend = cold_run(cold, task, seed, ablate=True)
                    self.assertEqual(len(trace), 200, "%s:%d" % (task, seed))
                    self.assertEqual(sum(r["reward"] for r in trace), 0.0,
                                     "%s:%d" % (task, seed))
            finally:
                cold.close()

    def test_probe_names_persistent_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "mem.db")
            log_path = os.path.join(tmp, "cold.jsonl")
            warm = MemoryStore(path)
            try:
                warm_run(warm, "T3_navigate", 15)
            finally:
                warm.close()
            cold = MemoryStore(path)
            try:
                _agent, trace, _backend = cold_run(
                    cold, "T3_navigate", 15, log_path=log_path)
            finally:
                cold.close()
            self.assertEqual(len(trace), 13)
            first = _steps(log_path)[0]
            probe = first["args"]["probe"]
            self.assertEqual(probe["store_reads"], 1)
            self.assertIn("target", probe["persistent"])
            self.assertIn("obstacles", probe["persistent"])

    def test_warm_probe_uses_state_not_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "mem.db")
            log_path = os.path.join(tmp, "warm.jsonl")
            store = MemoryStore(path)
            try:
                agent = Agent(memory_store=store)
                agent.telemetry_log = Telemetry(log_path)
                agent.telemetry_log.write_header("T3_navigate", 200, policy="warm-test")
                trace = agent.run_task("T3_navigate", 15)
            finally:
                store.close()
            self.assertEqual(len(trace), 13)
            first = _steps(log_path)[0]
            probe = first["args"]["probe"]
            self.assertEqual(probe["store_reads"], 0)
            self.assertEqual(probe["persistent"], [])
            self.assertIn("target", probe["state"])

    def test_layout_first_write_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = MemoryStore(os.path.join(tmp, "mem.db"))
            try:
                full = json.dumps({"target": [6, 7], "obstacles": [[6, 1]]})
                stripped = json.dumps({"x": 0, "y": 0})
                store.save_layout("T3_navigate", 15, full)
                store.save_layout("T3_navigate", 15, stripped)
                self.assertEqual(store.get_layout("T3_navigate", 15), full)
                fresh = MemoryStore(os.path.join(tmp, "fresh.db"))
                try:
                    self.assertIsNone(fresh.get_layout("T3_navigate", 15))
                finally:
                    fresh.close()
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
