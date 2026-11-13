"""The conformance battery must check its own controls.

`evals/backend_conformance.py` runs the contract over four controls and the
shipped registry. It printed them and exited 0 either way, so a widening of
the contract — accepting a non-deterministic provider, or a provider that
never declared an identity — would change nothing observable.

Pinned: conforming ok, alternating not ok (non-deterministic),
class-identity not ok (identity-from-class-name), returns-none not ok
(no-proposal), and the registry carries both `stub` and `llamacpp`.
"""

import unittest

from evals.backend_conformance import checks, measure


class TestBackendConformanceChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = measure()

    def test_a_clean_report_has_no_findings(self):
        self.assertEqual(checks(self.report), [])

    def test_the_conforming_control_passes(self):
        case = {c["subject"]: c for c in self.report["cases"]}["conforming"]
        self.assertTrue(case["ok"])
        self.assertTrue(case["deterministic"])

    def test_the_non_deterministic_control_is_named(self):
        case = {c["subject"]: c for c in self.report["cases"]}["alternating"]
        self.assertFalse(case["ok"])
        self.assertIn("non-deterministic", case["findings"])

    def test_the_class_identity_control_is_named(self):
        case = {c["subject"]: c
                for c in self.report["cases"]}["class-identity"]
        self.assertFalse(case["ok"])
        self.assertIn("identity-from-class-name", case["findings"])

    def test_the_no_proposal_control_is_named_once(self):
        case = {c["subject"]: c for c in self.report["cases"]}["returns-none"]
        self.assertFalse(case["ok"])
        self.assertEqual(case["findings"].count("no-proposal"), 1)

    def test_every_shipped_provider_is_registered(self):
        # llamacpp launches its own server, openai asks one already running,
        # stub replays a script: all three are shipped seams.
        self.assertEqual(self.report["registered"],
                         ["llamacpp", "openai", "stub"])

    def test_a_widened_contract_is_named(self):
        broken = {"cases": [dict(c) for c in self.report["cases"]],
                  "registered": list(self.report["registered"])}
        for case in broken["cases"]:
            if case["subject"] == "alternating":
                case["ok"] = True
        findings = checks(broken)
        self.assertTrue(any("alternating" in f for f in findings), findings)

    def test_a_missing_control_is_named(self):
        broken = {"cases": [c for c in self.report["cases"]
                            if c["subject"] != "returning-none"
                            and c["subject"] != "returns-none"],
                  "registered": list(self.report["registered"])}
        findings = checks(broken)
        self.assertTrue(any("missing" in f for f in findings), findings)

    def test_an_unregistered_provider_is_named(self):
        broken = {"cases": list(self.report["cases"]),
                  "registered": ["stub"]}
        findings = checks(broken)
        self.assertTrue(any("llamacpp" in f for f in findings), findings)


if __name__ == "__main__":
    unittest.main()
