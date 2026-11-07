"""Terminal-anchor battery: truncated telemetry tails are detected.

A log is written with a header, actions and a verdict, then a separate
anchor records the final head and record count. ``intact`` verifies
with the anchor; ``truncated`` deletes the last two lines and verifies
with the anchor (detected); ``unanchored`` deletes the same lines and
verifies without the anchor (the old residual exposure). No weights,
binaries, or committed logs: every artifact lives in a temporary
directory and only hashes/counts are reported.
"""

import argparse
import json
import os
import tempfile
from pathlib import Path

from telemetry.log import Telemetry, verify_chain

MODES = ("intact", "truncated", "unanchored")


def _build_log(path):
    tel = Telemetry(path)
    tel.write_header("T3_navigate", 200, policy="chain-anchor-battery")
    for index in range(3):
        tel.append_action(index, "step", {"i": index})
        tel.append_result(index, True, "step", 1.0)
    tel.write_verdict("done", "steps=3 reward=1.0")
    return tel


def _truncate(path, keep=5):
    lines = Path(path).read_text(encoding="utf-8").splitlines(True)
    Path(path).write_text("".join(lines[:keep]), encoding="utf-8")


def measure_case(mode="intact", directory=None):
    if directory is None:
        raise ValueError("directory is required")
    path = os.path.join(directory, "run-%s.jsonl" % mode)
    tel = _build_log(path)
    anchor_path = tel.write_anchor()
    anchor = json.loads(Path(anchor_path).read_text(encoding="utf-8"))
    before = len(tel.read_all())
    if mode in ("truncated", "unanchored"):
        _truncate(path, keep=max(1, before - 2))
    after = len(Telemetry(path).read_all())
    if mode == "unanchored":
        result = verify_chain(path)
    else:
        result = verify_chain(path, anchor_path=anchor_path)
    return {
        "mode": mode,
        "records_before": before,
        "records_after": after,
        "anchor_records": anchor["records"],
        "anchor_head": anchor["head"],
        "ok": result["ok"],
        "findings": result["findings"],
        "verified_records": result["records"],
        "verified_head": result["head"],
        "detected": not result["ok"],
    }


def run_battery(modes=MODES):
    with tempfile.TemporaryDirectory() as directory:
        results = [measure_case(mode=mode, directory=directory)
                   for mode in modes]
        return {"model": "rule", "modes": list(modes), "cases": results}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", action="append", choices=MODES, default=[],
                        help="repeatable (default: all modes)")
    args = parser.parse_args()
    modes = tuple(args.mode) if args.mode else MODES
    print(json.dumps(run_battery(modes), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
