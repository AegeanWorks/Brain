"""The header-reader battery must check its own memory claim.

``evals/header_reader.py`` exists to prove one property: reading only
headers costs a small fixed memory instead of retaining every action. The
README states it as 100k records at 0.1 MB peak versus 124.2 MB, and the
battery printed those numbers and exited 0 either way, so a change that
made ``read_headers`` accumulate would only alter the printed JSON.

``checks(report)`` compares the two modes on the property, not on exact
bytes: the header reader must return exactly the header count, retain far
less than the full reader, and both must see the same headers. A ratio
floor keeps the test stable against allocator noise.
"""

import unittest

from evals.header_reader import RECORDS, checks, run_battery

#: The header reader must use at least this many times less peak memory.
MIN_RATIO = 10.0


def _mode(report, name):
    for case in report["cases"]:
        if case["mode"] == name:
            return case
    raise AssertionError("mode missing: %s" % name)


class TestHeaderReaderChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = run_battery()

    def test_a_real_run_has_no_findings(self):
        self.assertEqual(checks(self.report), [])

    def test_header_mode_returns_only_headers(self):
        headers = _mode(self.report, "headers")
        self.assertEqual(headers["returned"], 1)
        self.assertEqual(headers["headers"], 1)
        self.assertEqual(headers["lines"], RECORDS + 1)

    def test_all_mode_retains_every_record(self):
        everything = _mode(self.report, "all")
        self.assertEqual(everything["returned"], RECORDS + 1)
        self.assertEqual(everything["headers"], 1)

    def test_header_mode_retains_far_less(self):
        everything = _mode(self.report, "all")
        headers = _mode(self.report, "headers")
        ratio = everything["peak_bytes"] / max(headers["peak_bytes"], 1)
        self.assertGreater(ratio, MIN_RATIO, "ratio %.1fx" % ratio)

    def test_both_modes_see_the_same_headers(self):
        self.assertEqual(_mode(self.report, "all")["headers"],
                         _mode(self.report, "headers")["headers"])

    def test_a_header_reader_that_retains_everything_is_named(self):
        broken = {"cases": [dict(c) for c in self.report["cases"]]}
        _mode(broken, "headers")["peak_bytes"] = \
            _mode(broken, "all")["peak_bytes"]
        findings = checks(broken)
        self.assertTrue(any("memory" in f or "ratio" in f for f in findings),
                        findings)

    def test_a_header_reader_that_returns_everything_is_named(self):
        broken = {"cases": [dict(c) for c in self.report["cases"]]}
        _mode(broken, "headers")["returned"] = RECORDS + 1
        findings = checks(broken)
        self.assertTrue(any("returned" in f for f in findings), findings)

    def test_a_lost_header_is_named(self):
        broken = {"cases": [dict(c) for c in self.report["cases"]]}
        _mode(broken, "headers")["headers"] = 0
        findings = checks(broken)
        self.assertTrue(any("headers" in f for f in findings), findings)

    def test_a_missing_mode_is_named(self):
        broken = {"cases": [c for c in self.report["cases"]
                            if c["mode"] != "headers"]}
        findings = checks(broken)
        self.assertTrue(any("missing" in f for f in findings), findings)


if __name__ == "__main__":
    unittest.main()
