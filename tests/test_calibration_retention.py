"""Calibration-journal retention: archive older forecasts, keep the newest.

Failing-first: the forecast journal grows without bound. Rotation must
keep the newest N records live, archive older records with their
per-record checksums, back the pre-rotation journal up, and preserve the
combined Brier/skill exactly. Short journals are no-ops; conflicting
archive ids and corrupt files are refused.
"""

import json
import os
import tempfile
import time
import unittest
from pathlib import Path

from calibration import summary
from calibration_store import (append_forecasts, load_all_forecasts,
                               load_forecasts, rotate_forecast_journal,
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
EXTRA = tuple(
    ("run3:%d" % index, 0.6 if index % 2 == 0 else 0.3,
     1 if index % 3 == 0 else 0)
    for index in range(9)
)
ALL = FIRST + SECOND + EXTRA


def _forecasts(rows):
    return [{"id": identifier, "probability": probability,
             "outcome": outcome} for identifier, probability, outcome in rows]


class TestCalibrationRetention(unittest.TestCase):
    def test_rotate_splits_and_preserves_score(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            append_forecasts(_forecasts(ALL), path, at=AT)
            before_records = load_forecasts(path)
            before = summary(before_records, min_resolved=10)
            report = rotate_forecast_journal(path, keep_recent=10)
            live = load_forecasts(path)
            archive_path = path + ".archive"
            archive = load_forecasts(archive_path)
            combined = load_all_forecasts(path)
            after = summary(combined, min_resolved=10)
            live_ok = verify_forecast_file(path)["ok"]
            archive_ok = verify_forecast_file(archive_path)["ok"]
            backup = load_forecasts(path + ".bak")
            meta = json.loads(Path(path + ".rotation").read_text(
                encoding="utf-8"))
        self.assertTrue(report["rotated"])
        self.assertEqual(report["source_records"], 19)
        self.assertEqual(report["archived"], 9)
        self.assertEqual(report["kept"], 10)
        self.assertEqual(len(live), 10)
        self.assertEqual(len(archive), 9)
        self.assertEqual(len(combined), 19)
        self.assertEqual(len({r["id"] for r in combined}), 19)
        self.assertEqual(before["counts"], after["counts"])
        self.assertAlmostEqual(before["brier"], after["brier"], places=6)
        self.assertAlmostEqual(before["skill"], after["skill"], places=6)
        self.assertTrue(live_ok)
        self.assertTrue(archive_ok)
        self.assertEqual(len(backup), 19)
        self.assertEqual(meta["source_records"], 19)
        self.assertEqual(meta["archived"], 9)
        self.assertEqual(meta["kept"], 10)
        self.assertEqual(meta["archive_records"], 9)

    def test_second_rotation_extends_the_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            append_forecasts(_forecasts(ALL), path, at=AT)
            rotate_forecast_journal(path, keep_recent=10)
            extra = [{"id": "run4:%d" % index, "probability": 0.5,
                      "outcome": index % 2} for index in range(6)]
            append_forecasts(extra, path, at=AT)
            report = rotate_forecast_journal(path, keep_recent=10)
            combined = load_all_forecasts(path)
            live = load_forecasts(path)
            archive = load_forecasts(path + ".archive")
        self.assertTrue(report["rotated"])
        self.assertEqual(report["source_records"], 16)
        self.assertEqual(report["archived"], 6)
        self.assertEqual(len(live), 10)
        self.assertEqual(len(archive), 15)
        self.assertEqual(len(combined), 25)
        self.assertEqual(len({r["id"] for r in combined}), 25)

    def test_short_journal_is_a_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            append_forecasts(_forecasts(FIRST[:5]), path, at=AT)
            report = rotate_forecast_journal(path, keep_recent=10)
            live = load_forecasts(path)
            archive_exists = Path(path + ".archive").exists()
            backup_exists = Path(path + ".bak").exists()
            meta_exists = Path(path + ".rotation").exists()
        self.assertFalse(report["rotated"])
        self.assertEqual(report["source_records"], 5)
        self.assertEqual(len(live), 5)
        self.assertFalse(archive_exists)
        self.assertFalse(backup_exists)
        self.assertFalse(meta_exists)

    def test_conflicting_archive_id_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            archive_path = path + ".archive"
            append_forecasts(_forecasts(ALL), path, at=AT)
            append_forecasts([{"id": "run1:0", "probability": 0.1,
                               "outcome": 0}], archive_path, at=AT)
            before = Path(path).read_bytes()
            with self.assertRaises(ValueError):
                rotate_forecast_journal(path, keep_recent=10)
            after = Path(path).read_bytes()
        self.assertEqual(before, after)

    def test_corrupt_live_or_archive_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            append_forecasts(_forecasts(ALL), path, at=AT)
            Path(path + ".archive").write_text("{bad\\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                rotate_forecast_journal(path, keep_recent=10)
            Path(path + ".archive").unlink()
            Path(path).write_text("{bad\\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                rotate_forecast_journal(path, keep_recent=10)

    def test_missing_live_is_a_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            report = rotate_forecast_journal(path, keep_recent=10)
            combined = load_all_forecasts(path)
        self.assertFalse(report["rotated"])
        self.assertEqual(report["source_records"], 0)
        self.assertEqual(combined, [])

    def test_invalid_parameters_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            append_forecasts(_forecasts(FIRST[:2]), path, at=AT)
            for value in (0, -1, True, 1.5, "10"):
                with self.assertRaises(ValueError):
                    rotate_forecast_journal(path, keep_recent=value)
            with self.assertRaises(ValueError):
                rotate_forecast_journal(path, keep_recent=1,
                                        archive_path=path)
            with self.assertRaises(ValueError):
                rotate_forecast_journal(path, keep_recent=1,
                                        lock_timeout=-1)

    def test_stale_lock_is_stolen(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            append_forecasts(_forecasts(ALL), path, at=AT)
            lock = Path(path + ".lock")
            lock.write_text("1:1\n", encoding="utf-8")
            old = time.time() - 60
            os.utime(lock, (old, old))
            report = rotate_forecast_journal(path, keep_recent=10)
            lock_exists = lock.exists()
        self.assertTrue(report["rotated"])
        self.assertFalse(lock_exists)

    def test_fresh_lock_times_out_without_rotation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            append_forecasts(_forecasts(ALL), path, at=AT)
            before = Path(path).read_bytes()
            lock = Path(path + ".lock")
            lock.write_text("1:1\n", encoding="utf-8")
            with self.assertRaises(TimeoutError):
                rotate_forecast_journal(path, keep_recent=10,
                                        lock_timeout=0.0)
            after = Path(path).read_bytes()
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
