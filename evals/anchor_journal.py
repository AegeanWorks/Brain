"""Anchor-journal battery: chained run anchors and truncation detection.

A log is anchored twice (head at 11 records, then at 16). The journal
chains each anchor hash to the previous one. ``intact`` verifies the
full log against the latest anchor; ``truncated`` cuts the log back to
13 records and verifies it against the journal, which must report
``truncated-tail:13<16``. The journal itself is verified for hash and
prev-link integrity in both modes. No weights, binaries, or committed
logs: everything lives in a temporary directory.
"""

import argparse
import json
import os
import tempfile
from pathlib import Path

from telemetry.log import (Telemetry, verify_anchor_journal,
                           verify_chain)

MODES = ("intact", "truncated")
STAMP = "2026-11-07T00:00:00Z"


def _build(path):
    tel = Telemetry(path)
    tel.write_header("T3_navigate", 200, policy="anchor-journal-battery")
    for index in range(10):
        tel.append_action(index, "step", {"i": index})
    first = tel.write_anchor_journal(created_at=STAMP)
    for index in range(10, 15):
        tel.append_action(index, "step", {"i": index})
    second = tel.write_anchor_journal(created_at=STAMP)
    return tel, first, second


def _truncate(path, keep):
    lines = Path(path).read_text(encoding="utf-8").splitlines(True)
    Path(path).write_text("".join(lines[:keep]), encoding="utf-8")


def measure_case(mode="intact", directory=None):
    if directory is None:
        raise ValueError("directory is required")
    path = os.path.join(directory, "run-%s.jsonl" % mode)
    tel, first, second = _build(path)
    before = len(tel.read_all())
    if mode == "truncated":
        _truncate(path, 13)
    after = len(Telemetry(path).read_all())
    journal_path = path + ".anchors"
    journal = verify_anchor_journal(journal_path)
    result = verify_chain(path, journal_path=journal_path)
    return {
        "mode": mode,
        "records_before": before,
        "records_after": after,
        "anchors": journal["anchors"],
        "first_seq": first["seq"],
        "latest_seq": second["seq"],
        "journal_ok": journal["ok"],
        "journal_errors": journal["errors"],
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
