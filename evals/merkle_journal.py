"""Merkle journal battery: chained batches and retained historical proofs.

A 24-record log gets a first 8-record batch; 8 more records get a second
batch. The journal retains both roots with ``prev``/``hash`` links, so
record 20 proves against batch 1 after batch 2 is written. The modes
show intact verification, a truncated log, a deleted first anchor, a
resigned tampered root, a refused range rollback, a missing journal,
and the old single-anchor overwrite (where the earlier proof is lost).
The single anchor is unchanged; the journal is a separate sidecar and
is never committed.
"""

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

from telemetry.log import Telemetry
from telemetry.merkle import (append_merkle_anchor,
                              merkle_proof_for_journal_record,
                              merkle_proof_for_record, verify_merkle_anchor,
                              verify_merkle_journal, verify_merkle_proof,
                              write_merkle_anchor)

MODES = ("intact", "truncated", "deleted-first", "tampered-root",
         "rollback", "missing", "single-anchor")
STAMP = "2026-11-07T00:00:00Z"


def _log(path, records):
    tel = Telemetry(path)
    for index in range(records):
        tel.append_action(index, "step", {"i": index})


def _truncate(path, keep):
    lines = Path(path).read_text(encoding="utf-8").splitlines(True)
    Path(path).write_text("".join(lines[:keep]), encoding="utf-8")


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _resign(record):
    body = {key: value for key, value in record.items() if key != "hash"}
    record["hash"] = hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()
    return record


def _two_batches(path):
    _log(path, 24)
    first = append_merkle_anchor(path, batch_size=8, created_at=STAMP)
    _log(path, 8)
    second = append_merkle_anchor(path, batch_size=8, created_at=STAMP)
    return first, second, path + ".merkle.journal"


def _history(path, journal, index=20):
    try:
        proof = merkle_proof_for_journal_record(path, journal, index)
        return proof["batch"], verify_merkle_proof(proof), None
    except ValueError as exc:
        return None, False, str(exc)


def measure_case(mode="intact", directory=None):
    if directory is None:
        raise ValueError("directory is required")
    path = os.path.join(directory, "run-%s.jsonl" % mode)
    journal = path + ".merkle.journal"
    result = {"mode": mode, "anchors": 0, "latest_start": None,
              "latest_end": None, "journal_ok": None, "findings": [],
              "history_batch": None, "history_ok": None,
              "latest_proof_ok": None, "error": None}
    if mode == "single-anchor":
        _log(path, 24)
        write_merkle_anchor(path, batch_size=8, created_at=STAMP)
        _log(path, 8)
        write_merkle_anchor(path, batch_size=8, created_at=STAMP)
        anchor = verify_merkle_anchor(path, path + ".merkle")
        result.update({"anchors": 1, "latest_start": anchor["start"],
                       "latest_end": anchor["end"],
                       "journal_ok": anchor["ok"],
                       "findings": anchor["findings"]})
        try:
            proof = merkle_proof_for_record(path, path + ".merkle", 20)
            result["history_ok"] = verify_merkle_proof(proof)
        except ValueError as exc:
            result["history_ok"] = False
            result["error"] = str(exc)
        return result
    if mode == "missing":
        _log(path, 4)
        verified = verify_merkle_journal(path, journal)
        result.update({"journal_ok": verified["ok"],
                       "findings": verified["findings"]})
        return result
    if mode == "rollback":
        _log(path, 24)
        append_merkle_anchor(path, batch_size=8, created_at=STAMP)
        _truncate(path, 16)
        try:
            append_merkle_anchor(path, batch_size=8, created_at=STAMP)
        except ValueError as exc:
            result["error"] = str(exc)
        result["journal_ok"] = result["error"] is None
        return result
    _two_batches(path)
    if mode == "truncated":
        _truncate(path, 30)
    elif mode == "deleted-first":
        lines = Path(journal).read_text(encoding="utf-8").splitlines(True)
        Path(journal).write_text("".join(lines[1:]), encoding="utf-8")
    elif mode == "tampered-root":
        records = [json.loads(line) for line in
                   Path(journal).read_text(encoding="utf-8").splitlines()]
        records[1]["root"] = "0" * 64
        _resign(records[1])
        Path(journal).write_text(
            "".join(json.dumps(record, sort_keys=True) + "\n"
                    for record in records), encoding="utf-8")
    verified = verify_merkle_journal(path, journal)
    batch, history_ok, error = _history(path, journal)
    latest_batch, latest_ok, _ = _history(path, journal, 28)
    result.update({
        "anchors": verified["anchors"],
        "latest_start": (verified["latest"] or {}).get("start"),
        "latest_end": (verified["latest"] or {}).get("end"),
        "journal_ok": verified["ok"],
        "findings": verified["findings"],
        "history_batch": batch,
        "history_ok": history_ok,
        "latest_proof_ok": latest_ok,
        "error": error,
    })
    if latest_batch is None:
        result["latest_proof_ok"] = False
    return result


def run_battery(modes=MODES):
    with tempfile.TemporaryDirectory() as directory:
        return {
            "model": "rule",
            "modes": list(modes),
            "cases": [measure_case(mode, directory) for mode in modes],
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", action="append", choices=MODES, default=[],
                        help="repeatable (default: all modes)")
    args = parser.parse_args()
    modes = tuple(args.mode) if args.mode else MODES
    print(json.dumps(run_battery(modes), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
