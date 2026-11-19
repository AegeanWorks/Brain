"""Failing-first regressions for the seven reforge findings in evals/.

Each test is keyed to a code in reports/reforge/genuine/ALL.json and asserts
the behaviour the finding says is missing. They are written against the
current APIs (no historical line numbers) so they keep pinning the fix.
"""

import unittest
from unittest.mock import patch

import evals.context_channel as context_channel
import evals.header_reader as header_reader
import evals.policy_ceiling as policy_ceiling
import evals.prompt_budget as prompt_budget
import evals.replication as replication
from evals.phi_diagnosis import phi_diagnosis
from evals.rule_confidence import PIN_SEEDS, _run_seed
from self_model.online import OnlinePredictor


class TestStabilityGateSilentNoop(unittest.TestCase):
    """S20: default trials=200 must still fire the higher-trial re-scan."""

    def test_default_trials_runs_the_stability_rescan(self):
        good = {"ok": True, "syn": 1.0,
                "family": {"p_upper": 0.001, "p_lower": 1.0},
                "columns": [0, 1], "blocks": ["M", "P"]}
        bad = {"ok": True, "syn": 1.0,
               "family": {"p_upper": 0.9, "p_lower": 1.0},
               "columns": [0, 1], "blocks": ["M", "P"]}
        calls = []

        def fake_scan(rows, target, trials=200, family_wise=True,
                      dedupe=True, **_kwargs):
            calls.append(trials)
            return [bad] if len(calls) == 2 else [good]

        rows = [[0.0, 0.0, 0.0]] * 5
        target = [0, 1, 0, 1, 0]
        with patch.object(replication, "scan_pairs", side_effect=fake_scan), \
                patch.object(replication, "pair_report", return_value={
                    "ok": True, "syn": 1.0, "null": {"p_upper": 0.001}}):
            result = replication.scan_with_holdout(
                rows, target, rows, target, alpha=0.01,
                require_replication=False)
        # Currently only the first scan runs, so calls == [200] and the
        # unstable candidate is selected purely on replication.
        self.assertEqual(calls, [200, 200])
        self.assertEqual(result["selected"], [])


class TestOnlyPositiveGapsFlagged(unittest.TestCase):
    """S4: a nonzero gap in either direction must be flagged."""

    def test_a_negative_gap_is_flagged(self):
        class FakeAgent:
            def run_task(self, task, seed, max_steps=200):
                return [object()] * 5  # rule reaches the goal in 5 steps

        # The oracle claims 7 steps are needed, so rule - optimal == -2.
        with patch.object(policy_ceiling, "Agent", FakeAgent), \
                patch.object(policy_ceiling, "optimal_steps",
                             lambda task, seed: 7):
            report = policy_ceiling.headroom(seeds=(0,))
        self.assertFalse(report["optimal_everywhere"])
        for task in policy_ceiling.TASKS:
            self.assertEqual(report[task]["suboptimal_seeds"], [0], task)


class TestFrozenObserveReturnType(unittest.TestCase):
    """S9: the frozen predictor's observe must return the count."""

    def test_frozen_observe_returns_a_single_count(self):
        inner = OnlinePredictor()
        key = ("T5_choice", "left", 0)
        inner.observe(key, True)
        frozen = context_channel._FrozenPredictor(inner)
        outcome = frozen.observe(key, False)
        self.assertIsInstance(outcome, int)
        self.assertEqual(outcome, inner.seen(key))


class TestPredictableOnShortTrace(unittest.TestCase):
    """S27: a sub-three-row trace cannot support phi, so not predictable."""

    def test_short_varying_trace_is_not_predictable(self):
        report = phi_diagnosis([[1.0], [2.0]])
        self.assertEqual(report["phi"], 0.0)
        # Currently predictable is True because the column varies, even
        # though phi_ar returns 0.0 below three rows by construction.
        self.assertFalse(report["predictable"])


class TestPromptBudgetSubset(unittest.TestCase):
    """S33: a --mode subset must not be reported as a missing mode."""

    def test_single_mode_report_has_no_findings(self):
        report = prompt_budget.run_battery(modes=("uncapped",))
        self.assertEqual(prompt_budget.checks(report), [])

    def test_single_mode_cli_exits_zero(self):
        subset = {"model": "PromptBackend", "modes": ["uncapped"],
                  "cases": [{"mode": "uncapped", "actions_match_rule": True,
                             "reward": 1.0, "steps": 13}]}
        with patch.object(prompt_budget, "run_battery", return_value=subset), \
                patch("sys.argv", ["prompt_budget", "--mode", "uncapped"]):
            with self.assertRaises(SystemExit) as caught:
                prompt_budget.main()
        self.assertEqual(caught.exception.code, 0)


class TestHeaderReaderSubset(unittest.TestCase):
    """S34: a --mode subset must not be reported as a missing mode."""

    def test_single_mode_report_has_no_findings(self):
        report = {"modes": ["headers"], "cases": [
            {"mode": "headers", "returned": 1, "headers": 1,
             "peak_bytes": 100, "lines": 100001, "seconds": 0.1}]}
        self.assertEqual(header_reader.checks(report), [])

    def test_single_mode_cli_exits_zero(self):
        subset = {"modes": ["headers"], "cases": [
            {"mode": "headers", "returned": 1, "headers": 1,
             "peak_bytes": 100, "lines": 100001, "seconds": 0.1}]}
        with patch.object(header_reader, "run_battery", return_value=subset), \
                patch("sys.argv", ["header_reader", "--mode", "headers"]):
            with self.assertRaises(SystemExit) as caught:
                header_reader.main()
        self.assertEqual(caught.exception.code, 0)


class TestPinExpectationsAsserted(unittest.TestCase):
    """S51: every PIN_SEEDS step/reward pair must gate a drifted trace."""

    def test_pin_values_match_the_current_traces(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            for task, seed, steps, reward in PIN_SEEDS:
                trace, _pairs = _run_seed(task, seed, True, directory,
                                          "pin-%s-%d" % (task, seed))
                self.assertEqual(len(trace), steps, (task, seed, "steps"))
                self.assertEqual(sum(r["reward"] for r in trace), reward,
                                 (task, seed, "reward"))

    def test_measure_seeds_rejects_a_drifted_pin(self):
        import tempfile

        import evals.rule_confidence as rc

        with tempfile.TemporaryDirectory() as directory, \
                patch.object(rc, "_run_seed", return_value=([], [])):
            # measure_seeds currently binds _steps/_reward to throwaway
            # names, so a zero-length trace is silently accepted.
            with self.assertRaises(AssertionError):
                rc.measure_seeds("drift", directory)


if __name__ == "__main__":
    unittest.main()
