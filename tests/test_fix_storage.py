"""Regression tests for the storage-layer review findings (reforge genuine).

Failing-first against the shipped code: a non-ASCII MAC must still produce a
named tamper finding, the LIKE fallback must not treat ``_``/``%`` in a term as
SQL wildcards, a transient ``OperationalError`` must never quarantine a healthy
database, and calibration must reject duplicate forecast ids. S60 (stale-lock
release race) is covered elsewhere and is already fixed via an ownership token.
"""

import hashlib
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from calibration import summary
from memory.store import MemoryStore
from telemetry.log import Telemetry, verify_chain

KEY = hashlib.sha256(b"fix-storage-hmac-key").digest()


class TestNonAsciiMac(unittest.TestCase):
    def _build_keyed_log(self, path):
        tel = Telemetry(path, hmac_key=KEY)
        tel.write_header("T3_navigate", 200, policy="fix-storage")
        tel.append_action(0, "step", {"i": 0})
        tel.append_result(0, True, "step", 1.0)
        tel.write_verdict("done", "steps=1 reward=1.0")

    def test_non_ascii_mac_reports_bad_mac_not_typeerror(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            self._build_keyed_log(path)
            lines = Path(path).read_text(encoding="utf-8").splitlines(True)
            record = json.loads(lines[0])
            # Attacker-controlled non-ASCII mac; digest excludes mac so the
            # record still reaches the HMAC comparison.
            record["mac"] = "caf\u00e9-\u2603"
            lines[0] = json.dumps(record, sort_keys=True) + "\n"
            Path(path).write_text("".join(lines), encoding="utf-8")
            result = verify_chain(path, hmac_key=KEY)
        self.assertFalse(result["ok"])
        self.assertTrue(any(f.startswith("bad-mac:0") for f in result["findings"]),
                        result["findings"])

    def test_ascii_mac_still_verifies(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            self._build_keyed_log(path)
            result = verify_chain(path, hmac_key=KEY)
        self.assertTrue(result["ok"], result["findings"])


class TestLikeWildcards(unittest.TestCase):
    def test_fallback_escapes_like_wildcards(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "m.db")
            writer = MemoryStore(path)
            writer.save("T3_navigate", "legit", 1.0)
            writer.save("T3Xnavigate", "underscore wildcard", 1.0)
            writer.save("T3%navigate", "percent wildcard", 1.0)
            writer.close()
            reader = MemoryStore(path)
            # The FTS expression is a syntax error, forcing the LIKE fallback.
            keys = [row["key"] for row in
                    reader.recall("T3_navigate AND (", limit=10)]
            reader.close()
        self.assertEqual(keys, ["T3_navigate"])


class TestQuarantineScope(unittest.TestCase):
    def test_transient_operational_error_is_not_quarantined(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "mem.db")
            first = MemoryStore(path)
            try:
                first.save("k1", "keep me", 0.9)
            finally:
                first.close()
            real_connect = MemoryStore._connect_validated
            calls = []

            def flaky_connect(instance):
                calls.append(1)
                if len(calls) == 1:
                    raise sqlite3.OperationalError("database is locked")
                return real_connect(instance)

            with patch.object(MemoryStore, "_connect_validated", flaky_connect):
                with self.assertRaises(sqlite3.OperationalError):
                    MemoryStore(path)
            self.assertFalse(
                os.path.exists(path + ".corrupt"),
                "a transient lock must not quarantine a healthy store")
            reopened = MemoryStore(path)
            try:
                self.assertEqual(reopened.count(), 1)
            finally:
                reopened.close()

    def test_genuine_corruption_still_quarantined(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bad.db")
            with open(path, "wb") as fh:
                fh.write(b"\x00\x01\x02not-sqlite" * 100)
            store = MemoryStore(path)
            try:
                self.assertEqual(store.count(), 0)
                self.assertTrue(os.path.exists(path + ".corrupt"))
            finally:
                store.close()


class TestUniqueForecastIds(unittest.TestCase):
    def test_duplicate_forecast_ids_rejected(self):
        forecasts = [
            {"id": "dup", "probability": 0.2, "outcome": 1},
            {"id": "dup", "probability": 0.9, "outcome": 0},
        ]
        with self.assertRaises(ValueError):
            summary(forecasts, min_resolved=1)

    def test_unique_ids_still_scored(self):
        result = summary([
            {"id": "a", "probability": 0.9, "outcome": 1},
            {"id": "b", "probability": 0.1, "outcome": 0},
        ], min_resolved=2)
        self.assertEqual(result["counts"]["resolved"], 2)


if __name__ == "__main__":
    unittest.main()
