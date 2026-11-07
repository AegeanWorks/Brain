"""Tamper-evident telemetry: hash-chain probes.

Transferred idea: Assay hash-chained evidence ledger + retrospective
review. Every record links prev->digest; verify_chain names the
defect (edited / deleted / reordered / unchained / corrupt) instead
of reading a hand-edited log back silently.
"""

import json
import os
import tempfile
import unittest

from telemetry.log import Telemetry, verify_chain


def _write_fixture(path):
    tel = Telemetry(path)
    tel.write_header("task-a", 10)
    tel.append_action(1, "exec", {"cmd": "x"})
    tel.append_result(1, True, "ok", 1.5)
    return tel


def _lines(path):
    with open(path, "r", encoding="utf-8") as f:
        return [ln for ln in f if ln.strip()]


def _rewrite(path, lines):
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)


class TestChain(unittest.TestCase):
    def test_intact_chain_verifies(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "t.jsonl")
            _write_fixture(path)
            result = verify_chain(path)
            self.assertTrue(result["ok"])
            self.assertEqual(result["findings"], [])
            self.assertEqual(result["records"], 3)
            rows = Telemetry(path).read_all()
            self.assertEqual(result["head"], rows[-1]["digest"])
            self.assertEqual(rows[0]["prev"], "GENESIS")
            self.assertEqual(rows[1]["prev"], rows[0]["digest"])
            self.assertEqual(rows[2]["prev"], rows[1]["digest"])

    def test_edited_record_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "t.jsonl")
            _write_fixture(path)
            lines = _lines(path)
            obj = json.loads(lines[1])
            obj["args"] = {"cmd": "rm -rf /"}
            lines[1] = json.dumps(obj, sort_keys=True) + "\n"
            _rewrite(path, lines)
            result = verify_chain(path)
            self.assertFalse(result["ok"])
            self.assertIn("edited-record:1", result["findings"])

    def test_deleted_record_breaks_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "t.jsonl")
            _write_fixture(path)
            lines = _lines(path)
            _rewrite(path, [lines[0], lines[2]])
            result = verify_chain(path)
            self.assertFalse(result["ok"])
            self.assertTrue(any(f.startswith("broken-link")
                                for f in result["findings"]))

    def test_reordered_records_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "t.jsonl")
            _write_fixture(path)
            lines = _lines(path)
            _rewrite(path, [lines[0], lines[2], lines[1]])
            result = verify_chain(path)
            self.assertFalse(result["ok"])
            self.assertTrue(any(f.startswith("reordered-record")
                                for f in result["findings"]))

    def test_legacy_unchained_record_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "t.jsonl")
            with open(path, "w", encoding="utf-8") as f:
                f.write(json.dumps({"schema": 2, "seq": 0, "type": "header",
                                    "ts": 0.0, "M": None, "P": None,
                                    "S": None, "hub": None},
                                   sort_keys=True) + "\n")
            result = verify_chain(path)
            self.assertFalse(result["ok"])
            self.assertIn("unchained-record:0", result["findings"])

    def test_corrupt_line_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "t.jsonl")
            _write_fixture(path)
            lines = _lines(path)
            lines.insert(1, "{not json\n")
            _rewrite(path, lines)
            result = verify_chain(path)
            self.assertFalse(result["ok"])
            self.assertIn("corrupt-line:1", result["findings"])


if __name__ == "__main__":
    unittest.main()
