"""Header-reader battery: streaming headers vs decoding every record.

Episode and claim verification only need header records. `read_all`
parses and retains every action; `read_headers` streams the file and
retains only headers. The battery writes a 100k-record log and reports
retained objects, peak Python memory and wall time for both readers.
"""

import argparse
import json
import os
import tempfile
import time
import tracemalloc

from telemetry.log import Telemetry

MODES = ("all", "headers")
RECORDS = 100_000


def _write_log(path):
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps({
            "schema": 2, "seq": 0, "type": "header", "ts": 0.0,
            "task": "T3_navigate", "budget": 200,
            "episode_sha256": "a" * 64,
        }, sort_keys=True) + "\n")
        for index in range(RECORDS):
            handle.write(json.dumps({
                "schema": 2, "seq": index + 1, "type": "action",
                "kind": "step", "ts": 0.0, "args": {"i": index},
                "M": [0, 1], "P": [0, 0], "S": [0, 1],
                "hub": [0, 0, 0],
            }, sort_keys=True) + "\n")


def measure_case(mode, directory):
    path = os.path.join(directory, "run-%s.jsonl" % mode)
    _write_log(path)
    tel = Telemetry(path)
    tracemalloc.start()
    started = time.perf_counter()
    if mode == "all":
        records = tel.read_all()
        headers = [row for row in records
                   if row.get("type") == "header"]
    else:
        headers = tel.read_headers()
        records = None
    elapsed = time.perf_counter() - started
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "mode": mode,
        "lines": RECORDS + 1,
        "returned": len(records) if records is not None else len(headers),
        "headers": len(headers),
        "peak_bytes": peak,
        "seconds": elapsed,
    }


def run_battery(modes=MODES):
    with tempfile.TemporaryDirectory() as directory:
        return {"model": "rule", "lines": RECORDS + 1,
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
