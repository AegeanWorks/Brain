"""Calibration-store battery: cross-run forecasts and named defects.

A six-forecast first run scores Brier 0.185 / skill 0.26 descriptively;
a four-forecast second run aggregates to ten resolved forecasts with
Brier 0.129 / skill 0.484. The in-memory mode shows no file before the
append and six restored records after it. Duplicate ids, tampered
checksums, corrupt lines, missing stores and lock states are named.
"""

import argparse
import json
import os
import tempfile
import time
from pathlib import Path

from calibration import summary
from calibration_store import (append_forecasts, load_forecasts,
                               verify_forecast_file)

MODES = ("in-memory", "first-run", "aggregated", "duplicate", "tampered",
         "corrupt-line", "missing", "stale-lock", "fresh-lock")
AT = "2026-11-07T00:00:00Z"
FIRST = (
    ("run1:0", 0.9, 1), ("run1:1", 0.8, 1), ("run1:2", 0.7, 0),
    ("run1:3", 0.6, 1), ("run1:4", 0.5, 0), ("run1:5", 0.4, 0),
)
SECOND = (
    ("run2:0", 0.8, 1), ("run2:1", 0.7, 1),
    ("run2:2", 0.2, 0), ("run2:3", 0.1, 0),
)


def _forecasts(rows):
    return [{"id": identifier, "probability": probability,
             "outcome": outcome} for identifier, probability, outcome in rows]


def _stats(records):
    stats = summary(records, min_resolved=10)
    return {
        "records": len(records),
        "resolved": stats["counts"]["resolved"],
        "ignored": stats["counts"]["ignored"],
        "brier": stats["brier"],
        "skill": stats["skill"],
        "warnings": stats["warnings"],
    }


def measure_case(mode="first-run", directory=None):
    if directory is None:
        raise ValueError("directory is required")
    path = os.path.join(directory, "forecasts-%s.jsonl" % mode)
    result = {"mode": mode, "ok": None, "findings": [], "records": 0,
              "resolved": 0, "ignored": 0, "brier": None, "skill": None,
              "warnings": [], "first_brier": None, "first_skill": None,
              "file_before": False, "file_after": False,
              "lock_exists": None, "error": None}
    if mode == "in-memory":
        forecasts = _forecasts(FIRST)
        result["in_memory"] = _stats(forecasts)
        result["file_before"] = Path(path).exists()
        append_forecasts(forecasts, path, at=AT)
        loaded = load_forecasts(path)
        verified = verify_forecast_file(path)
        result.update(_stats(loaded))
        result.update({"ok": verified["ok"],
                       "findings": verified["findings"],
                       "file_after": Path(path).exists()})
        return result
    if mode == "missing":
        loaded = load_forecasts(path)
        verified = verify_forecast_file(path)
        result.update({"ok": verified["ok"],
                       "findings": verified["findings"],
                       "records": len(loaded)})
        return result
    if mode == "stale-lock":
        lock = Path(path + ".lock")
        lock.write_text("1:1\n", encoding="utf-8")
        old = time.time() - 60
        os.utime(lock, (old, old))
        append_forecasts(_forecasts(FIRST[:1]), path, at=AT)
        verified = verify_forecast_file(path)
        loaded = load_forecasts(path)
        result.update(_stats(loaded))
        result.update({"ok": verified["ok"],
                       "findings": verified["findings"],
                       "lock_exists": lock.exists(),
                       "file_after": Path(path).exists()})
        return result
    if mode == "fresh-lock":
        lock = Path(path + ".lock")
        lock.write_text("1:1\n", encoding="utf-8")
        try:
            append_forecasts(_forecasts(FIRST[:1]), path, at=AT,
                             lock_timeout=0.0)
        except TimeoutError as exc:
            result["error"] = str(exc)
        result["file_after"] = Path(path).exists()
        return result
    if mode == "duplicate":
        append_forecasts(_forecasts(FIRST), path, at=AT)
        try:
            append_forecasts(_forecasts(FIRST[:1]), path, at=AT)
        except ValueError as exc:
            result["error"] = str(exc)
        verified = verify_forecast_file(path)
        loaded = load_forecasts(path)
        result.update(_stats(loaded))
        result.update({"ok": verified["ok"],
                       "findings": verified["findings"],
                       "file_after": Path(path).exists()})
        return result
    if mode == "tampered":
        append_forecasts(_forecasts(FIRST), path, at=AT)
        lines = Path(path).read_text(encoding="utf-8").splitlines(True)
        record = json.loads(lines[0])
        record["probability"] = 0.1
        lines[0] = json.dumps(record) + "\n"
        Path(path).write_text("".join(lines), encoding="utf-8")
        verified = verify_forecast_file(path)
        try:
            load_forecasts(path)
        except ValueError as exc:
            result["error"] = str(exc)
        result.update({"ok": verified["ok"],
                       "findings": verified["findings"],
                       "file_after": Path(path).exists()})
        return result
    if mode == "corrupt-line":
        append_forecasts(_forecasts(FIRST), path, at=AT)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write("{bad json\n")
        verified = verify_forecast_file(path)
        try:
            load_forecasts(path)
        except ValueError as exc:
            result["error"] = str(exc)
        result.update({"ok": verified["ok"],
                       "findings": verified["findings"],
                       "file_after": Path(path).exists()})
        return result
    append_forecasts(_forecasts(FIRST), path, at=AT)
    if mode == "aggregated":
        first = _stats(load_forecasts(path))
        append_forecasts(_forecasts(SECOND), path, at=AT)
        result["first_brier"] = first["brier"]
        result["first_skill"] = first["skill"]
    loaded = load_forecasts(path)
    verified = verify_forecast_file(path)
    result.update(_stats(loaded))
    result.update({"ok": verified["ok"],
                   "findings": verified["findings"],
                   "file_after": Path(path).exists()})
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
