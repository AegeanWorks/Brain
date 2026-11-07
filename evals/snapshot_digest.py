"""Snapshot content-vs-graph digest battery.

Re-capturing the same T3:15/65 battery changes the exact graph digest
(captured_at) but keeps the content digest. A changed steps field moves
both. A .meta sidecar verifies record count, graph and content; a
tampered meta or missing meta is named. The runs stay 13/6 with 1.0.
"""

import argparse
import copy
import json
import os
import tempfile
from pathlib import Path

from snapshot import (capture_snapshot, export_snapshot, snapshot_digests,
                      verify_snapshot)

MODES = ("recapture", "changed", "meta-intact", "meta-tampered", "missing")


def _battery(directory):
    records = capture_snapshot((("T3_navigate", 15),
                                ("T3_navigate", 65)), directory)
    return records


def measure_case(mode="recapture", directory=None):
    if directory is None:
        raise ValueError("directory is required")
    root = os.path.join(directory, "case-%s" % mode)
    os.makedirs(root, exist_ok=True)
    first = _battery(root)
    second = _battery(root)
    first_digests = snapshot_digests(first)
    second_digests = snapshot_digests(second)
    result = {
        "mode": mode,
        "records": first_digests["records"],
        "steps": [record["steps"] for record in first],
        "rewards": [record["reward"] for record in first],
        "success": all(record["success"] for record in first),
        "graph_same": (first_digests["graph_sha256"]
                       == second_digests["graph_sha256"]),
        "content_same": (first_digests["content_sha256"]
                         == second_digests["content_sha256"]),
        "graph_sha256": first_digests["graph_sha256"],
        "content_sha256": first_digests["content_sha256"],
    }
    if mode == "changed":
        changed = copy.deepcopy(first)
        changed[0]["steps"] += 1
        changed_digests = snapshot_digests(changed)
        result["graph_same"] = (changed_digests["graph_sha256"]
                                == first_digests["graph_sha256"])
        result["content_same"] = (changed_digests["content_sha256"]
                                  == first_digests["content_sha256"])
    elif mode in ("meta-intact", "meta-tampered", "missing"):
        path = os.path.join(root, "snapshot.jsonl")
        meta_path = path + ".meta"
        export_snapshot(first, path, meta_path=meta_path)
        if mode == "meta-tampered":
            meta = json.loads(Path(meta_path).read_text(encoding="utf-8"))
            meta["content_sha256"] = "0" * 64
            Path(meta_path).write_text(json.dumps(meta), encoding="utf-8")
        elif mode == "missing":
            Path(meta_path).unlink()
        verified = verify_snapshot(path, meta_path)
        result["verify_ok"] = verified["ok"]
        result["findings"] = verified["findings"]
    return result


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
