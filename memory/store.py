"""SQLite-backed store with FTS5 index and LIKE fallback.

Operational notes:
- One base table holds the records; one FTS5 external-content
  table indexes key/content for ranked lookup.
- Durability: commit then os.fsync on the database file.
- Ordering is deterministic: all reads use ORDER BY id ASC.
Stdlib only: sqlite3, os, time.
"""
import os
import sqlite3
import time


_SCHEMA_BASE = (
    "CREATE TABLE IF NOT EXISTS memories("
    "id INTEGER PRIMARY KEY, "
    "key TEXT UNIQUE NOT NULL, "
    "content TEXT NOT NULL, "
    "conf REAL NOT NULL, "
    "ts REAL NOT NULL)"
)

_SCHEMA_FTS = (
    "CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts "
    "USING fts5(key, content, content='memories', content_rowid='id')"
)

_TRIGGERS = (
    "CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN "
    "INSERT INTO memories_fts(rowid, key, content) "
    "VALUES (new.id, new.key, new.content); END",
    "CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN "
    "INSERT INTO memories_fts(memories_fts, rowid, key, content) "
    "VALUES('delete', old.id, old.key, old.content); END",
    "CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN "
    "INSERT INTO memories_fts(memories_fts, rowid, key, content) "
    "VALUES('delete', old.id, old.key, old.content); "
    "INSERT INTO memories_fts(rowid, key, content) "
    "VALUES (new.id, new.key, new.content); END",
)


class MemoryStore:
    """Persisted key/content map with full-text lookup.

    Layout: memories(id INTEGER PK, key TEXT UNIQUE,
    content TEXT, conf REAL, ts REAL) plus FTS5 index.
    """

    def __init__(self, path):
        """Open or create the store at path. Uses WAL mode."""
        self._path = path
        self._conn = sqlite3.connect(path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(_SCHEMA_BASE)
        self._conn.execute(_SCHEMA_FTS)
        for stmt in _TRIGGERS:
            self._conn.execute(stmt)
        self._persist()

    def _persist(self):
        """Commit then flush the database file to storage."""
        self._conn.commit()
        if self._path != ":memory:":
            fd = os.open(self._path, os.O_RDWR)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)

    def save(self, key, content, conf):
        """Insert or replace one record by key. Returns the row id."""
        if not isinstance(key, str) or not key:
            raise ValueError("Why: key must be a non-empty string. Fix: pass key=str.")
        if not isinstance(content, str):
            raise ValueError("Why: content must be a string. Fix: pass content=str.")
        ts = time.time()
        self._conn.execute(
            "INSERT INTO memories(key, content, conf, ts) VALUES(?, ?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET "
            "content=excluded.content, conf=excluded.conf, ts=excluded.ts",
            (key, content, float(conf), ts),
        )
        self._persist()
        row = self._conn.execute(
            "SELECT id FROM memories WHERE key=?", (key,)
        ).fetchone()
        return int(row[0])

    def recall(self, query, limit=5):
        """Return up to limit records matching query, ordered by id ASC.

        Primary path uses FTS5 MATCH; on syntax error or zero hits
        the lookup falls back to LIKE over key and content.
        """
        n = max(1, int(limit))
        q = "" if query is None else str(query)
        rows = []
        if q:
            try:
                rows = self._conn.execute(
                    "SELECT m.id, m.key, m.content, m.conf, m.ts "
                    "FROM memories_fts f JOIN memories m ON m.id=f.rowid "
                    "WHERE memories_fts MATCH ? ORDER BY m.id ASC LIMIT ?",
                    (q, n),
                ).fetchall()
            except sqlite3.OperationalError:
                rows = []
        if not rows:
            like = "%" + q + "%"
            rows = self._conn.execute(
                "SELECT id, key, content, conf, ts FROM memories "
                "WHERE key LIKE ? OR content LIKE ? "
                "ORDER BY id ASC LIMIT ?",
                (like, like, n),
            ).fetchall()
        return [
            {"id": r[0], "key": r[1], "content": r[2], "conf": r[3], "ts": r[4]}
            for r in rows
        ]

    def snapshot(self):
        """Return a deterministic dict view of all records ordered by id."""
        rows = self._conn.execute(
            "SELECT id, key, content, conf, ts FROM memories ORDER BY id ASC"
        ).fetchall()
        entries = [
            {"id": r[0], "key": r[1], "content": r[2], "conf": r[3], "ts": r[4]}
            for r in rows
        ]
        return {"count": len(entries), "entries": entries}

    def count(self):
        """Return the number of stored records."""
        row = self._conn.execute("SELECT COUNT(*) FROM memories").fetchone()
        return int(row[0])

    def close(self):
        """Flush and close the underlying connection."""
        try:
            self._persist()
        finally:
            self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False
