"""A battery must fail loudly, not merely print.

Ten shipped batteries have no ``assert``, ``raise`` or non-zero exit, so a
scripted gate cannot tell a healthy run from a regressed one without a
human reading the JSON. Measured: ``python -m evals.telemetry_lock`` exits
0 both intact and with ``--ablate`` (the deliberately broken case).

``evals/battery_check.py`` gives batteries one shared contract: a finding
list drives the exit code, so 0 means "every claim held" and 1 means "a
claim failed". These tests pin the contract and the honesty of the audit
that lists which batteries do not use it.
"""

import os
import subprocess
import sys
import tempfile
import unittest

from evals.battery_check import (
    audit_batteries,
    battery_result,
    exit_code_for,
    format_findings,
)

BRAIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestBatteryContract(unittest.TestCase):
    def test_no_findings_is_success(self):
        self.assertEqual(exit_code_for([]), 0)

    def test_any_finding_is_failure(self):
        self.assertEqual(exit_code_for(["chain-broken"]), 1)
        self.assertEqual(exit_code_for(["a", "b"]), 1)

    def test_result_carries_ok_and_findings(self):
        result = battery_result("telemetry_lock", ["chain-broken"], {"n": 1})
        self.assertFalse(result["ok"])
        self.assertEqual(result["findings"], ["chain-broken"])
        self.assertEqual(result["battery"], "telemetry_lock")
        self.assertEqual(result["payload"], {"n": 1})
        self.assertEqual(exit_code_for(result["findings"]), 1)

    def test_result_without_findings_is_ok(self):
        result = battery_result("telemetry_lock", [], {"n": 1})
        self.assertTrue(result["ok"])
        self.assertEqual(exit_code_for(result["findings"]), 0)

    def test_format_findings_is_one_line_each(self):
        text = format_findings("x", ["first", "second"])
        lines = [line for line in text.splitlines() if line.strip()]
        self.assertEqual(len(lines), 2)
        self.assertTrue(all("x" in line for line in lines))
        self.assertIn("first", text)

    def test_a_battery_exits_non_zero_when_it_reports_a_finding(self):
        # Drive the contract end to end through a subprocess.
        script = (
            "import sys\n"
            "from evals.battery_check import battery_result, exit_code_for\n"
            "r = battery_result('demo', ['claim-failed'], {})\n"
            "sys.exit(exit_code_for(r['findings']))\n"
        )
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "demo.py")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(script)
            proc = subprocess.run([sys.executable, path], cwd=BRAIN,
                                  capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 1, proc.stderr)


class TestBatteryAudit(unittest.TestCase):
    def test_audit_reports_the_shipped_batteries(self):
        report = audit_batteries(BRAIN)
        # telemetry_lock adopted the contract this cycle: it now fails loudly.
        self.assertIn("telemetry_lock", report["with_contract"])
        self.assertIn("contract", report)
        self.assertGreater(report["total"], 20)

    def test_audit_still_names_the_uncovered_batteries(self):
        # The audit is only useful while it keeps naming the gap.
        report = audit_batteries(BRAIN)
        self.assertTrue(report["without_contract"])
        for name in ("calibration", "estimators", "recompute"):
            self.assertIn(name, report["without_contract"])

    def test_audit_finds_both_populations(self):
        report = audit_batteries(BRAIN)
        # Some batteries already refuse malformed input, so they are counted.
        self.assertTrue(report["with_contract"])
        self.assertTrue(report["without_contract"])
        self.assertEqual(
            len(report["with_contract"]) + len(report["without_contract"]),
            report["total"])

    def test_audit_of_a_missing_directory_degrades(self):
        report = audit_batteries(os.path.join(BRAIN, "no-such-dir"))
        self.assertEqual(report["total"], 0)
        self.assertEqual(report["without_contract"], [])


if __name__ == "__main__":
    unittest.main()
