"""The demo must prove something: real episodes, real deltas.

The scaffolded compat contract runs ``python demo.py --scripted --seed 7``
twice and compares the ``WORLD-DELTA`` lines, so those lines have to come
from an actual run. These tests pin that: different seeds give different
deltas, the same seed repeats exactly, and the deltas describe the world
facts the agent changed rather than constants.
"""

import io
import unittest
from contextlib import redirect_stdout

import demo
from agent import Agent


def _run(argv):
    output = io.StringIO()
    with redirect_stdout(output):
        code = demo.main(argv)
    return code, output.getvalue().splitlines()


class TestScriptedOutput(unittest.TestCase):
    def test_the_scripted_run_prints_world_deltas(self):
        code, lines = _run(["--scripted", "--seed", "7"])
        self.assertEqual(code, 0)
        self.assertTrue(any(line.startswith("WORLD-DELTA:") for line in lines))
        self.assertEqual(lines[0], "task=T3_navigate seed=7")

    def test_the_same_seed_repeats_byte_for_byte(self):
        _first_code, first = _run(["--scripted", "--seed", "7"])
        _second_code, second = _run(["--scripted", "--seed", "7"])
        self.assertEqual(first, second)

    def test_a_different_seed_changes_the_deltas(self):
        _code_a, first = _run(["--scripted", "--seed", "7"])
        _code_b, second = _run(["--scripted", "--seed", "1"])
        self.assertNotEqual(first, second)

    def test_the_deltas_come_from_the_episode_not_a_constant(self):
        _code, lines = _run(["--scripted", "--seed", "7"])
        steps = [line for line in lines if line.startswith("WORLD-DELTA: steps=")]
        self.assertEqual(len(steps), 1)
        observed = len(Agent().run_task("T3_navigate", 7, max_steps=200))
        self.assertEqual(steps[0], "WORLD-DELTA: steps=0->%d" % observed)

    def test_a_walk_is_reported_as_position_changes(self):
        _code, lines = _run(["--scripted", "--seed", "7"])
        self.assertTrue(any(line.startswith("WORLD-DELTA: x=") for line in lines))
        self.assertTrue(any(line.startswith("WORLD-DELTA: y=") for line in lines))

    def test_a_collection_is_reported_as_an_item_delta(self):
        _code, lines = _run(["--scripted", "--seed", "7"])
        self.assertIn("WORLD-DELTA: items=0->1", lines)


class TestHumanOutput(unittest.TestCase):
    def test_the_human_trace_names_the_task_and_the_verdict(self):
        code, lines = _run(["--seed", "7"])
        self.assertEqual(code, 0)
        self.assertIn("task T3_navigate, seed 7", lines[0])
        self.assertTrue(any("done (steps=" in line for line in lines))
        self.assertTrue(any("reward 1.0" in line for line in lines))

    def test_every_step_line_carries_an_action_and_a_position(self):
        _code, lines = _run(["--seed", "7"])
        steps = [line for line in lines if line.startswith("  ")]
        self.assertTrue(steps)
        for line in steps:
            self.assertIn("[", line)
            self.assertIn("]", line)


class TestHelperFunctions(unittest.TestCase):
    def test_deltas_ignores_unchanged_facts(self):
        previous = {"x": 1, "y": 2, "items": 0}
        self.assertEqual(demo.deltas(previous, {"x": 1, "y": 2, "items": 0}), [])

    def test_deltas_reports_each_changed_fact(self):
        previous = {"x": 1, "y": 2, "items": 0}
        self.assertEqual(demo.deltas(previous, {"x": 1, "y": 3, "items": 1}),
                         [("y", 2, 3), ("items", 0, 1)])

    def test_the_first_step_reports_from_none(self):
        previous = {"x": None, "y": None, "items": 0}
        self.assertEqual(demo.deltas(previous, {"x": 1, "y": 0, "items": 0}),
                         [("x", None, 1), ("y", None, 0)])


if __name__ == "__main__":
    unittest.main()
