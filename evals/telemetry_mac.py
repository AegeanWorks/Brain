"""Keyed telemetry battery: HMAC-signed records and named tamper findings.

A keyed log carries an HMAC-SHA256 ``mac`` on every record. The battery
shows: correct key passes; wrong key, missing MAC and a payload edit with
a recomputed digest are named; an unkeyed log still verifies unkeyed and
reports missing-mac when a key is supplied. Test keys are derived here,
never read from the environment or a repository file.
"""

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

from telemetry.log import Telemetry, _digest_of, verify_chain

KEY = hashlib.sha256(b"brain-hmac-eval-key").digest()
WRONG = hashlib.sha256(b"brain-hmac-eval-wrong").digest()
MODES = ("keyed", "wrong-key", "missing-mac", "tampered",
         "unkeyed", "unkeyed-keyed")


def _build(path, key=KEY):
    tel = Telemetry(path, hmac_key=key)
    tel.write_header("T3_navigate", 200, policy="hmac-battery")
    for index in range(3):
        tel.append_action(index, "step", {"i": index})
        tel.append_result(index, True, "step", 1.0)
    tel.write_verdict("done", "steps=3 reward=1.0")
    return tel


def _rewrite(path, mutate):
    lines = Path(path).read_text(encoding="utf-8").splitlines(True)
    records = [json.loads(line) for line in lines]
    mutate(records)
    Path(path).write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n"
                for record in records),
        encoding="utf-8")


def measure_case(mode="keyed", directory=None):
    if directory is None:
        raise ValueError("directory is required")
    path = os.path.join(directory, "run-%s.jsonl" % mode)
    key = None if mode in ("unkeyed", "unkeyed-keyed") else KEY
    _build(path, key=key)
    if mode == "missing-mac":
        _rewrite(path, lambda records: records[0].pop("mac"))
    elif mode == "tampered":
        def _tamper(records):
            records[0]["task"] = "tampered"
            records[0]["digest"] = _digest_of(records[0])
        _rewrite(path, _tamper)
    records = Telemetry(path).read_all()
    verify_key = KEY if mode in ("keyed", "wrong-key", "missing-mac",
                                 "tampered", "unkeyed-keyed") else None
    if mode == "wrong-key":
        verify_key = WRONG
    result = verify_chain(path, hmac_key=verify_key)
    return {
        "mode": mode,
        "records": len(records),
        "mac_count": sum(1 for record in records
                         if isinstance(record.get("mac"), str)),
        "ok": result["ok"],
        "findings": result["findings"],
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
