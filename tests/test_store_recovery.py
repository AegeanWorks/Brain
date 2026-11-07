"""Store recovery: a corrupt database file is quarantined, never fatal."""

import os
import tempfile
import unittest

from memory.store import MemoryStore


class TestStoreRecovery(unittest.TestCase):
    def test_corrupt_file_quarantined_and_store_functional(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "mem.db")
            garbage = b"\x00\x01\x02corrupt-not-sqlite" * 100
            with open(path, "wb") as fh:
                fh.write(garbage)
            store = MemoryStore(path)
            try:
                self.assertEqual(store.count(), 0)
                rowid = store.save("k1", "recovered and working", 0.7)
                self.assertGreater(rowid, 0)
                hits = store.recall("recovered", limit=5)
                self.assertEqual(len(hits), 1)
                self.assertEqual(hits[0]["key"], "k1")
                quarantine = path + ".corrupt"
                self.assertTrue(os.path.exists(quarantine))
                with open(quarantine, "rb") as fh:
                    self.assertEqual(fh.read(), garbage)
                notes = store.recovery_notes()
                self.assertTrue(any("quarantined" in n for n in notes))
            finally:
                store.close()

    def test_healthy_file_never_quarantined(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "mem.db")
            first = MemoryStore(path)
            try:
                first.save("k1", "alpha beta", 0.9)
            finally:
                first.close()
            second = MemoryStore(path)
            try:
                self.assertEqual(second.count(), 1)
                self.assertFalse(os.path.exists(path + ".corrupt"))
                self.assertEqual(second.recovery_notes(), [])
            finally:
                second.close()


if __name__ == "__main__":
    unittest.main()
