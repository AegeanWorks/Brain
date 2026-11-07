"""Concurrent telemetry writers must preserve the hash chain.

Failing-first harness: two writers read the same head digest before
either appends, so both link to the old head and verify_chain reports
a broken link. The append must serialise head-read through durable
write; the test forces the interleaving with a slowed head read.
"""

import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from telemetry.log import LOCK_STALE_SECONDS, Telemetry, verify_chain


class TestTelemetryConcurrency(unittest.TestCase):
    def test_two_writers_keep_one_valid_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            barrier = threading.Barrier(2)
            real_head = Telemetry._head_digest

            def slowed_head(tel):
                head = real_head(tel)
                time.sleep(0.1)
                return head

            errors = []

            def writer():
                tel = Telemetry(path)
                try:
                    barrier.wait(timeout=5)
                    tel.append_action(1, "concurrent", {"writer": tel is not None})
                except Exception as exc:  # hygiene: allow test thread reports failure
                    errors.append(exc)

            with mock.patch.object(Telemetry, "_head_digest", slowed_head):
                threads = [threading.Thread(target=writer) for _ in range(2)]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join(timeout=10)

            self.assertEqual(errors, [])
            result = verify_chain(path)
            self.assertTrue(result["ok"], result["findings"])
            self.assertEqual(result["records"], 2)

    def test_single_writer_chain_still_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            tel = Telemetry(path)
            for seq in range(3):
                tel.append_action(seq, "single", {"seq": seq})
            result = verify_chain(path)
            self.assertTrue(result["ok"], result["findings"])
            self.assertEqual(result["records"], 3)

    def test_lock_timeout_surfaces_instead_of_interleaving(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            lock = Path(path + ".lock")
            lock.write_text("9999:0\n", encoding="utf-8")
            tel = Telemetry(path, lock_timeout=0.05)
            with self.assertRaises(TimeoutError) as caught:
                tel.append_action(1, "blocked", {})
            self.assertIn("telemetry lock", str(caught.exception))
            lock.unlink()
            tel.append_action(2, "released", {})
            result = verify_chain(path)
            self.assertTrue(result["ok"], result["findings"])
            self.assertEqual(result["records"], 1)

    def test_stale_lock_is_broken(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            lock = Path(path + ".lock")
            lock.write_text("9999:0\n", encoding="utf-8")
            old = time.time() - LOCK_STALE_SECONDS - 5.0
            os.utime(lock, (old, old))
            tel = Telemetry(path, lock_timeout=1.0)
            tel.append_action(1, "recovered", {})
            self.assertFalse(lock.exists())
            result = verify_chain(path)
            self.assertTrue(result["ok"], result["findings"])
            self.assertEqual(result["records"], 1)


if __name__ == "__main__":
    unittest.main()
