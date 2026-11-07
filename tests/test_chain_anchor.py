"""Terminal telemetry anchor: a truncated tail must not read back as valid.

Failing-first: verify_chain validates internal links only, so deleting
trailing records leaves a valid prefix and returns ok=true. The anchor
is a separate head+count witness written after the run; anchored
verification reports truncated-tail when the log is shorter than the
witness. The anchor-off control documents the residual exposure.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

from telemetry.log import Telemetry, verify_chain, write_anchor


def _log(path, records=5):
    tel = Telemetry(path)
    for index in range(records):
        tel.append_action(index, "step", {"i": index})
    return tel


def _truncate(path, keep=3):
    lines = Path(path).read_text(encoding="utf-8").splitlines(True)
    Path(path).write_text("".join(lines[:keep]), encoding="utf-8")


class TestChainAnchor(unittest.TestCase):
    def test_intact_log_passes_with_anchor(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            tel = _log(path, 5)
            anchor_path = tel.write_anchor()
            result = verify_chain(path, anchor_path=anchor_path)
        self.assertTrue(result["ok"])
        self.assertEqual(result["records"], 5)
        self.assertEqual(result["findings"], [])

    def test_truncated_tail_detected_with_anchor(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            tel = _log(path, 5)
            anchor_path = tel.write_anchor()
            _truncate(path, 3)
            result = verify_chain(path, anchor_path=anchor_path)
        self.assertFalse(result["ok"])
        self.assertEqual(result["records"], 3)
        self.assertTrue(any(finding.startswith("truncated-tail")
                            for finding in result["findings"]))

    def test_anchor_off_leaves_truncation_undetected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            _log(path, 5)
            _truncate(path, 3)
            result = verify_chain(path)
        self.assertTrue(result["ok"])
        self.assertEqual(result["records"], 3)

    def test_missing_anchor_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            _log(path, 5)
            result = verify_chain(path, anchor_path=path + ".anchor")
        self.assertFalse(result["ok"])
        self.assertIn("missing-anchor", result["findings"])

    def test_anchor_mismatch_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            tel = _log(path, 5)
            anchor_path = tel.write_anchor()
            anchor = json.loads(Path(anchor_path).read_text(encoding="utf-8"))
            anchor["head"] = "0" * 64
            Path(anchor_path).write_text(json.dumps(anchor), encoding="utf-8")
            result = verify_chain(path, anchor_path=anchor_path)
        self.assertFalse(result["ok"])
        self.assertIn("anchor-mismatch", result["findings"])

    def test_anchor_write_is_atomic_and_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            tel = _log(path, 3)
            first = Path(tel.write_anchor()).read_text(encoding="utf-8")
            second = Path(tel.write_anchor()).read_text(encoding="utf-8")
            leftovers = [name for name in os.listdir(tmp) if name.endswith(".tmp")]
        self.assertEqual(first, second)
        self.assertEqual(leftovers, [])

    def test_write_anchor_helper_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            tel = _log(path, 2)
            records = tel.read_all()
            anchor_path = write_anchor(path, records[-1]["digest"], len(records))
            result = verify_chain(path, anchor_path=anchor_path)
        self.assertTrue(result["ok"])
        self.assertEqual(result["records"], 2)


if __name__ == "__main__":
    unittest.main()
