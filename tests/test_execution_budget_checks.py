"""The execution-budget battery must enforce its own caps.

``evals/execution_budget.py`` prints five modes: a generous budget leaves
the 13-step/1.0 run byte-identical to the rule, and the step, LLM, token
and time caps each raise ``BudgetExceeded`` naming their own dimension
after exceeding it. It exited 0 either way, so a budget that stopped
enforcing (or enforced the wrong dimension) only altered the printed JSON.

Measured: generous 13 steps / success / actions match; step raises
``steps`` 4>3 at 3 steps; llm raises ``llm_calls`` 3>2 after 2 calls; token
raises ``tokens`` 10>8; time raises ``seconds``.
"""

import unittest

from evals.execution_budget import MODES, checks, run_battery

#: The dimension each capped mode must name, and the modes that must not raise.
EXPECTED_KIND = {
    "generous": None,
    "step": "steps",
    "llm": "llm_calls",
    "token": "tokens",
    "time": "seconds",
}


def _case(report, mode):
    for case in report["cases"]:
        if case["mode"] == mode:
            return case
    raise AssertionError("mode missing: %s" % mode)


class TestExecutionBudgetChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = run_battery()

    def test_a_real_run_has_no_findings(self):
        self.assertEqual(checks(self.report), [])

    def test_each_mode_names_its_own_dimension(self):
        for mode in MODES:
            self.assertEqual(_case(self.report, mode)["kind"],
                             EXPECTED_KIND[mode], mode)

    def test_a_capped_run_exceeds_its_limit(self):
        for mode in ("step", "llm", "token"):
            case = _case(self.report, mode)
            self.assertGreater(case["used"], case["limit"], mode)

    def test_generous_budget_preserves_the_rule_run(self):
        generous = _case(self.report, "generous")
        self.assertTrue(generous["actions_match_rule"])
        self.assertTrue(generous["success"])
        self.assertEqual(generous["steps"], 13)
        self.assertEqual(generous["reward"], 1.0)

    def test_a_capped_run_is_not_a_success(self):
        for mode in ("step", "llm", "token", "time"):
            self.assertFalse(_case(self.report, mode)["success"], mode)

    def test_a_budget_that_stops_enforcing_is_named(self):
        broken = {"cases": [dict(c) for c in self.report["cases"]]}
        _case(broken, "step")["kind"] = None
        findings = checks(broken)
        self.assertTrue(any("step" in f for f in findings), findings)

    def test_a_wrong_dimension_is_named(self):
        broken = {"cases": [dict(c) for c in self.report["cases"]]}
        _case(broken, "llm")["kind"] = "steps"
        findings = checks(broken)
        self.assertTrue(any("llm" in f for f in findings), findings)

    def test_a_cap_above_its_limit_is_named(self):
        broken = {"cases": [dict(c) for c in self.report["cases"]]}
        _case(broken, "token")["used"] = 1.0  # below limit 8
        findings = checks(broken)
        self.assertTrue(any("token" in f for f in findings), findings)

    def test_a_changed_generous_run_is_named(self):
        broken = {"cases": [dict(c) for c in self.report["cases"]]}
        _case(broken, "generous")["actions_match_rule"] = False
        findings = checks(broken)
        self.assertTrue(any("generous" in f for f in findings), findings)

    def test_a_missing_mode_is_named(self):
        broken = {"cases": [c for c in self.report["cases"]
                            if c["mode"] != "time"]}
        findings = checks(broken)
        self.assertTrue(any("missing" in f for f in findings), findings)


if __name__ == "__main__":
    unittest.main()
