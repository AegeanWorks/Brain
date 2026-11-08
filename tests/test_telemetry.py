"""Telemetry roundtrip checks."""

import hashlib
import json
import os
import time
import unittest
import tempfile

from telemetry.log import Telemetry


class TestTelemetry(unittest.TestCase):
    def test_read_headers_matches_filtered_read_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "t.jsonl")
            tel = Telemetry(path)
            tel.write_header("task-a", 10, episode_sha256="a" * 64)
            tel.append_action(1, "exec", {"cmd": "x"})
            tel.write_header("task-b", 5, episode_sha256="b" * 64)
            tel.append_action(2, "exec", {"cmd": "y"})
            headers = tel.read_headers()
            expected = [row for row in tel.read_all()
                        if row.get("type") == "header"]
        self.assertEqual(headers, expected)
        self.assertEqual([row["task"] for row in headers],
                         ["task-a", "task-b"])

    def test_read_headers_missing_file_is_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "missing.jsonl")
            self.assertEqual(Telemetry(path).read_headers(), [])

    def test_read_headers_raises_on_malformed_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bad.jsonl")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("{bad json\n")
            with self.assertRaises(ValueError):
                Telemetry(path).read_headers()

    def test_append_read_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "t.jsonl")
            tel = Telemetry(path)
            tel.write_header("task-a", 10)
            tel.append_action(1, "exec", {"cmd": "x"}, M=[1], P=[2], S=[3], hub=[0.5, 0.25])
            tel.append_result(1, True, "ok", 1.5, M=[1], P=[2], S=[3], hub=[0.5, 0.25])
            rows = tel.read_all()
            self.assertEqual(len(rows), 3)
            self.assertEqual([r["type"] for r in rows], ["header", "action", "result"])
            for r in rows:
                self.assertEqual(r["schema"], 2)
                for key in ("seq", "type", "ts", "M", "P", "S", "hub"):
                    self.assertIn(key, r)
            self.assertEqual(rows[0]["task"], "task-a")
            self.assertEqual(rows[0]["budget"], 10)
            self.assertEqual(rows[1]["seq"], 1)
            self.assertEqual(rows[1]["kind"], "exec")
            self.assertEqual(rows[1]["args"], {"cmd": "x"})
            self.assertTrue(rows[2]["ok"])
            self.assertEqual(rows[2]["cost"], 1.5)

    def test_fsync_file_exists_and_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "t.jsonl")
            tel = Telemetry(path)
            tel.write_header("task-b", 1, manifest_sha256="abc123")
            tel.append_action(1, "run", {})
            self.assertTrue(os.path.exists(path))
            self.assertGreater(os.path.getsize(path), 0)
            with open(path, "r", encoding="utf-8") as f:
                lines = [ln for ln in f if ln.strip()]
            self.assertGreaterEqual(len(lines), 2)
            for ln in lines:
                obj = json.loads(ln)
                self.assertEqual(obj["schema"], 2)
            self.assertEqual(json.loads(lines[0])["manifest_sha256"], "abc123")

    def test_verdict_and_bins(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "t.jsonl")
            tel = Telemetry(path)
            tel.write_header("task-c", 5)
            tel.append_action(1, "run", {"n": 1})
            tel.append_result(1, False, "err", 0.5)
            tel.write_verdict("fail", "done")
            rows = tel.read_all()
            self.assertEqual(rows[-1]["type"], "verdict")
            self.assertEqual(rows[-1]["verdict"], "fail")
            self.assertEqual(rows[-1]["reason"], "done")
            grouped = tel.bins(step_ms=50)
            self.assertIsInstance(grouped, list)
            self.assertGreaterEqual(len(grouped), 1)
            self.assertEqual(sum(g["count"] for g in grouped), len(rows))


    def test_head_digest_tail_read_equivalence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "t.jsonl")
            tel = Telemetry(path)
            tel.write_header("task-d", 5)
            tel.append_action(1, "run", {"n": 1})
            last = tel.read_all()[-1]["digest"]
            self.assertEqual(Telemetry(path)._head_digest(), last)
            with open(path, "a", encoding="utf-8") as fh:
                fh.write("\n\n")
            self.assertEqual(Telemetry(path)._head_digest(), last)

            legacy_line = '{"legacy":true}\n'
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(legacy_line)
            want = "LEGACY:" + hashlib.sha256(
                legacy_line.encode("utf-8")).hexdigest()
            self.assertEqual(Telemetry(path)._head_digest(), want)

            legacy_path = os.path.join(tmp, "legacy.jsonl")
            legacy_raw = '{"legacy":"no-newline"}'
            with open(legacy_path, "w", encoding="utf-8") as fh:
                fh.write(legacy_raw)
            want = "LEGACY:" + hashlib.sha256(
                legacy_raw.encode("utf-8")).hexdigest()
            self.assertEqual(Telemetry(legacy_path)._head_digest(), want)

            with open(legacy_path, "a", encoding="utf-8") as fh:
                fh.write("\n\n")
            want = "LEGACY:" + hashlib.sha256(
                (legacy_raw + "\n").encode("utf-8")).hexdigest()
            self.assertEqual(Telemetry(legacy_path)._head_digest(), want)

    def test_head_digest_reads_tail_not_whole_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "big.jsonl")
            with open(path, "w", encoding="utf-8") as fh:
                for index in range(200_000):
                    fh.write('{"x":%d}\n' % index)
                fh.write(json.dumps({"digest": "a" * 64,
                                     "prev": "GENESIS"},
                                    sort_keys=True) + "\n")
            timings = []
            for _ in range(2):
                started = time.perf_counter()
                head = Telemetry(path)._head_digest()
                timings.append(time.perf_counter() - started)
            self.assertEqual(head, "a" * 64)
            self.assertLess(min(timings), 0.120)


if __name__ == "__main__":
    unittest.main()
