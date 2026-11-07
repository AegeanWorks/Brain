"""Optional HMAC-signed telemetry: keyed records and tamper findings.

The chain alone can be recomputed by an attacker. With ``hmac_key`` the
writer signs each record with HMAC-SHA256 over its canonical bytes, and
the verifier reports a missing or bad MAC. Unkeyed logs and their bytes
must stay unchanged. Test keys are derived here, never read from the
environment or a repository file.
"""

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from telemetry.log import Telemetry, _digest_of, verify_chain

KEY = hashlib.sha256(b"brain-hmac-test-key").digest()
WRONG = hashlib.sha256(b"brain-hmac-wrong-key").digest()


def _build(path, key=KEY):
    tel = Telemetry(path, hmac_key=key)
    tel.write_header("T3_navigate", 200, policy="mac-test")
    for index in range(3):
        tel.append_action(index, "step", {"i": index})
        tel.append_result(index, True, "step", 1.0)
    tel.write_verdict("done", "steps=3 reward=1.0")
    return tel


class TestTelemetryMac(unittest.TestCase):
    def test_keyed_records_verify_with_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            _build(path)
            records = Telemetry(path).read_all()
            result = verify_chain(path, hmac_key=KEY)
            unkeyed = verify_chain(path)
        self.assertEqual(len(records), 8)
        self.assertTrue(all(isinstance(record.get("mac"), str)
                            for record in records))
        self.assertTrue(result["ok"], result["findings"])
        self.assertTrue(unkeyed["ok"])

    def test_wrong_key_reports_bad_mac(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            _build(path)
            result = verify_chain(path, hmac_key=WRONG)
        self.assertFalse(result["ok"])
        self.assertTrue(any(finding.startswith("bad-mac:0")
                            for finding in result["findings"]))

    def test_missing_mac_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            _build(path)
            lines = Path(path).read_text(encoding="utf-8").splitlines(True)
            record = json.loads(lines[0])
            record.pop("mac")
            lines[0] = json.dumps(record, sort_keys=True) + "\n"
            Path(path).write_text("".join(lines), encoding="utf-8")
            result = verify_chain(path, hmac_key=KEY)
        self.assertFalse(result["ok"])
        self.assertTrue(any(finding.startswith("missing-mac:0")
                            for finding in result["findings"]))

    def test_tampered_payload_with_recomputed_digest_reports_bad_mac(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            _build(path)
            lines = Path(path).read_text(encoding="utf-8").splitlines(True)
            record = json.loads(lines[0])
            record["task"] = "tampered"
            record["digest"] = _digest_of(record)
            lines[0] = json.dumps(record, sort_keys=True) + "\n"
            Path(path).write_text("".join(lines), encoding="utf-8")
            result = verify_chain(path, hmac_key=KEY)
        self.assertFalse(result["ok"])
        self.assertTrue(any(finding.startswith("bad-mac:0")
                            for finding in result["findings"]))

    def test_unkeyed_log_with_key_reports_missing_mac(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            _build(path, key=None)
            records = Telemetry(path).read_all()
            result = verify_chain(path, hmac_key=KEY)
            unkeyed = verify_chain(path)
        self.assertFalse(any("mac" in record for record in records))
        self.assertTrue(unkeyed["ok"])
        self.assertFalse(result["ok"])
        self.assertTrue(any(finding.startswith("missing-mac:0")
                            for finding in result["findings"]))

    def test_invalid_hmac_key_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            with self.assertRaises(ValueError):
                Telemetry(path, hmac_key="text")
            _build(path)
            with self.assertRaises(ValueError):
                verify_chain(path, hmac_key="text")


if __name__ == "__main__":
    unittest.main()
