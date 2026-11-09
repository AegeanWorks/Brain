"""The progress-guard battery must check its own documented claims.

``evals/progress_guard.py`` states exact numbers in its docstring: the guard
cuts T3:15 33 -> 13 steps, T3:65 26 -> 6, T2:3 34 -> 8, with calls 21 -> 13
/ 6 / 8 under the guard and 4 / 4 / 3 under the skip, while T1 stays 36
steps / 22 calls. Before this the battery printed those numbers and exited
0 either way, so a planner regression that changed them was invisible to a
scripted gate.

``checks(report)`` compares the run against a pre-registered expectation
table and returns a finding per disagreement.
"""

import unittest

from evals.progress_guard import CASES, MODES, checks, run_battery


def _case(report, mode, task, seed):
    for case in report["cases"]:
        if (case["mode"], case["task"], case["seed"]) == (mode, task, seed):
            return case
    raise AssertionError("case missing: %s %s:%s" % (mode, task, seed))


class TestProgressGuardChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = run_battery()

    def test_a_real_run_has_no_findings(self):
        self.assertEqual(checks(self.report), [])

    def test_every_documented_number_is_pinned(self):
        # guard-off -> guard-on step counts from the docstring.
        expect = {("T3_navigate", 15): (33, 13),
                  ("T3_navigate", 65): (26, 6),
                  ("T2_delayed_match", 3): (34, 8),
                  ("T1_forage", 71): (36, 36)}
        for (task, seed), (off, on) in expect.items():
            self.assertEqual(
                _case(self.report, "guard-off", task, seed)["steps"], off,
                "%s:%d guard-off" % (task, seed))
            self.assertEqual(
                _case(self.report, "guard-on", task, seed)["steps"], on,
                "%s:%d guard-on" % (task, seed))

    def test_call_counts_are_pinned(self):
        expect = {("T3_navigate", 15): (21, 13, 4),
                  ("T3_navigate", 65): (21, 6, 4),
                  ("T2_delayed_match", 3): (21, 8, 3),
                  ("T1_forage", 71): (22, 22, 22)}
        for (task, seed), (off, on, skip) in expect.items():
            for mode, want in (("guard-off", off), ("guard-on", on),
                               ("skip-on", skip)):
                self.assertEqual(
                    _case(self.report, mode, task, seed)["backend_calls"],
                    want, "%s:%d %s" % (task, seed, mode))

    def test_rewards_are_identical_across_modes(self):
        for task, seed in CASES:
            rewards = {_case(self.report, mode, task, seed)["reward"]
                       for mode in MODES}
            self.assertEqual(len(rewards), 1,
                             "%s:%d rewards %s" % (task, seed, rewards))

    def test_a_changed_step_count_is_named(self):
        broken = {"cases": [dict(c) for c in self.report["cases"]]}
        _case(broken, "guard-on", "T3_navigate", 15)["steps"] = 99
        findings = checks(broken)
        self.assertTrue(any("steps" in f for f in findings), findings)

    def test_a_changed_call_count_is_named(self):
        broken = {"cases": [dict(c) for c in self.report["cases"]]}
        _case(broken, "skip-on", "T3_navigate", 65)["backend_calls"] = 99
        findings = checks(broken)
        self.assertTrue(any("calls" in f for f in findings), findings)

    def test_a_lost_reward_is_named(self):
        broken = {"cases": [dict(c) for c in self.report["cases"]]}
        _case(broken, "guard-on", "T2_delayed_match", 3)["reward"] = 0.0
        findings = checks(broken)
        self.assertTrue(any("reward" in f for f in findings), findings)

    def test_a_vanished_guard_is_named(self):
        # If the guard stops rejecting, guard-on and guard-off stop differing:
        # the audit compares them rather than trusting either alone.
        broken = {"cases": [dict(c) for c in self.report["cases"]]}
        off = _case(broken, "guard-off", "T3_navigate", 15)
        on = _case(broken, "guard-on", "T3_navigate", 15)
        on["steps"] = off["steps"]
        on["progress_rejections"] = 0
        findings = checks(broken)
        self.assertTrue(any("guard" in f for f in findings), findings)

    def test_missing_case_is_named(self):
        broken = {"cases": [c for c in self.report["cases"]
                            if not (c["mode"] == "skip-on"
                                    and c["task"] == "T1_forage")]}
        findings = checks(broken)
        self.assertTrue(any("missing" in f for f in findings), findings)


if __name__ == "__main__":
    unittest.main()
