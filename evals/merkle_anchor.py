"""Merkle batch-anchor battery: root, proof, truncation and tamper.

A 20-record log is anchored over its last 8 records. ``intact`` verifies
the root and a detached proof for record 15; ``truncated`` cuts the log
to 15; ``tampered-root`` edits the anchor root; ``tampered-record``
changes a batch digest; ``proof-tampered`` changes the proof leaf. The
linear chain and the rule behavior are untouched; only the batch
commitment and its findings change.
"""

import argparse
import json
import os
import tempfile
from pathlib import Path

from telemetry.log import Telemetry
from telemetry.merkle import (merkle_proof_for_record, verify_merkle_anchor,
                              verify_merkle_proof, write_merkle_anchor)

MODES = ("intact", "truncated", "tampered-root", "tampered-record",
         "proof-tampered", "missing")
STAMP = "2026-11-07T00:00:00Z"


def _build(path, records=20):
    tel = Telemetry(path)
    for index in range(records):
        tel.append_action(index, "step", {"i": index})
    return tel


def _truncate(path, keep):
    lines = Path(path).read_text(encoding="utf-8").splitlines(True)
    Path(path).write_text("".join(lines[:keep]), encoding="utf-8")


def measure_case(mode="intact", directory=None):
    if directory is None:
        raise ValueError("directory is required")
    path = os.path.join(directory, "run-%s.jsonl" % mode)
    _build(path, 20)
    if mode != "missing":
        write_merkle_anchor(path, batch_size=8, created_at=STAMP)
    anchor_path = path + ".merkle"
    if mode == "truncated":
        _truncate(path, 15)
    elif mode == "tampered-root":
        anchor = json.loads(Path(anchor_path).read_text(encoding="utf-8"))
        anchor["root"] = "0" * 64
        Path(anchor_path).write_text(json.dumps(anchor), encoding="utf-8")
    elif mode == "tampered-record":
        lines = Path(path).read_text(encoding="utf-8").splitlines(True)
        record = json.loads(lines[15])
        record["digest"] = "b" * 64
        lines[15] = json.dumps(record, sort_keys=True) + "\n"
        Path(path).write_text("".join(lines), encoding="utf-8")
    anchor_result = verify_merkle_anchor(path, anchor_path)
    proof_ok = None
    proof_size = None
    if mode != "missing":
        try:
            proof = merkle_proof_for_record(path, anchor_path, 15)
            proof_size = len(proof["proof"])
            if mode == "proof-tampered":
                proof["leaf"] = "0" * 64
            proof_ok = verify_merkle_proof(proof)
        except ValueError:
            proof_ok = False
    return {
        "mode": mode,
        "records": len(Telemetry(path).read_all()),
        "anchor_ok": anchor_result["ok"],
        "findings": anchor_result["findings"],
        "root": anchor_result["root"],
        "start": anchor_result["start"],
        "end": anchor_result["end"],
        "count": anchor_result["count"],
        "proof_ok": proof_ok,
        "proof_size": proof_size,
        "detected": (not anchor_result["ok"]) or proof_ok is False,
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
