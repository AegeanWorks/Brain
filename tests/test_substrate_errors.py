"""Substrate error visibility: counters exist, ok reflects reward, faults counted."""

import os
import tempfile
import unittest

from agent import Agent
from memory.store import MemoryStore
from planner.plan import Planner as TrackerPlanner
from self_model.model import SelfModel as PersistentSelfModel


class FaultyStore:
    """Minimal memory_store double whose save always raises."""

    def bind_hub(self, getter):
        self._get_hub = getter

    def save(self, key, content, conf):
        raise OSError("injected save failure")

    def count(self):
        return 0


class TestSubstrateErrors(unittest.TestCase):
    def test_exposes_zero_counters_after_clean_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "mem.db")
            log_path = os.path.join(tmp, "run.jsonl")
            store = MemoryStore(db_path)
            try:
                tracker = TrackerPlanner([(f"s{i}", f"op{i}") for i in range(30)])
                sm = PersistentSelfModel()
                agent = Agent(memory_store=store, planner_tracker=tracker, self_model=sm)
                trace = agent.run_task_logged("T1_forage", 7, max_steps=30, log_path=log_path)
                self.assertGreater(len(trace), 0)
                errors = agent.substrate_errors()
                self.assertEqual(
                    errors,
                    {"bind": 0, "memory_store": 0, "planner_tracker": 0,
                     "self_model": 0, "telemetry_log": 0, "verdict": 0},
                )
            finally:
                store.close()

    def test_persistent_ok_reflects_reward(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "mem.db")
            log_path = os.path.join(tmp, "run.jsonl")
            store = MemoryStore(db_path)
            try:
                tracker = TrackerPlanner([(f"s{i}", f"op{i}") for i in range(30)])
                sm = PersistentSelfModel()
                agent = Agent(memory_store=store, planner_tracker=tracker, self_model=sm)
                trace = agent.run_task_logged("T1_forage", 7, max_steps=30, log_path=log_path)
                rewards = sum(1 for r in trace if float(r["reward"]) > 0.0)
                snap = sm.snapshot()
                self.assertEqual(snap["steps"], len(trace))
                self.assertEqual(snap["errors"], len(trace) - rewards)
                self.assertGreater(snap["errors"], 0)
            finally:
                store.close()

    def test_faulty_store_counted_and_run_continues(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "run.jsonl")
            faulty = FaultyStore()
            tracker = TrackerPlanner([(f"s{i}", f"op{i}") for i in range(10)])
            sm = PersistentSelfModel()
            agent = Agent(memory_store=faulty, planner_tracker=tracker, self_model=sm)
            trace = agent.run_task_logged("T1_forage", 7, max_steps=10, log_path=log_path)
            self.assertGreater(len(trace), 0)
            errors = agent.substrate_errors()
            self.assertEqual(errors["memory_store"], len(trace))
            self.assertEqual(errors["bind"], 0)


if __name__ == "__main__":
    unittest.main()
