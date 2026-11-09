"""The prompt-budget battery must check that the cap changes no behavior.

``evals/prompt_budget.py`` already computes ``actions_match_rule`` — the
claim that a prompt cap trims the prompt without altering a single action —
and prints it, but exits 0 either way. A cap that silently changed an
action would show as ``actions_match_rule: false`` in the JSON and nothing
would fail.

The README states the numbers: uncapped 63 tokens, budgeted 52 with 13
omitted visit lines on T3:15, actions/steps/reward identical.

``checks(report)`` enforces the behavioral claim, the step/reward parity,
and that the cap actually trimmed the prompt.
"""

import unittest

from evals.prompt_budget import MODES, checks, run_battery


def _mode(report, name):
    for case in report["cases"]:
        if case["mode"] == name:
            return case
    raise AssertionError("mode missing: %s" % name)


class TestPromptBudgetChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = run_battery()

    def test_a_real_run_has_no_findings(self):
        self.assertEqual(checks(self.report), [])

    def test_actions_match_the_rule_in_every_mode(self):
        for mode in MODES:
            self.assertTrue(_mode(self.report, mode)["actions_match_rule"],
                            mode)

    def test_steps_and_reward_are_identical_across_modes(self):
        steps = {_mode(self.report, m)["steps"] for m in MODES}
        rewards = {_mode(self.report, m)["reward"] for m in MODES}
        self.assertEqual(len(steps), 1, steps)
        self.assertEqual(len(rewards), 1, rewards)
        self.assertEqual(steps, {13})
        self.assertEqual(rewards, {1.0})

    def test_the_cap_actually_trimmed(self):
        uncapped = _mode(self.report, "uncapped")
        budgeted = _mode(self.report, "budgeted")
        self.assertGreater(uncapped["prompt_max_tokens"],
                           budgeted["prompt_max_tokens"])
        self.assertEqual(uncapped["prompt_omitted_total"], 0)
        self.assertGreater(budgeted["prompt_omitted_total"], 0)

    def test_a_changed_action_is_named(self):
        broken = {"cases": [dict(c) for c in self.report["cases"]]}
        _mode(broken, "budgeted")["actions_match_rule"] = False
        findings = checks(broken)
        self.assertTrue(any("actions" in f for f in findings), findings)

    def test_a_changed_step_count_is_named(self):
        broken = {"cases": [dict(c) for c in self.report["cases"]]}
        _mode(broken, "budgeted")["steps"] = 99
        findings = checks(broken)
        self.assertTrue(any("steps" in f for f in findings), findings)

    def test_a_cap_that_trims_nothing_is_named(self):
        broken = {"cases": [dict(c) for c in self.report["cases"]]}
        uncapped = _mode(broken, "uncapped")
        _mode(broken, "budgeted")["prompt_max_tokens"] = \
            uncapped["prompt_max_tokens"]
        _mode(broken, "budgeted")["prompt_omitted_total"] = 0
        findings = checks(broken)
        self.assertTrue(any("trim" in f or "omitted" in f for f in findings),
                        findings)

    def test_a_missing_mode_is_named(self):
        broken = {"cases": [c for c in self.report["cases"]
                            if c["mode"] != "budgeted"]}
        findings = checks(broken)
        self.assertTrue(any("missing" in f for f in findings), findings)

    def test_lost_reward_is_named(self):
        broken = {"cases": [dict(c) for c in self.report["cases"]]}
        _mode(broken, "budgeted")["reward"] = 0.0
        findings = checks(broken)
        self.assertTrue(any("reward" in f for f in findings), findings)


if __name__ == "__main__":
    unittest.main()
