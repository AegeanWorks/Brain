"""Snapshot-diff battery: portable run records and deterministic deltas.

Captures T3:15 and T3:65 run records (steps, reward, success, action
hash, syn/phi), exports/reads them as JSONL, and diffs five controlled
variants: same, changed steps, added run, removed run, volatile-only
edit. Same and volatile-only diffs are empty; the other cases name the
record and fields. The captured runs stay 13/6 steps with 1.0 reward.
"""

import argparse
import copy
import json
import os
import tempfile

from snapshot import (capture_snapshot, diff_records, export_snapshot,
                      read_snapshot)

MODES = ("same", "changed", "added", "removed", "volatile")


def _battery(directory):
    records = capture_snapshot((("T3_navigate", 15),
                                ("T3_navigate", 65)), directory)
    path = os.path.join(directory, "snapshot.jsonl")
    export_snapshot(records, path)
    return records, path


def measure_case(mode="same", directory=None):
    if directory is None:
        raise ValueError("directory is required")
    base, path = _battery(directory)
    base = read_snapshot(path)
    new = copy.deepcopy(base)
    if mode == "changed":
        new[0]["steps"] += 1
    elif mode == "added":
        extra = copy.deepcopy(base[0])
        extra["id"] = "T3_navigate:99"
        extra["seed"] = 99
        new.append(extra)
    elif mode == "removed":
        new.pop()
    elif mode == "volatile":
        new[0]["created_at"] = "changed"
        new[0]["ts"] = 12345
    result = diff_records(base, new)
    return {
        "mode": mode,
        "records": len(base),
        "ids": [record["id"] for record in base],
        "steps": [record["steps"] for record in base],
        "rewards": [record["reward"] for record in base],
        "success": all(record["success"] for record in base),
        "actions": [record["action_sha256"][:8] for record in base],
        "diff": result,
    }


def run_battery(modes=MODES):
    with tempfile.TemporaryDirectory() as directory:
        return {"model": "rule", "modes": list(modes),
                "cases": [measure_case(mode, directory)
                          for mode in modes]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", action="append", choices=MODES, default=[],
                        help="repeatable (default: all modes)")
    args = parser.parse_args()
    modes = tuple(args.mode) if args.mode else MODES
    print(json.dumps(run_battery(modes), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
