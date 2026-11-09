"""The resume-identity battery must enforce its own identity claims.

``evals/resume_identity.py`` computes six claims and prints them: a rerun
with the same task/seed/config resumes with the same digest, a changed seed
or target starts a new episode, volatile keys are ignored, a legacy episode
asks, and a policy-any request resumes. It exited 0 either way, so a change
that made a changed seed resume, or a volatile key alter the digest, only
altered the printed JSON.

Measured: same -> resume, changed-seed -> new, changed-target -> new,
volatile -> resume, legacy -> ask, policy-any -> resume; headers match the
digests, reruns share an episode digest and actions, and a different seed
differs (13 vs 6 steps).
"""

import unittest

from evals.resume_identity import MODES, checks, run_battery

#: The decision each mode must produce.
EXPECTED = {
    "same": ("resume", True),
    "changed-seed": ("new", False),
    "changed-target": ("new", False),
    "volatile": ("resume", True),
    "legacy": ("ask", False),
    "policy-any": ("resume", False),
}


def _case(report, mode):
    for case in report["cases"]:
        if case["mode"] == mode:
            return case
    raise AssertionError("mode missing: %s" % mode)


class TestResumeIdentityChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = run_battery()

    def test_a_real_run_has_no_findings(self):
        self.assertEqual(checks(self.report), [])

    def test_every_mode_produces_its_documented_decision(self):
        for mode in MODES:
            decision, same = EXPECTED[mode]
            case = _case(self.report, mode)
            self.assertEqual(case["decision"], decision, mode)
            self.assertEqual(case["same_digest"], same, mode)

    def test_volatile_keys_do_not_change_the_digest(self):
        base = _case(self.report, "same")["base_sha256"]
        volatile = _case(self.report, "volatile")
        self.assertEqual(volatile["second_sha256"], base)

    def test_a_changed_seed_changes_the_digest(self):
        case = _case(self.report, "changed-seed")
        self.assertNotEqual(case["second_sha256"], case["base_sha256"])

    def test_a_changed_target_changes_the_digest(self):
        case = _case(self.report, "changed-target")
        self.assertNotEqual(case["second_sha256"], case["base_sha256"])

    def test_header_matches_the_digest_and_reruns_agree(self):
        for mode in ("same", "changed-seed"):
            case = _case(self.report, mode)
            headers = case["headers"]
            self.assertTrue(case["header_matches_digest"], mode)
            self.assertTrue(headers["first_equals_again"], mode)
            self.assertTrue(headers["actions_identical"], mode)
            self.assertNotEqual(headers["first_steps"],
                                headers["other_steps"], mode)

    def test_a_changed_seed_that_resumes_is_named(self):
        broken = {"cases": [dict(c) for c in self.report["cases"]]}
        _case(broken, "changed-seed")["decision"] = "resume"
        findings = checks(broken)
        self.assertTrue(any("decision" in f for f in findings), findings)

    def test_a_volatile_key_that_moves_the_digest_is_named(self):
        broken = {"cases": [dict(c) for c in self.report["cases"]]}
        base = _case(broken, "same")["base_sha256"]
        _case(broken, "volatile")["second_sha256"] = "f" * 64
        self.assertNotEqual(_case(broken, "volatile")["second_sha256"], base)
        findings = checks(broken)
        self.assertTrue(any("volatile" in f for f in findings), findings)

    def test_a_header_that_disagrees_is_named(self):
        broken = {"cases": [dict(c) for c in self.report["cases"]]}
        _case(broken, "same")["header_matches_digest"] = False
        findings = checks(broken)
        self.assertTrue(any("header" in f for f in findings), findings)

    def test_a_missing_mode_is_named(self):
        broken = {"cases": [c for c in self.report["cases"]
                            if c["mode"] != "legacy"]}
        findings = checks(broken)
        self.assertTrue(any("missing" in f for f in findings), findings)


if __name__ == "__main__":
    unittest.main()
