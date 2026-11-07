"""Merkle compaction battery: three anchors to one union root, safely.

A 24-record log gets three 8-record batch anchors (0-8, 8-16, 16-24).
Compaction writes one anchor over 0-24; proofs for records 0, 12 and 23
still verify. The copy mode leaves the 3-anchor source untouched; the
replace mode backs it up as .bak and leaves one live anchor. Missing or
truncated journals are refused; a proof outside the union is rejected.
"""

import argparse
import json
import os
import tempfile
from pathlib import Path

from telemetry.log import Telemetry
from telemetry.merkle import (append_merkle_anchor, compact_merkle_journal,
                              merkle_proof_for_journal_record,
                              verify_merkle_journal, verify_merkle_proof)

MODES = ("copy", "replace", "proofs", "missing", "truncated", "outside")
STAMP = "2026-11-07T00:00:00Z"


def _log(path, records):
    tel = Telemetry(path)
    for index in range(records):
        tel.append_action(index, "step", {"i": index})


def _three_batches(path):
    for _ in range(3):
        _log(path, 8)
        append_merkle_anchor(path, batch_size=8, created_at=STAMP)
    return path + ".merkle.journal"


def _truncate(path, keep):
    lines = Path(path).read_text(encoding="utf-8").splitlines(True)
    Path(path).write_text("".join(lines[:keep]), encoding="utf-8")


def _lines(path):
    return len([line for line in
                Path(path).read_text(encoding="utf-8").splitlines()
                if line.strip()])


def measure_case(mode="copy", directory=None):
    if directory is None:
        raise ValueError("directory is required")
    path = os.path.join(directory, "run-%s.jsonl" % mode)
    result = {"mode": mode, "source_anchors": 0, "anchors": 0,
              "start": None, "end": None, "count": None,
              "original_anchors": 0, "backup_anchors": None,
              "replaced": None, "verified": None, "backup_verified": None,
              "proofs_ok": [], "metadata": False, "source_lines": 0,
              "compact_lines": 0, "error": None}
    if mode == "missing":
        _log(path, 8)
        try:
            compact_merkle_journal(path, path + ".missing")
        except ValueError as exc:
            result["error"] = str(exc)
        return result
    if mode == "outside":
        _log(path, 16)
        append_merkle_anchor(path, batch_size=8, created_at=STAMP)
        _log(path, 8)
        append_merkle_anchor(path, batch_size=8, created_at=STAMP)
        journal = path + ".merkle.journal"
        compact = path + ".compact"
        report = compact_merkle_journal(path, journal, output_path=compact)
        try:
            merkle_proof_for_journal_record(path, compact, 0)
        except ValueError as exc:
            result["error"] = str(exc)
        merged = verify_merkle_journal(path, compact)
        result.update({"source_anchors": report["source_anchors"],
                       "anchors": merged["anchors"],
                       "start": report["start"], "end": report["end"],
                       "count": report["count"],
                       "verified": merged["ok"],
                       "metadata": Path(compact + ".compaction").exists(),
                       "source_lines": _lines(journal),
                       "compact_lines": _lines(compact)})
        return result
    journal = _three_batches(path)
    if mode == "truncated":
        _truncate(path, 20)
        try:
            compact_merkle_journal(path, journal)
        except ValueError as exc:
            result["error"] = str(exc)
        return result
    source = verify_merkle_journal(path, journal)
    if mode == "replace":
        report = compact_merkle_journal(path, journal, replace=True)
        live = verify_merkle_journal(path, journal)
        backup = verify_merkle_journal(path, journal + ".bak")
        result.update({"anchors": live["anchors"],
                       "backup_anchors": backup["anchors"],
                       "verified": live["ok"],
                       "backup_verified": backup["ok"],
                       "replaced": report["replaced"],
                       "metadata": Path(journal + ".compaction").exists(),
                       "source_lines": _lines(journal + ".bak"),
                       "compact_lines": _lines(journal)})
    else:
        compact = path + ".compact"
        report = compact_merkle_journal(path, journal, output_path=compact)
        merged = verify_merkle_journal(path, compact)
        proofs = [merkle_proof_for_journal_record(path, compact, index)
                  for index in (0, 12, 23)]
        result.update({"anchors": merged["anchors"],
                       "verified": merged["ok"],
                       "proofs_ok": [verify_merkle_proof(item)
                                     for item in proofs],
                       "metadata": Path(compact + ".compaction").exists(),
                       "source_lines": _lines(journal),
                       "compact_lines": _lines(compact)})
    result.update({"source_anchors": report["source_anchors"],
                   "start": report["start"], "end": report["end"],
                   "count": report["count"],
                   "original_anchors": source["anchors"]})
    return result


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
