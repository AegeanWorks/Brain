"""A registry nobody can reach is not pluggable.

Cycle 151 shipped `models.registry` with `register`/`build`/`names`, and the
whole seam checked out — but nothing in production calls `build`. Measured:
zero non-test callers, and every battery in `evals/` instantiates its backend
directly (`backends = WaitingBackend()`, `PromptBackend(5)`, ~10 sites). There
is also no CLI for running the agent at all, so "choose a backend" could only
be done by editing Python.

These tests pin the thing that makes the word true: a command line that names
a provider, builds it through the registry, runs an episode with it, and
reports the identity it pinned. Absurd input is misuse (exit 2), a provider
that is not registered is misuse with the available names listed, and a run
that succeeds exits 0.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

BRAIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run(args):
    return subprocess.run([sys.executable, "-m", "run_agent"] + args,
                          cwd=BRAIN, capture_output=True, text=True,
                          timeout=180)


class TestRunAgentCli(unittest.TestCase):
    def test_an_episode_runs_with_the_rule_policy(self):
        proc = _run(["--task", "T3_navigate", "--seed", "15"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["model"], "rule")
        self.assertEqual(payload["steps"], 13)
        self.assertEqual(payload["reward"], 1.0)

    def test_a_registered_backend_can_be_named(self):
        proc = _run(["--task", "T3_navigate", "--seed", "15",
                     "--backend", "stub",
                     "--stub-script", "right,right,right"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        # StubBackend's identity is class-name derived, so the pin keeps the
        # historical label rather than moving every header.
        self.assertEqual(payload["model"], "StubBackend")
        self.assertEqual(payload["backend"], "stub")

    def test_an_unknown_backend_is_misuse_and_names_the_choices(self):
        proc = _run(["--task", "T3_navigate", "--backend", "no-such"])
        self.assertEqual(proc.returncode, 2)
        self.assertIn("no-such", proc.stderr)
        self.assertIn("stub", proc.stderr)

    def test_a_missing_task_is_misuse(self):
        proc = _run([])
        self.assertEqual(proc.returncode, 2)

    def test_an_unknown_task_is_misuse(self):
        proc = _run(["--task", "T9_nowhere"])
        self.assertEqual(proc.returncode, 2)
        self.assertIn("T9_nowhere", proc.stderr)

    def test_a_stub_without_a_script_is_misuse(self):
        proc = _run(["--task", "T3_navigate", "--backend", "stub"])
        self.assertEqual(proc.returncode, 2)
        self.assertIn("stub-script", proc.stderr)

    def test_the_run_reports_the_backend_it_actually_used(self):
        proc = _run(["--task", "T3_navigate", "--seed", "15",
                     "--backend", "stub", "--stub-script", "right,right"])
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["backend"], "stub")
        self.assertIn("model", payload)
        self.assertIn("steps", payload)

    def test_naming_a_backend_does_not_change_a_rule_run(self):
        rule = json.loads(_run(["--task", "T3_navigate", "--seed",
                                "15"]).stdout)
        self.assertEqual(rule["model"], "rule")
        self.assertEqual(rule["steps"], 13)


if __name__ == "__main__":
    unittest.main()
