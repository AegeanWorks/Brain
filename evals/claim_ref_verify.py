"""Claim-ref battery: verdict refs checked against live log headers.

Two logged runs carry two episode digests. Claims referencing both verify
2/2; verifying against only the first leaves the second unverified; a
fabricated ref is named; a verdict without a ref is unreferenced; the
claim store loads and verifies; a headerless/missing log is refused.
"""

import argparse
import json
import os
import tempfile
from pathlib import Path

from agent import Agent
from claims import ClaimLedger
from claims_store import save_ledger
from claims_verify import verify_claim_refs, verify_claim_store
from telemetry.log import Telemetry

MODES = ("verified", "missing-log", "fabricated", "unreferenced", "store",
         "no-header", "missing-file")
STAMP = 1700000000.0
AT = "2026-11-07T00:00:00Z"


def _run(tmp, task, seed, name):
    path = os.path.join(tmp, name + ".jsonl")
    Agent().run_task_logged(task, seed, max_steps=200, log_path=path)
    header = Telemetry(path).read_all()[0]
    return header["episode_sha256"], path


def _ledger(one, two=None):
    ledger = ClaimLedger()
    ledger.add("T3:15 takes 13 steps", "steps != 13")
    ledger.record("C1", "supports", "actual=13", at=AT, ref=one)
    if two is not None:
        ledger.add("T3:65 takes 6 steps", "steps != 6")
        ledger.record("C2", "supports", "actual=6", at=AT, ref=two)
    return ledger


def _summary(ledger):
    return {"claims": len(ledger.claims()),
            "verdicts": sum(len(c.verdicts) for c in ledger.claims())}


def measure_case(mode="verified", directory=None):
    if directory is None:
        raise ValueError("directory is required")
    result = {"mode": mode, "claims": 0, "verdicts": 0, "verified": 0,
              "unverified": 0, "unreferenced": 0, "episodes": 0,
              "ok": None, "findings": [], "error": None}
    if mode == "missing-file":
        ledger = _ledger("f" * 64)
        try:
            verify_claim_refs(ledger, os.path.join(directory, "missing.jsonl"))
        except ValueError as exc:
            result["error"] = str(exc)
        result.update(_summary(ledger))
        return result
    if mode == "no-header":
        path = os.path.join(directory, "no-header.jsonl")
        Telemetry(path).append_action(0, "step", {"i": 0})
        ledger = _ledger("f" * 64)
        try:
            verify_claim_refs(ledger, path)
        except ValueError as exc:
            result["error"] = str(exc)
        result.update(_summary(ledger))
        return result
    first, log1 = _run(directory, "T3_navigate", 15, "first-" + mode)
    second, log2 = _run(directory, "T3_navigate", 65, "second-" + mode)
    if mode == "fabricated":
        ledger = _ledger("f" * 64)
        logs = log1
    elif mode == "unreferenced":
        ledger = ClaimLedger()
        ledger.add("unreferenced", "never")
        ledger.record("C1", "supports", "no ref", at=AT)
        logs = [log1, log2]
    elif mode == "store":
        ledger = _ledger(first, second)
        store = os.path.join(directory, "claims-store.json")
        save_ledger(ledger, store, saved_at=STAMP)
        result.update(_summary(ledger))
        verified = verify_claim_store(store, [log1, log2])
        result.update({"verified": verified["verified"],
                       "unverified": verified["unverified"],
                       "unreferenced": verified["unreferenced"],
                       "episodes": len(verified["episodes"]),
                       "ok": verified["ok"],
                       "findings": verified["findings"]})
        return result
    else:
        ledger = _ledger(first, second)
        logs = [log1, log2] if mode == "verified" else log1
    verified = verify_claim_refs(ledger, logs)
    result.update(_summary(ledger))
    result.update({"verified": verified["verified"],
                   "unverified": verified["unverified"],
                   "unreferenced": verified["unreferenced"],
                   "episodes": len(verified["episodes"]),
                   "ok": verified["ok"],
                   "findings": verified["findings"]})
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
