"""Advisory lock ownership: a stale-lock victim must not delete its successor.

Failing-first: each lock writes pid:timestamp and release blindly unlinks the
lock path. If a long-held lock is stolen as stale and a new writer acquires the
path, the original writer's release deletes the new writer's lock, allowing two
writers in. Release must only unlink a lock whose contents are its own token.
"""

import os
import tempfile
import unittest
from pathlib import Path

from claims_store import _locked as claims_locked
from calibration_store import _locked as calibration_locked
from telemetry.log import _append_lock


def _steal_and_replace(lock_path, new_token):
    stolen = Path(str(lock_path) + ".test_steal")
    os.replace(lock_path, stolen)
    stolen.unlink()
    lock_path.write_text(new_token, encoding="utf-8")


def _normal_release(lock_factory, target):
    with lock_factory(target, timeout_seconds=1.0):
        lock_path = Path(str(target) + ".lock")
        token = lock_path.read_text(encoding="utf-8")
    return token, lock_path.exists()


def _stolen_release(lock_factory, target):
    with lock_factory(target, timeout_seconds=1.0):
        lock_path = Path(str(target) + ".lock")
        token = lock_path.read_text(encoding="utf-8")
        _steal_and_replace(lock_path, "successor:token\n")
    state = lock_path.exists()
    content = lock_path.read_text(encoding="utf-8") if state else None
    if state:
        lock_path.unlink()
    return token, state, content


class TestFileLockOwnership(unittest.TestCase):
    def _check(self, lock_factory):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "state.json")
            token, gone = _normal_release(lock_factory, target)
            self.assertTrue(token.strip())
            self.assertFalse(gone, "normal release left the lock behind")
            token, exists, content = _stolen_release(lock_factory, target)
            self.assertTrue(token.strip())
            self.assertTrue(exists, "release deleted a successor lock")
            self.assertEqual(content, "successor:token\n")

    def test_telemetry_lock_preserves_successor(self):
        def factory(target, timeout_seconds=3.0):
            return _append_lock(target, timeout_seconds=timeout_seconds)
        self._check(factory)

    def test_claim_store_lock_preserves_successor(self):
        self._check(claims_locked)

    def test_calibration_store_lock_preserves_successor(self):
        self._check(calibration_locked)


if __name__ == "__main__":
    unittest.main()
