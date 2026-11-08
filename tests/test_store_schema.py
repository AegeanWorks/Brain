"""Layouts schema: the declared shape matches the migrated shape.

ADR-094 added a ``fingerprint`` column by an in-place ``ALTER``, but the
``CREATE TABLE`` declaration was not updated, so every fresh store still
migrated itself on open and the declared schema misdescribed the table.
This pins the declaration, the one-time legacy migration, and the
no-op migration on an already-current store.
"""

import json
import os
import sqlite3
import tempfile
import unittest

from memory import store as store_module
from memory.store import MemoryStore


def _layout_columns(conn):
    return [row[1] for row in
            conn.execute("PRAGMA table_info(layouts)").fetchall()]


class TestLayoutSchema(unittest.TestCase):
    def test_declared_schema_includes_fingerprint(self):
        self.assertIn("fingerprint", store_module._SCHEMA_LAYOUT)

    def test_fresh_store_needs_no_migration(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = MemoryStore(os.path.join(tmp, "mem.db"))
            try:
                self.assertIn("fingerprint",
                              _layout_columns(store._conn))
                self.assertIs(store._ensure_layout_fingerprint(store._conn),
                              False)
            finally:
                store.close()

    def test_legacy_store_is_migrated_and_row_survives(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "legacy.db")
            conn = sqlite3.connect(path)
            conn.execute(
                "CREATE TABLE layouts(task TEXT NOT NULL, seed INTEGER NOT NULL, "
                "content TEXT NOT NULL, ts REAL NOT NULL, PRIMARY KEY(task, seed))")
            conn.execute("INSERT INTO layouts VALUES(?,?,?,?)",
                         ("T3_navigate", 15,
                          json.dumps({"target": [6, 7]}), 1.0))
            conn.commit()
            conn.close()
            store = MemoryStore(path)
            try:
                self.assertIn("fingerprint", _layout_columns(store._conn))
                self.assertIs(store._ensure_layout_fingerprint(store._conn),
                              False)
                self.assertEqual(store.get_layout("T3_navigate", 15),
                                 json.dumps({"target": [6, 7]}))
                self.assertIsNone(store.layout_fingerprint("T3_navigate", 15))
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
