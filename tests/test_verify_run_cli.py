"""The aggregate verifier needs a command line, not just a function.

Cycle 128 shipped `verify_run`, which composes every evidence check, but a
survey of top-level modules showed it had no `main`, no `argparse` and no
`__main__` guard. A consumer could only use it by importing it, so the one
call that checks everything was the one thing a human could not run.

These tests pin the CLI contract: `--log` is required, a clean log exits 0,
a failing log exits 1 with the failing layer named, and a missing path
exits 2 for misuse rather than raising a traceback.
"""

import os
import subprocess
import sys
import tempfile
import unittest

from agent import Agent
from run_verify import format_report

BRAIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _write_log(directory, name="run.jsonl", task="T3_navigate", seed=15):
    path = os.path.join(directory, name)
    Agent().run_task_logged(task, seed, max_steps=200, log_path=path)
    return path


def _run(args):
    return subprocess.run([sys.executable, "-m", "run_verify"] + args,
                          cwd=BRAIN, capture_output=True, text=True,
                          timeout=120)


class TestVerifyRunCli(unittest.TestCase):
    def test_a_clean_log_exits_zero(self):
        with tempfile.TemporaryDirectory() as d:
            path = _write_log(d)
            proc = _run(["--log", path])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("OK", proc.stdout)

    def test_a_failing_log_exits_one_and_names_the_layer(self):
        with tempfile.TemporaryDirectory() as d:
            path = _write_log(d)
            # Truncate the file after the header: the chain breaks.
            with open(path, "r", encoding="utf-8") as fh:
                lines = fh.readlines()
            with open(path, "w", encoding="utf-8") as fh:
                fh.writelines(lines[:2])
            proc = _run(["--log", path])
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("chain", proc.stdout)

    def test_a_missing_log_is_misuse(self):
        with tempfile.TemporaryDirectory() as d:
            proc = _run(["--log", os.path.join(d, "nope.jsonl")])
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)

    def test_no_arguments_is_misuse(self):
        proc = _run([])
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)

    def test_the_json_flag_prints_the_full_report(self):
        import json

        with tempfile.TemporaryDirectory() as d:
            path = _write_log(d)
            proc = _run(["--log", path, "--json"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["checked"],
                         ["chain", "episode", "replay", "results"])

    def test_format_report_names_each_layer(self):
        with tempfile.TemporaryDirectory() as d:
            path = _write_log(d)
            text = format_report({
                "ok": True, "log": path, "findings": [],
                "checked": ["chain", "episode", "replay", "results"],
                "layers": {name: {"ok": True} for name in
                           ("chain", "episode", "replay", "results")},
            })
        self.assertIn("chain", text)
        self.assertIn("results", text)
        self.assertIn("OK", text)


if __name__ == "__main__":
    unittest.main()
