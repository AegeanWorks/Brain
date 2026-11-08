"""Calibration forecast journal: append-only, checksummed, cross-run.

Failing-first: calibration.summary scores only the forecasts present in
one process, and SelfModel.calibration() reads the current episode lists.
Forecasts are immutable observations, so the journal appends one
checksummed JSONL record per forecast, restores them, and thereby lets
two runs aggregate to ten resolved forecasts.
"""

import hashlib
import json
import os
import tempfile
import time
import unittest
from pathlib import Path

from calibration import summary
from calibration_store import (_record_digest, append_forecasts,
                               load_all_forecasts, load_forecasts,
                               rotate_forecast_journal,
                               verify_forecast_file)

AT = "2026-11-07T00:00:00Z"

FIRST = (
    ("run1:0", 0.9, 1), ("run1:1", 0.8, 1), ("run1:2", 0.7, 0),
    ("run1:3", 0.6, 1), ("run1:4", 0.5, 0), ("run1:5", 0.4, 0),
)
SECOND = (
    ("run2:0", 0.8, 1), ("run2:1", 0.7, 1),
    ("run2:2", 0.2, 0), ("run2:3", 0.1, 0),
)


def _forecasts(rows):
    return [{"id": identifier, "probability": probability,
             "outcome": outcome} for identifier, probability, outcome in rows]


class TestCalibrationStore(unittest.TestCase):
    def test_append_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            report = append_forecasts(_forecasts(FIRST), path, at=AT)
            loaded = load_forecasts(path)
            verified = verify_forecast_file(path)
            stats = summary(loaded, min_resolved=6)
        self.assertEqual(report["appended"], 6)
        self.assertEqual(report["records"], 6)
        self.assertEqual(report["resolved"], 6)
        self.assertEqual(len(loaded), 6)
        self.assertEqual(loaded[0]["at"], AT)
        self.assertEqual(len(loaded[0]["sha256"]), 64)
        self.assertTrue(verified["ok"], verified["findings"])
        self.assertEqual(verified["resolved"], 6)
        self.assertEqual(verified["ignored"], 0)
        self.assertAlmostEqual(stats["brier"], 0.185, places=6)
        self.assertAlmostEqual(stats["skill"], 0.26, places=6)

    def test_two_runs_aggregate_to_ten(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            append_forecasts(_forecasts(FIRST), path, at=AT)
            append_forecasts(_forecasts(SECOND), path, at=AT)
            loaded = load_forecasts(path)
            verified = verify_forecast_file(path)
            stats = summary(loaded, min_resolved=10)
        self.assertEqual(len(loaded), 10)
        self.assertEqual(verified["records"], 10)
        self.assertEqual(verified["resolved"], 10)
        self.assertEqual(stats["counts"]["resolved"], 10)
        self.assertAlmostEqual(stats["brier"], 0.129, places=6)
        self.assertAlmostEqual(stats["skill"], 0.484, places=6)
        self.assertFalse(any("descriptive below" in warning
                             for warning in stats["warnings"]))
        self.assertTrue(any("bin" in warning
                            for warning in stats["warnings"]))

    def test_duplicate_id_refused_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            append_forecasts(_forecasts(FIRST[:1]), path, at=AT)
            before = Path(path).read_bytes()
            with self.assertRaises(ValueError):
                append_forecasts(_forecasts(FIRST[:1]), path, at=AT)
            after = Path(path).read_bytes()
            loaded = load_forecasts(path)
        self.assertEqual(before, after)
        self.assertEqual(len(loaded), 1)

    def test_duplicate_within_batch_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            batch = _forecasts(FIRST[:1]) + _forecasts(FIRST[:1])
            with self.assertRaises(ValueError):
                append_forecasts(batch, path, at=AT)
            exists = Path(path).exists()
        self.assertFalse(exists)

    def test_invalid_batch_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            batch = _forecasts(FIRST[:1]) + [
                {"id": "bad", "probability": 1.1, "outcome": 1}]
            with self.assertRaises(ValueError):
                append_forecasts(batch, path, at=AT)
            exists = Path(path).exists()
        self.assertFalse(exists)

    def test_tampered_record_fails_verify_and_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            append_forecasts(_forecasts(FIRST[:1]), path, at=AT)
            record = json.loads(Path(path).read_text(encoding="utf-8"))
            record["probability"] = 0.1
            Path(path).write_text(json.dumps(record) + "\n", encoding="utf-8")
            verified = verify_forecast_file(path)
            with self.assertRaises(ValueError):
                load_forecasts(path)
        self.assertFalse(verified["ok"])
        self.assertTrue(any("checksum" in finding
                            for finding in verified["findings"]))

    def test_corrupt_line_names_the_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            append_forecasts(_forecasts(FIRST[:1]), path, at=AT)
            with open(path, "a", encoding="utf-8") as handle:
                handle.write("{bad json\n")
            verified = verify_forecast_file(path)
            with self.assertRaises(ValueError):
                load_forecasts(path)
        self.assertFalse(verified["ok"])
        self.assertTrue(any("line 2" in finding
                            for finding in verified["findings"]))

    def test_keyed_journal_roundtrip_and_wrong_key(self):
        key = hashlib.sha256(b"calibration-eval-key").digest()
        wrong = hashlib.sha256(b"calibration-eval-wrong").digest()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            report = append_forecasts(_forecasts(FIRST), path, at=AT,
                                      hmac_key=key)
            loaded = load_forecasts(path, hmac_key=key)
            verified = verify_forecast_file(path, hmac_key=key)
            unkeyed = load_forecasts(path)
            with self.assertRaises(ValueError):
                load_forecasts(path, hmac_key=wrong)
            wrong_verified = verify_forecast_file(path, hmac_key=wrong)
        self.assertTrue(report["hmac"])
        self.assertEqual(len(loaded), 6)
        self.assertTrue(verified["ok"], verified["findings"])
        self.assertTrue(verified["hmac"])
        self.assertEqual(len(unkeyed), 6)
        self.assertFalse(wrong_verified["ok"])
        self.assertTrue(any("mac" in finding.lower()
                            for finding in wrong_verified["findings"]))

    def test_keyed_journal_requires_macs(self):
        key = hashlib.sha256(b"calibration-eval-key").digest()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            append_forecasts(_forecasts(FIRST), path, at=AT)
            with self.assertRaises(ValueError):
                load_forecasts(path, hmac_key=key)
            verified = verify_forecast_file(path, hmac_key=key)
        self.assertFalse(verified["ok"])
        self.assertTrue(any("missing its mac" in finding.lower()
                            for finding in verified["findings"]))

    def test_keyed_journal_detects_recomputed_checksum(self):
        key = hashlib.sha256(b"calibration-eval-key").digest()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            append_forecasts(_forecasts(FIRST), path, at=AT, hmac_key=key)
            records = [json.loads(line) for line in
                       Path(path).read_text(encoding="utf-8").splitlines()]
            records[0]["probability"] = 0.1
            records[0]["sha256"] = _record_digest(records[0])
            Path(path).write_text(
                "".join(json.dumps(record, sort_keys=True) + "\n"
                        for record in records), encoding="utf-8")
            verified = verify_forecast_file(path, hmac_key=key)
            with self.assertRaises(ValueError):
                load_forecasts(path, hmac_key=key)
        self.assertFalse(verified["ok"])
        self.assertTrue(any("mac" in finding.lower()
                            for finding in verified["findings"]))

    def test_keyed_rotation_preserves_records_and_score(self):
        key = hashlib.sha256(b"calibration-eval-key").digest()
        wrong = hashlib.sha256(b"calibration-eval-wrong").digest()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            rows = FIRST + SECOND
            before = summary(_forecasts(rows), min_resolved=1)
            append_forecasts(_forecasts(rows), path, at=AT, keep_recent=6,
                             hmac_key=key)
            combined = load_all_forecasts(path, hmac_key=key)
            after = summary(combined, min_resolved=1)
            before_bytes = Path(path).read_bytes()
            with self.assertRaises(ValueError):
                rotate_forecast_journal(path, keep_recent=6,
                                        hmac_key=wrong)
            after_bytes = Path(path).read_bytes()
        self.assertEqual(len(combined), 10)
        self.assertAlmostEqual(before["brier"], after["brier"], places=6)
        self.assertEqual(before_bytes, after_bytes)

    def test_invalid_hmac_key_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            for value in ("text", b"", 3):
                with self.assertRaises(ValueError):
                    append_forecasts(_forecasts(FIRST[:1]), path, at=AT,
                                     hmac_key=value)
                with self.assertRaises(ValueError):
                    load_forecasts(path, hmac_key=value)

    def test_missing_store_is_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            loaded = load_forecasts(path)
            verified = verify_forecast_file(path)
        self.assertEqual(loaded, [])
        self.assertTrue(verified["ok"])
        self.assertEqual(verified["records"], 0)
        self.assertEqual(verified["findings"], [])

    def test_unresolved_outcome_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            append_forecasts([{"id": "u:0", "probability": 0.5,
                               "outcome": None}], path, at=AT)
            verified = verify_forecast_file(path)
            stats = summary(load_forecasts(path), min_resolved=1)
        self.assertEqual(verified["resolved"], 0)
        self.assertEqual(verified["ignored"], 1)
        self.assertEqual(stats["counts"]["ignored"], 1)

    def test_stale_lock_is_stolen(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            lock = Path(path + ".lock")
            lock.write_text("1:1\n", encoding="utf-8")
            old = time.time() - 60
            os.utime(lock, (old, old))
            append_forecasts(_forecasts(FIRST[:1]), path, at=AT)
            lock_exists = lock.exists()
            verified = verify_forecast_file(path)
        self.assertFalse(lock_exists)
        self.assertTrue(verified["ok"])

    def test_fresh_lock_times_out_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            lock = Path(path + ".lock")
            lock.write_text("1:1\n", encoding="utf-8")
            with self.assertRaises(TimeoutError):
                append_forecasts(_forecasts(FIRST[:1]), path, at=AT,
                                 lock_timeout=0.0)
            exists = Path(path).exists()
        self.assertFalse(exists)

    def test_empty_append_is_a_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            report = append_forecasts([], path, at=AT)
            exists = Path(path).exists()
        self.assertEqual(report["appended"], 0)
        self.assertFalse(exists)

    def test_invalid_inputs_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            invalid = (
                [{"probability": 0.5, "outcome": 1}],
                [{"id": "", "probability": 0.5, "outcome": 1}],
                [{"id": "a", "probability": True, "outcome": 1}],
                [{"id": "a", "probability": 0.5, "outcome": 2}],
                [{"id": "a", "probability": 0.5, "outcome": True}],
                [{"id": "a", "probability": 0.5, "outcome": 1, "x": 1}],
                [{"id": "a", "probability": 0.5, "outcome": 1, "at": 3}],
            )
            for batch in invalid:
                with self.assertRaises(ValueError):
                    append_forecasts(batch, path, at=AT)
            with self.assertRaises(ValueError):
                append_forecasts(_forecasts(FIRST[:1]), path, at=AT,
                                 lock_timeout=-1)
        self.assertFalse(Path(path).exists())


if __name__ == "__main__":
    unittest.main()
