"""Workspace source hash and run-header binding (harness transfer).

Failing-first: there is no workspace file map or tree digest, and logged
headers do not bind the source tree that produced a run. The hash must
be stable across identical trees, change when a source file changes, and
ignore caches, logs, reports and database sidecars.
"""

import os
import tempfile
import unittest
from pathlib import Path

from agent import Agent
from telemetry.log import Telemetry
from workspace import workspace_digest, workspace_files


def _workspace(root):
    files = {
        "a.py": "a = 1\n",
        "b.md": "# b\n",
        "sub/c.py": "c = 3\n",
        "notes.txt": "notes\n",
        ".git/HEAD": "ref: refs/heads/master\n",
        "__pycache__/x.pyc": "bytecode",
        "run.jsonl": '{"log":true}\n',
        "reports/report.md": "report\n",
        ".aikit/ledger.json": "{}\n",
        "data.db": "db",
    }
    for name, content in files.items():
        path = Path(root) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


class TestWorkspaceHash(unittest.TestCase):
    def test_file_map_excludes_noise(self):
        with tempfile.TemporaryDirectory() as tmp:
            _workspace(tmp)
            files = workspace_files(tmp)
        self.assertEqual(set(files), {"a.py", "b.md", "sub/c.py", "notes.txt"})
        self.assertEqual(len(files["a.py"]), 64)

    def test_digest_stable_and_sensitive(self):
        with tempfile.TemporaryDirectory() as tmp:
            _workspace(tmp)
            first = workspace_digest(tmp)
            second = workspace_digest(tmp)
            (Path(tmp) / "a.py").write_text("a = 2\n", encoding="utf-8")
            changed = workspace_digest(tmp)
            (Path(tmp) / "__pycache__" / "y.pyc").write_text(
                "more", encoding="utf-8")
            after_cache = workspace_digest(tmp)
        self.assertEqual(first, second)
        self.assertNotEqual(first, changed)
        self.assertEqual(changed, after_cache)

    def test_missing_root_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                workspace_digest(os.path.join(tmp, "missing"))

    def test_logged_header_binds_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = os.path.join(tmp, "workspace")
            _workspace(root)
            log1 = os.path.join(tmp, "run1.jsonl")
            log2 = os.path.join(tmp, "run2.jsonl")
            log3 = os.path.join(tmp, "run3.jsonl")
            trace = Agent().run_task_logged(
                "T3_navigate", 15, max_steps=200, log_path=log1,
                workspace_root=root)
            Agent().run_task_logged(
                "T3_navigate", 15, max_steps=200, log_path=log2,
                workspace_root=root)
            (Path(root) / "a.py").write_text("a = 9\n", encoding="utf-8")
            Agent().run_task_logged(
                "T3_navigate", 15, max_steps=200, log_path=log3,
                workspace_root=root)
            first = Telemetry(log1).read_all()[0]
            second = Telemetry(log2).read_all()[0]
            third = Telemetry(log3).read_all()[0]
            want = workspace_digest(root)
        self.assertEqual(len(trace), 13)
        self.assertEqual(first["workspace_sha256"], second["workspace_sha256"])
        self.assertNotEqual(first["workspace_sha256"],
                            third["workspace_sha256"])
        # log3 ran against the mutated tree, so its header must carry `want`
        # (the digest measured after a.py became "a = 9"). log1's header must
        # still match a freshly built identical tree.
        self.assertEqual(third["workspace_sha256"], want)
        with tempfile.TemporaryDirectory() as tmp2:
            _workspace(tmp2)
            self.assertEqual(first["workspace_sha256"],
                             workspace_digest(tmp2))

    def test_header_workspace_is_optional(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "run.jsonl")
            Agent().run_task_logged("T3_navigate", 15, max_steps=200,
                                    log_path=log_path)
            header = Telemetry(log_path).read_all()[0]
        self.assertIsNone(header["workspace_sha256"])


if __name__ == "__main__":
    unittest.main()
