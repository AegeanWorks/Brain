"""Workspace-binding battery: source digest in logged run headers.

A temp source tree is hashed, logged with ``workspace_root=...``, and
compared to the run header. The same tree reruns with the same digest;
editing a source file changes it; adding a cache file does not. Without
``workspace_root`` the header field stays null. The agent still runs the
same 13-step/1.0 T3:15 path; only the evidence binding changes.
"""

import argparse
import json
import os
import tempfile
from pathlib import Path

from agent import Agent
from telemetry.log import Telemetry
from workspace import workspace_digest, workspace_files

MODES = ("same", "changed", "ignored-cache", "default")


def _workspace(root):
    files = {"a.py": "a = 1\n", "b.md": "# b\n", "sub/c.py": "c = 3\n"}
    for name, content in files.items():
        path = Path(root) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _logged(root, log_path):
    trace = Agent().run_task_logged("T3_navigate", 15, max_steps=200,
                                    log_path=log_path, workspace_root=root)
    header = Telemetry(log_path).read_all()[0]
    return header, trace


def measure_case(mode="same", directory=None):
    if directory is None:
        raise ValueError("directory is required")
    root = os.path.join(directory, "workspace-%s" % mode)
    _workspace(root)
    before = workspace_digest(root)
    files = workspace_files(root)
    if mode == "changed":
        (Path(root) / "a.py").write_text("a = 2\n", encoding="utf-8")
    elif mode == "ignored-cache":
        (Path(root) / "__pycache__").mkdir(exist_ok=True)
        (Path(root) / "__pycache__" / "x.pyc").write_text(
            "bytecode", encoding="utf-8")
    after = workspace_digest(root)
    if mode == "default":
        log_path = os.path.join(directory, "run-default.jsonl")
        trace = Agent().run_task_logged("T3_navigate", 15, max_steps=200,
                                        log_path=log_path)
        header = Telemetry(log_path).read_all()[0]
    else:
        log_path = os.path.join(directory, "run-%s.jsonl" % mode)
        header, trace = _logged(root, log_path)
    return {
        "mode": mode,
        "files": len(files),
        "before": before,
        "after": after,
        "digest_same": before == after,
        "header_sha256": header.get("workspace_sha256"),
        "header_matches": header.get("workspace_sha256") == after,
        "steps": len(trace),
        "reward": sum(record["reward"] for record in trace),
        "success": bool(trace[-1]["done"]) and sum(
            record["reward"] for record in trace) > 0.0,
    }


def run_battery(modes=MODES):
    with tempfile.TemporaryDirectory() as directory:
        return {"model": "rule", "modes": list(modes),
                "cases": [measure_case(mode, directory) for mode in modes]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", action="append", choices=MODES, default=[],
                        help="repeatable (default: all modes)")
    args = parser.parse_args()
    modes = tuple(args.mode) if args.mode else MODES
    print(json.dumps(run_battery(modes), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
