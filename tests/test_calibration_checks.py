"""The calibration battery must check its own fixtures.

``evals/calibration.py`` runs six cases whose scores are known exactly by
construction — a perfect forecaster (Brier 0, skill 1), an inverted one
(Brier 1, skill -3), a calibrated set, a small sample, an ignored outcome
and the real T3:15 self-model readout. It printed them and exited 0 either
way, so a change to the scorer that moved a known score only altered the
JSON.

Measured: perfect 0.0/1.0, calibrated 0.166/0.308333, inverted 1.0/-3.0,
small 0.0/None, ignored 0.04/0.84, run 0.005385/0.924167.

Re-baselined in ADR-140: the real-run case moved from 0.230769/-2.25 to
0.005385/0.924167 because the agent now records a confidence formed
*before* the action rather than `1.0 if reward > 0 else 0.5`. The old score
was a restatement of the base rate; the new one is a forecast.
"""

import unittest

from evals.calibration import checks, run_battery

#: Exact ``(brier, skill)`` each fixture must produce.
EXPECTED = {
    "perfect": (0.0, 1.0),
    "calibrated": (0.166, 0.308333),
    "inverted": (1.0, -3.0),
    "small": (0.0, None),
    "ignored": (0.04, 0.84),
    "run-T3-15": (0.005385, 0.924167),
}


def _case(report, mode):
    for case in report["cases"]:
        if case["mode"] == mode:
            return case
    raise AssertionError("mode missing: %s" % mode)


class TestCalibrationChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = run_battery()

    def test_a_real_run_has_no_findings(self):
        self.assertEqual(checks(self.report), [])

    def test_every_fixture_scores_as_documented(self):
        for mode, (brier, skill) in EXPECTED.items():
            stats = _case(self.report, mode)["stats"]
            self.assertAlmostEqual(stats["brier"], brier, places=6, msg=mode)
            if skill is None:
                self.assertIsNone(stats["skill"], mode)
            else:
                self.assertAlmostEqual(stats["skill"], skill, places=6,
                                       msg=mode)

    def test_perfect_beats_inverted(self):
        perfect = _case(self.report, "perfect")["stats"]
        inverted = _case(self.report, "inverted")["stats"]
        self.assertLess(perfect["brier"], inverted["brier"])
        self.assertGreater(perfect["skill"], inverted["skill"])

    def test_small_sample_warns_and_inverted_warns(self):
        for mode in ("small", "inverted"):
            stats = _case(self.report, mode)["stats"]
            self.assertTrue(stats["warnings"], mode)

    def test_the_real_run_keeps_its_pinned_score(self):
        case = _case(self.report, "run-T3-15")
        self.assertEqual(case["steps"], 13)
        self.assertEqual(case["reward"], 1.0)
        self.assertEqual(case["stats"]["counts"]["resolved"], 13)

    def test_a_moved_brier_is_named(self):
        broken = {"cases": [dict(c) for c in self.report["cases"]]}
        _case(broken, "perfect")["stats"] = dict(
            _case(broken, "perfect")["stats"], brier=0.5)
        findings = checks(broken)
        self.assertTrue(any("perfect" in f for f in findings), findings)

    def test_a_moved_skill_is_named(self):
        broken = {"cases": [dict(c) for c in self.report["cases"]]}
        _case(broken, "inverted")["stats"] = dict(
            _case(broken, "inverted")["stats"], skill=0.0)
        findings = checks(broken)
        self.assertTrue(any("inverted" in f for f in findings), findings)

    def test_a_suddenly_resolved_small_sample_is_named(self):
        broken = {"cases": [dict(c) for c in self.report["cases"]]}
        stats = dict(_case(broken, "small")["stats"])
        stats["skill"] = 1.0
        _case(broken, "small")["stats"] = stats
        findings = checks(broken)
        self.assertTrue(any("small" in f for f in findings), findings)

    def test_a_missing_mode_is_named(self):
        broken = {"cases": [c for c in self.report["cases"]
                            if c["mode"] != "run-T3-15"]}
        findings = checks(broken)
        self.assertTrue(any("missing" in f for f in findings), findings)


if __name__ == "__main__":
    unittest.main()
