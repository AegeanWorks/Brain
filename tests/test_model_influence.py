"""Say plainly how much of a run the model actually decided.

The measured problem this pins: with the trust guards on, a model that always
proposes ``up`` is rejected on 12 of 13 steps and the rule policy wins the
episode. The transcript therefore looked like model competence when it was
entirely the rule's. Both the JSON report and the human transcript now state
the accepted/rejected counts, and `--trust-model` exposes the counterfactual.

    guarded  T3_navigate seed 15:  13 steps, reward 1.0,  0 accepted, 12 rejected
    trusted  T3_navigate seed 15:  40+ steps, reward 0.0, all accepted
"""

import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

import brain
import run_agent
from agent import Agent, Planner
from models.openai_backend import OpenAIBackend


class _UpClient:
    """A client that always proposes one action, like a stuck model."""

    model = "always-up"

    def __init__(self, text="up"):
        self.text = text
        self.calls = 0

    def chat(self, messages, temperature=0.0, max_tokens=8):
        self.calls += 1
        return {"text": self.text, "model": self.model, "seconds": 0.0,
                "usage": {}}


def _guarded(text="up"):
    return Agent(planner=Planner(backend=OpenAIBackend(client=_UpClient(text))))


def _trusted(text="up"):
    return Agent(planner=Planner(
        backend=OpenAIBackend(client=_UpClient(text)),
        noop_guard=False, progress_guard=False, trust_window=None,
        skip_after_distrust=False))


def _reward(trace):
    return sum(float(step.get("reward", 0.0)) for step in trace)


def _UpBackend():
    """A ready backend whose model always proposes ``up``."""
    return OpenAIBackend(client=_UpClient("up"))


class TestCounters(unittest.TestCase):
    def test_a_rejected_proposal_is_counted_as_a_fallback(self):
        agent = _guarded("up")
        agent.run_task("T3_navigate", 15)
        self.assertEqual(agent.planner.accepted, 0)
        self.assertGreater(agent.planner.fallbacks, 0)

    def test_a_trusted_proposal_is_counted_as_accepted(self):
        agent = _trusted("up")
        agent.run_task("T3_navigate", 15, max_steps=20)
        self.assertGreater(agent.planner.accepted, 0)
        self.assertEqual(agent.planner.fallbacks, 0)

    def test_the_guards_are_what_make_the_episode_succeed(self):
        guarded_trace = _guarded("up").run_task("T3_navigate", 15)
        trusted_trace = _trusted("up").run_task("T3_navigate", 15, max_steps=40)
        self.assertEqual(_reward(guarded_trace), 1.0)
        self.assertEqual(_reward(trusted_trace), 0.0)
        self.assertLess(len(guarded_trace), len(trusted_trace))


class TestHumanReport(unittest.TestCase):
    def _render(self, accepted, fallbacks):
        planner = Planner()
        planner.accepted, planner.fallbacks = accepted, fallbacks
        output = io.StringIO()
        with redirect_stdout(output):
            brain._report_model_influence(planner)
        return output.getvalue()

    def test_zero_acceptances_says_the_rule_produced_the_run(self):
        text = self._render(0, 12)
        self.assertIn("12 proposals, 0 accepted, 12 rejected", text)
        self.assertIn("the rule policy produced this run", text)
        self.assertIn("--trust-model", text)

    def test_some_acceptances_report_counts_without_the_warning(self):
        text = self._render(7, 5)
        self.assertIn("12 proposals, 7 accepted, 5 rejected", text)
        self.assertNotIn("changed nothing", text)

    def test_never_consulted_is_stated_not_implied(self):
        self.assertIn("never consulted", self._render(0, 0))

    def test_every_rendered_line_is_console_safe(self):
        for counts in ((0, 12), (7, 5), (0, 0)):
            self._render(*counts).encode("cp1254")

    def test_the_run_transcript_ends_with_the_influence_line(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = brain.main(["run", "T3_navigate", "--seed", "15"])
        self.assertEqual(code, 0)
        self.assertIn("policy rule", output.getvalue())
        self.assertNotIn("proposals", output.getvalue(),
                         "the rule policy consults no model")

    def test_an_openai_run_puts_the_influence_line_in_the_transcript(self):
        # Drive the real CLI branch (not just _report_model_influence): with
        # --backend openai a planner exists, so its counts must reach stdout.
        with mock.patch("models.registry.build",
                        return_value=_UpBackend()):
            output = io.StringIO()
            with redirect_stdout(output):
                code = brain.main(["run", "T3_navigate", "--seed", "15",
                                   "--backend", "openai"])
        text = output.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("policy openai", text)
        self.assertIn("model: 12 proposals, 0 accepted, 12 rejected", text)
        self.assertIn("the rule policy produced this run", text)


class TestJsonReport(unittest.TestCase):
    def _run(self, extra=()):
        with mock.patch.object(run_agent, "_build_backend") as build:
            build.return_value = OpenAIBackend(client=_UpClient("up"))
            output, err = io.StringIO(), io.StringIO()
            with redirect_stdout(output), redirect_stderr(err):
                code = run_agent.main(["--task", "T3_navigate", "--seed", "15",
                                       "--backend", "openai", *extra])
        return code, json.loads(output.getvalue()), err.getvalue()

    def test_the_report_carries_the_counts(self):
        code, report, _err = self._run()
        self.assertEqual(code, 0)
        self.assertEqual(report["model_accepted"], 0)
        self.assertEqual(report["model_rejected"], 12)

    def test_a_useless_model_prints_a_warning_on_stderr(self):
        _code, _report, err = self._run()
        self.assertIn("changed nothing", err)

    def test_trust_model_disables_the_guards(self):
        planner = run_agent._make_planner(_UpBackend(), trust_model=True)
        self.assertIs(planner.noop_guard, False)
        self.assertIs(planner.progress_guard, False)
        self.assertIsNone(planner.trust_window)
        self.assertIs(planner.skip_after_distrust, False)

    def test_the_default_keeps_every_guard_on(self):
        planner = run_agent._make_planner(_UpBackend(), trust_model=False)
        self.assertIs(planner.noop_guard, True)
        self.assertIs(planner.progress_guard, True)
        self.assertEqual(planner.trust_window, 20)
        self.assertIs(planner.skip_after_distrust, True)

    def test_no_backend_means_no_planner(self):
        self.assertIsNone(run_agent._make_planner(None, trust_model=False))


if __name__ == "__main__":
    unittest.main()
