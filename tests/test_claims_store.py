"""Durable claim-ledger store: atomic snapshots, backups and quarantine.

Failing-first: ClaimLedger roundtrips as JSON but has no file API, so
claims and verdicts vanish on exit. The store must save one checksummed
snapshot atomically, keep the previous snapshot as ``.bak``, load it
back, quarantine a corrupt primary and recover from the backup, and
refuse to hang behind a fresh writer lock.
"""

import json
import os
import tempfile
import time
import unittest
from pathlib import Path

from claims import ClaimLedger
from claims_store import (_digest, load_ledger, save_ledger,
                          verify_ledger_file)

STAMP = 1700000000.0
AT = "2026-11-07T00:00:00Z"


def _ledger(extra=False):
    ledger = ClaimLedger()
    ledger.add("T3:15 takes 13 steps", "steps != 13", 0.9)
    ledger.record("C1", "supports", "actual=13", at=AT)
    ledger.add("T3:65 takes 6 steps", "steps != 6", 0.8)
    ledger.record("C2", "supports", "actual=6", at=AT)
    ledger.add("T3:65 reward is 0.0", "reward != 0.0", 0.7)
    ledger.record("C3", "refutes", "actual=1.0", at=AT)
    if extra:
        ledger.add("extra claim", "never", 0.5)
    return ledger


def _rewrite(path, mutate):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    mutate(payload)
    Path(path).write_text(json.dumps(payload, sort_keys=True) + "\n",
                          encoding="utf-8")


class TestClaimStore(unittest.TestCase):
    def test_roundtrip_preserves_claims_and_verdicts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "claims.json")
            ledger = _ledger()
            report = save_ledger(ledger, path, saved_at=STAMP)
            loaded = load_ledger(path)
            verified = verify_ledger_file(path)
        self.assertEqual(loaded.claims(), ledger.claims())
        self.assertEqual(report["claims"], 3)
        self.assertEqual(report["verdicts"], 3)
        self.assertEqual(len(report["sha256"]), 64)
        self.assertTrue(verified["ok"], verified["findings"])
        self.assertEqual(verified["claims"], 3)
        self.assertEqual(verified["verdicts"], 3)

    def test_refs_survive_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "claims.json")
            ledger = ClaimLedger()
            ledger.add("T3:15 takes 13 steps", "steps != 13")
            ledger.record("C1", "supports", "actual=13", at=AT,
                          ref="episode-a")
            save_ledger(ledger, path, saved_at=STAMP)
            loaded = load_ledger(path)
            verified = verify_ledger_file(path)
        self.assertEqual(loaded.get("C1").verdicts[0].ref, "episode-a")
        self.assertTrue(verified["ok"], verified["findings"])

    def test_forged_status_with_valid_checksum_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "claims.json")
            save_ledger(_ledger(), path, saved_at=STAMP)
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            payload["claims"][0]["status"] = "refuted"
            payload["sha256"] = _digest(payload)
            Path(path).write_text(json.dumps(payload, sort_keys=True) + "\n",
                                  encoding="utf-8")
            verified = verify_ledger_file(path)
            with self.assertRaises(ValueError):
                load_ledger(path)
        self.assertFalse(verified["ok"])
        self.assertTrue(any("claims are invalid" in finding
                            for finding in verified["findings"]),
                        verified["findings"])

    def test_keyed_snapshot_roundtrip_and_wrong_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "claims.json")
            key = b"claim-store-key-32-bytes-long!!"
            wrong = b"wrong-key-32-bytes-long!!!!!!!!"
            save_ledger(_ledger(), path, saved_at=STAMP, hmac_key=key)
            loaded = load_ledger(path, hmac_key=key)
            verified = verify_ledger_file(path, hmac_key=key)
            unkeyed = load_ledger(path)
            with self.assertRaises(ValueError):
                load_ledger(path, hmac_key=wrong)
            wrong_verified = verify_ledger_file(path, hmac_key=wrong)
            still_loads = load_ledger(path, hmac_key=key)
            primary_exists = Path(path).exists()
        self.assertEqual(loaded.claims(), _ledger().claims())
        self.assertTrue(verified["ok"], verified["findings"])
        self.assertTrue(verified["hmac"])
        self.assertEqual(unkeyed.claims(), _ledger().claims())
        self.assertTrue(primary_exists, "a wrong key quarantined the primary")
        self.assertEqual(still_loads.claims(), loaded.claims())
        self.assertFalse(wrong_verified["ok"])
        self.assertTrue(any("mac" in finding.lower()
                            for finding in wrong_verified["findings"]))

    def test_keyed_snapshot_requires_a_mac(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "claims.json")
            key = b"claim-store-key-32-bytes-long!!"
            save_ledger(_ledger(), path, saved_at=STAMP)
            with self.assertRaises(ValueError):
                load_ledger(path, hmac_key=key)
            verified = verify_ledger_file(path, hmac_key=key)
        self.assertFalse(verified["ok"])
        self.assertTrue(any("missing its mac" in finding.lower()
                            for finding in verified["findings"]),
                        verified["findings"])

    def test_keyed_snapshot_detects_recomputed_checksum(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "claims.json")
            key = b"claim-store-key-32-bytes-long!!"
            save_ledger(_ledger(), path, saved_at=STAMP, hmac_key=key)
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            payload["claims"][0]["text"] = "tampered"
            payload["sha256"] = _digest(payload)
            Path(path).write_text(json.dumps(payload, sort_keys=True) + "\n",
                                  encoding="utf-8")
            verified = verify_ledger_file(path, hmac_key=key)
            with self.assertRaises(ValueError):
                load_ledger(path, hmac_key=key)
        self.assertFalse(verified["ok"])
        self.assertTrue(any("mac" in finding.lower()
                            for finding in verified["findings"]))

    def test_invalid_hmac_key_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "claims.json")
            for value in ("text", b"", 3):
                with self.assertRaises(ValueError):
                    save_ledger(_ledger(), path, saved_at=STAMP,
                                hmac_key=value)
                with self.assertRaises(ValueError):
                    load_ledger(path, hmac_key=value)

    def test_missing_primary_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "claims.json")
            loaded = load_ledger(path)
            verified = verify_ledger_file(path)
        self.assertEqual(loaded.claims(), ())
        self.assertFalse(verified["ok"])
        self.assertIn("missing-primary", verified["findings"])

    def test_second_save_backs_up_and_corrupt_recovers(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "claims.json")
            first = _ledger()
            second = _ledger(extra=True)
            save_ledger(first, path, saved_at=STAMP)
            save_ledger(second, path, saved_at=STAMP)
            Path(path).write_text("{not json\n", encoding="utf-8")
            broken = verify_ledger_file(path)
            loaded = load_ledger(path)
            after = verify_ledger_file(path)
            quarantine = Path(path + ".corrupt")
            backup = Path(path + ".bak")
            backup_exists = backup.exists()
            quarantine_exists = quarantine.exists()
        self.assertFalse(broken["ok"])
        self.assertTrue(any("invalid-primary" in finding
                            for finding in broken["findings"]))
        self.assertEqual(loaded.claims(), first.claims())
        self.assertEqual(after["ok"], False)
        self.assertIn("missing-primary", after["findings"])
        self.assertTrue(backup_exists)
        self.assertTrue(quarantine_exists)

    def test_missing_primary_loads_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "claims.json")
            first = _ledger()
            save_ledger(first, path, saved_at=STAMP)
            save_ledger(_ledger(extra=True), path, saved_at=STAMP)
            Path(path).unlink()
            loaded = load_ledger(path)
        self.assertEqual(loaded.claims(), first.claims())

    def test_tampered_payload_fails_verify_and_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "claims.json")
            save_ledger(_ledger(), path, saved_at=STAMP)
            _rewrite(path, lambda payload:
                     payload["claims"][0].__setitem__("text", "tampered"))
            verified = verify_ledger_file(path)
            with self.assertRaises(ValueError):
                load_ledger(path)
            quarantine_exists = Path(path + ".corrupt").exists()
        self.assertFalse(verified["ok"])
        self.assertTrue(any("checksum" in finding
                            for finding in verified["findings"]))
        self.assertTrue(quarantine_exists)

    def test_invalid_schema_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "claims.json")
            save_ledger(_ledger(), path, saved_at=STAMP)
            _rewrite(path, lambda payload: payload.__setitem__("schema", 2))
            verified = verify_ledger_file(path)
            with self.assertRaises(ValueError):
                load_ledger(path)
        self.assertFalse(verified["ok"])
        self.assertTrue(any("schema" in finding
                            for finding in verified["findings"]))

    def test_stale_lock_is_stolen(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "claims.json")
            lock = Path(path + ".lock")
            lock.write_text("1:1\n", encoding="utf-8")
            old = time.time() - 60
            os.utime(lock, (old, old))
            report = save_ledger(_ledger(), path, saved_at=STAMP)
            lock_exists = lock.exists()
        self.assertEqual(report["claims"], 3)
        self.assertFalse(lock_exists)

    def test_fresh_lock_times_out_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "claims.json")
            lock = Path(path + ".lock")
            lock.write_text("1:1\n", encoding="utf-8")
            with self.assertRaises(TimeoutError):
                save_ledger(_ledger(), path, saved_at=STAMP, lock_timeout=0.0)
            primary_exists = Path(path).exists()
        self.assertFalse(primary_exists)

    def test_no_temporary_files_after_saves(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "claims.json")
            save_ledger(_ledger(), path, saved_at=STAMP)
            save_ledger(_ledger(extra=True), path, saved_at=STAMP)
            names = sorted(os.listdir(tmp))
            leftovers = [name for name in names if name.endswith(".tmp")]
            backup_exists = Path(path + ".bak").exists()
        self.assertEqual(leftovers, [])
        self.assertTrue(backup_exists)

    def test_saved_at_makes_checksum_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            first_path = os.path.join(tmp, "first.json")
            second_path = os.path.join(tmp, "second.json")
            first = save_ledger(_ledger(), first_path, saved_at=STAMP)
            second = save_ledger(_ledger(), second_path, saved_at=STAMP)
            first_ok = verify_ledger_file(first_path)["ok"]
            second_ok = verify_ledger_file(second_path)["ok"]
        self.assertEqual(first["sha256"], second["sha256"])
        self.assertTrue(first_ok)
        self.assertTrue(second_ok)

    def test_invalid_inputs_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "claims.json")
            with self.assertRaises(ValueError):
                save_ledger({}, path, saved_at=STAMP)
            with self.assertRaises(ValueError):
                save_ledger(_ledger(), path, saved_at="now")
            with self.assertRaises(ValueError):
                save_ledger(_ledger(), path, saved_at=STAMP,
                            lock_timeout=-1)


if __name__ == "__main__":
    unittest.main()
