"""Agent loop checks: run completes with a non-empty trace."""

import json
import os
import tempfile
import unittest

from agent import Agent, Memory, Planner, SelfModel, Telemetry


class TestAgent(unittest.TestCase):
    def test_run_completes_all_tasks(self):
        for task in ("T1_forage", "T2_delayed_match", "T3_navigate"):
            agent = Agent()
            trace = agent.run_task(task, 7, max_steps=200)
            self.assertGreater(len(trace), 0)
            last = trace[-1]
            for key in ("step", "state", "action", "reward", "done"):
                self.assertIn(key, last)
            # loop stopped on done or on the step cap
            self.assertTrue(last["done"] or len(trace) == 200)
            self.assertGreater(len(agent.memory), 0)
            self.assertGreater(len(agent.telemetry.events()), 0)
            self.assertGreater(len(agent.selfmodel.history()), 0)

    def test_run_with_injected_world(self):
        from worlds.grid import GridWorld

        agent = Agent(
            memory=Memory(),
            planner=Planner(),
            selfmodel=SelfModel(),
            telemetry=Telemetry(),
            world=GridWorld("T1_forage", 2),
        )
        trace = agent.run(max_steps=50)
        self.assertGreater(len(trace), 0)

    def test_hub_shared(self):
        agent = Agent()
        agent.hub_write({"k": "v"})
        self.assertEqual(agent.get_hub()["k"], "v")
        self.assertEqual(agent.memory.read_hub()["k"], "v")
        self.assertEqual(agent.planner.read_hub()["k"], "v")
        with self.assertRaises(TypeError):
            agent.hub_write("not-a-dict")

    def test_tempdir_trace_roundtrip(self):
        agent = Agent()
        trace = agent.run_task("T1_forage", 5, max_steps=30)
        self.assertGreater(len(trace), 0)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "trace.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(trace, fh)
            with open(path, encoding="utf-8") as fh:
                back = json.load(fh)
        self.assertEqual(len(back), len(trace))
        self.assertEqual(back[0]["action"], trace[0]["action"])


if __name__ == "__main__":
    unittest.main()
