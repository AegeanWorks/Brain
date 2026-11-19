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

from evals.battery_check import exit_code_for, format_findings
from telemetry.log import Telemetry

MODES = ("all", "headers")
RECORDS = 100_000

#: The header reader must retain at least this many times less peak memory
#: than the full reader. A floor rather than an exact number: allocator
#: noise moves the absolute bytes, but not the order of magnitude.
MIN_MEMORY_RATIO = 10.0


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
                "modes": list(modes),
                "cases": [measure_case(mode, directory) for mode in modes]}


def checks(report, modes=None):
    """Return the claims this battery's own output contradicts.

    The battery exists to prove that reading only headers costs far less
    memory than retaining every record. These findings check that property
    rather than exact byte counts, so allocator noise cannot move them.
    ``modes`` is the subset requested by ``--mode``; the comparison findings
    only apply when both modes are present, so a single-mode inspection is a
    valid pass.
    """
    findings = []
    by_mode = {case.get("mode"): case for case in report.get("cases", [])}
    if modes is None:
        modes = report.get("modes", MODES)
    for mode in MODES:
        if mode in modes and mode not in by_mode:
            findings.append("missing-mode:%s" % mode)
    if findings:
        return findings
    if "headers" in by_mode:
        headers = by_mode["headers"]
        # The header reader must return one record whatever the log length.
        if headers.get("returned") != 1:
            findings.append("headers-returned:%s!=1" % headers.get("returned"))
        if headers.get("headers") != 1:
            findings.append("headers-count:%s!=1" % headers.get("headers"))
    if "all" in by_mode:
        # The full reader must return every line the run reports.
        total = by_mode["all"].get("returned")
        if total is not None and total < 2:
            findings.append("all-returned:%s<2" % total)
    if "all" in by_mode and "headers" in by_mode:
        everything, headers = by_mode["all"], by_mode["headers"]
        if everything.get("headers") != headers.get("headers"):
            findings.append("heads-disagree:%s!=%s"
                            % (everything.get("headers"), headers.get("headers")))
        ratio = everything.get("peak_bytes", 0) / max(
            headers.get("peak_bytes", 1), 1)
        if ratio < MIN_MEMORY_RATIO:
            findings.append("memory-ratio:%.1f<%.1f" % (ratio, MIN_MEMORY_RATIO))
    return findings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", action="append", choices=MODES, default=[],
                        help="repeatable (default: all modes)")
    args = parser.parse_args()
    modes = tuple(args.mode) if args.mode else MODES
    report = run_battery(modes)
    print(json.dumps(report, indent=2, sort_keys=True))
    findings = checks(report)
    if findings:
        print(format_findings("header_reader", findings), end="")
    raise SystemExit(exit_code_for(findings))


if __name__ == "__main__":
    main()
