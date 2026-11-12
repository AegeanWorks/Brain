"""A world-provided context block carries a detectable interaction.

``DualWorld`` exports two independent latent bits through the agent's
optional ``G`` signal block. This pins the channel: the default reader keeps
the shipped six-column row, the extended reader appends ``G``, a world
without the hook emits nothing, and the signed scan recovers the planted
``G`` interaction on train rows and holdout rows while a noise world with
the same latents selects nothing.
"""

import unittest

from agent import Agent
from evals.context_channel import collect_rows, measure
from evals.module_state import read_signals, signals_from_trace
from worlds.dual import DualWorld, NoiseDualWorld
from worlds.grid import GridWorld


def _target_leak(values, target):
    mapping = {}
    for value, outcome in zip(values, target):
        if mapping.setdefault(value, outcome) != outcome:
            return False
    return True


class TestContextChannel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.trace = Agent(world=DualWorld(0)).run(max_steps=4)

    def test_default_reader_keeps_the_six_column_row(self):
        rows = signals_from_trace(self.trace)
        self.assertTrue(rows)
        self.assertTrue(all(len(row) == 7 for row in rows))

    def test_extended_reader_appends_the_context_block(self):
        rows = signals_from_trace(self.trace, include_context=True)
        world = DualWorld(0)
        self.assertEqual(len(rows), len(world.latents))
        for row, (a, b) in zip(rows, world.latents):
            self.assertEqual(len(row), 9)
            self.assertEqual([row[6], row[7]], [float(a), float(b)])

    def test_world_without_hook_emits_no_context(self):
        trace = Agent(world=GridWorld("T1_forage", 0)).run(max_steps=4)
        self.assertTrue(all("G" not in step["signals"] for step in trace))

    def test_disabled_signals_emit_no_context(self):
        agent = Agent(world=DualWorld(0), module_signals=False)
        trace = agent.run(max_steps=4)
        self.assertEqual(signals_from_trace(trace, include_context=True), [])

    def test_each_latent_alone_does_not_determine_the_reward(self):
        rows, target = collect_rows(DualWorld, range(20))
        for column in (6, 7):
            self.assertFalse(_target_leak([row[column] for row in rows], target))

    def test_planted_pair_is_selected_and_noise_is_not(self):
        planted = measure(DualWorld, range(10), range(10, 20))
        noise = measure(NoiseDualWorld, range(10), range(10, 20))
        self.assertEqual(planted["selected"], [[6, 7]])
        self.assertTrue(planted["g_pair_selected"])
        self.assertEqual(noise["selected"], [])

    def test_dropping_the_context_block_is_the_executable_ablation(self):
        ablated = measure(DualWorld, range(10), range(10, 20),
                          include_context=False)
        self.assertEqual(ablated["selected"], [])
        self.assertFalse(ablated["g_pair_selected"])

    def test_signals_reach_the_telemetry_log(self):
        import json
        import os
        import tempfile

        from telemetry.log import Telemetry

        handle, path = tempfile.mkstemp(suffix=".jsonl")
        os.close(handle)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        agent = Agent(world=DualWorld(2), telemetry_log=Telemetry(path))
        agent.run(max_steps=4)
        rows = read_signals(path, include_context=True)
        self.assertTrue(rows)
        self.assertTrue(all(len(row) == 9 for row in rows))
        with open(path, "r", encoding="utf-8") as handle:
            blocks = [json.loads(line)["args"]["signals"]
                      for line in handle
                      if line.strip() and json.loads(line).get("type") == "action"]
        self.assertTrue(blocks)
        self.assertTrue(all("G" in block for block in blocks))


if __name__ == "__main__":
    unittest.main()
