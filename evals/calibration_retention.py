"""Calibration retention battery: archive older forecasts, keep the newest.

A 19-record journal rotates to 10 live + 9 archived with the same
Brier/skill, a 19-record backup and a .rotation sidecar. A second
rotation after 6 new records yields 10 live + 15 archived = 25 records.
Short/missing journals are no-ops; archive id conflicts and fresh locks
are refused.
"""

import argparse
import json
import os
import tempfile
import time
from pathlib import Path

from calibration import summary
from calibration_store import (append_forecasts, load_all_forecasts,
                               load_forecasts, rotate_forecast_journal,
                               verify_forecast_file)

MODES = ("before", "rotate", "all", "second", "noop", "conflict",
         "missing", "lock")
AT = "2026-11-07T00:00:00Z"
FIRST = (
    ("run1:0", 0.9, 1), ("run1:1", 0.8, 1), ("run1:2", 0.7, 0),
    ("run1:3", 0.6, 1), ("run1:4", 0.5, 0), ("run1:5", 0.4, 0),
)
SECOND = (
    ("run2:0", 0.8, 1), ("run2:1", 0.7, 1),
    ("run2:2", 0.2, 0), ("run2:3", 0.1, 0),
)
EXTRA = tuple(
    ("run3:%d" % index, 0.6 if index % 2 == 0 else 0.3,
     1 if index % 3 == 0 else 0)
    for index in range(9)
)
ALL = FIRST + SECOND + EXTRA


def _forecasts(rows):
    return [{"id": identifier, "probability": probability,
             "outcome": outcome} for identifier, probability, outcome in rows]


def _stats(records):
    result = summary(records, min_resolved=10)
    return {"brier": result["brier"], "skill": result["skill"],
            "resolved": result["counts"]["resolved"]}


def measure_case(mode="rotate", directory=None):
    if directory is None:
        raise ValueError("directory is required")
    path = os.path.join(directory, "forecasts-%s.jsonl" % mode)
    archive = path + ".archive"
    result = {"mode": mode, "rotated": None, "source_records": 0,
              "live": 0, "archive": 0, "total": 0,
              "before_brier": None, "before_skill": None,
              "after_brier": None, "after_skill": None,
              "resolved": 0, "backup": None, "metadata": False,
              "unique": None, "findings": [], "error": None}
    if mode == "missing":
        report = rotate_forecast_journal(path, keep_recent=10)
        result.update({"rotated": report["rotated"],
                       "source_records": report["source_records"],
                       "live": len(load_forecasts(path)),
                       "total": len(load_all_forecasts(path))})
        return result
    if mode == "lock":
        append_forecasts(_forecasts(ALL), path, at=AT)
        lock = Path(path + ".lock")
        lock.write_text("1:1\n", encoding="utf-8")
        try:
            rotate_forecast_journal(path, keep_recent=10, lock_timeout=0.0)
        except TimeoutError as exc:
            result["error"] = str(exc)
        result.update({"live": len(load_forecasts(path)),
                       "total": len(load_forecasts(path))})
        return result
    if mode == "noop":
        append_forecasts(_forecasts(FIRST[:5]), path, at=AT)
        report = rotate_forecast_journal(path, keep_recent=10)
        result.update({"rotated": report["rotated"],
                       "source_records": report["source_records"],
                       "live": len(load_forecasts(path)),
                       "archive": 0, "total": len(load_forecasts(path))})
        return result
    if mode == "conflict":
        append_forecasts(_forecasts(ALL), path, at=AT)
        append_forecasts([{"id": "run1:0", "probability": 0.1,
                           "outcome": 0}], archive, at=AT)
        try:
            rotate_forecast_journal(path, keep_recent=10)
        except ValueError as exc:
            result["error"] = str(exc)
        result.update({"live": len(load_forecasts(path))})
        return result
    append_forecasts(_forecasts(ALL), path, at=AT)
    before = _stats(load_forecasts(path))
    result.update({"source_records": 19,
                   "before_brier": before["brier"],
                   "before_skill": before["skill"]})
    if mode == "before":
        result.update({"live": 19, "total": 19})
        return result
    if mode == "second":
        rotate_forecast_journal(path, keep_recent=10)
        extra = [{"id": "run4:%d" % index, "probability": 0.5,
                  "outcome": index % 2} for index in range(6)]
        append_forecasts(extra, path, at=AT)
        report = rotate_forecast_journal(path, keep_recent=10)
        result["source_records"] = report["source_records"]
    else:
        report = rotate_forecast_journal(path, keep_recent=10)
    live = load_forecasts(path)
    archived = load_forecasts(archive) if Path(archive).exists() else []
    combined = load_all_forecasts(path)
    after = _stats(combined)
    result.update({"rotated": report["rotated"],
                   "live": len(live), "archive": len(archived),
                   "total": len(combined), "resolved": after["resolved"],
                   "after_brier": after["brier"],
                   "after_skill": after["skill"],
                   "backup": (len(load_forecasts(path + ".bak"))
                              if Path(path + ".bak").exists() else None),
                   "metadata": Path(path + ".rotation").exists(),
                   "unique": len({r["id"] for r in combined}) == len(combined)})
    if mode in ("rotate", "second"):
        result["findings"] = (verify_forecast_file(path)["findings"]
                              + verify_forecast_file(archive)["findings"])
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
