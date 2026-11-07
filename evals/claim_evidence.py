"""Claim/evidence battery: verdict refs cite logged episode digests.

A logged T3:15 run exposes its episode digest in the header; a supports
verdict carrying that ref survives claim-store save/load and matches the
header. Two runs keep distinct refs. A legacy payload without ref loads
with ref None, and an invalid ref leaves the verdict history unchanged.
"""

import argparse
import json
import os
import tempfile

from agent import Agent
from claims import ClaimLedger
from claims_store import load_ledger, save_ledger, verify_ledger_file
from telemetry.log import Telemetry

MODES = ("single", "two-runs", "legacy", "invalid")
STAMP = 1700000000.0
AT = "2026-11-07T00:00:00Z"


def _run(tmp, task, seed, name):
    log_path = os.path.join(tmp, name + ".jsonl")
    trace = Agent().run_task_logged(task, seed, max_steps=200,
                                    log_path=log_path)
    header = Telemetry(log_path).read_all()[0]
    return trace, header


def measure_case(mode="single", directory=None):
    if directory is None:
        raise ValueError("directory is required")
    result = {"mode": mode, "steps": 0, "episode_prefix": None,
              "ref_prefix": None, "ref_matches_header": None,
              "claims": 0, "verdicts": 0, "status": None,
              "store_ok": None, "legacy_none": None, "error": None}
    if mode == "legacy":
        payload = {
            "claims": [{
                "id": "C1", "text": "legacy", "kill_test": "never",
                "status": "supported", "confidence": 0.5,
                "verdicts": [{"status": "supports", "evidence": "old",
                              "at": AT}],
            }]
        }
        ledger = ClaimLedger.from_dict(payload)
        result.update({"claims": len(ledger.claims()),
                       "verdicts": len(ledger.get("C1").verdicts),
                       "status": ledger.get("C1").status,
                       "legacy_none": ledger.get("C1").verdicts[0].ref
                       is None})
        return result
    if mode == "invalid":
        ledger = ClaimLedger()
        ledger.add("text", "kill")
        try:
            ledger.record("C1", "supports", "ok", at=AT, ref="")
        except ValueError as exc:
            result["error"] = str(exc)
        result.update({"claims": len(ledger.claims()),
                       "verdicts": len(ledger.get("C1").verdicts),
                       "status": ledger.get("C1").status})
        return result
    trace, first_header = _run(directory, "T3_navigate", 15,
                               "first-" + mode)
    first_episode = first_header["episode_sha256"]
    path = os.path.join(directory, "claims-%s.json" % mode)
    ledger = ClaimLedger()
    ledger.add("T3:15 takes 13 steps", "steps != 13")
    ledger.record("C1", "supports", "actual=13", at=AT, ref=first_episode)
    result.update({"steps": len(trace),
                   "episode_prefix": first_episode[:12],
                   "ref_prefix": first_episode[:12]})
    if mode == "two-runs":
        _, second_header = _run(directory, "T3_navigate", 65,
                                "second-" + mode)
        second_episode = second_header["episode_sha256"]
        ledger.add("T3:65 takes 6 steps", "steps != 6")
        ledger.record("C2", "supports", "actual=6", at=AT,
                      ref=second_episode)
        result["second_episode_prefix"] = second_episode[:12]
        result["refs_distinct"] = first_episode != second_episode
    save_ledger(ledger, path, saved_at=STAMP)
    loaded = load_ledger(path)
    verified = verify_ledger_file(path)
    refs = [claim.verdicts[0].ref for claim in loaded.claims()]
    result.update({"claims": len(loaded.claims()),
                   "verdicts": sum(len(c.verdicts)
                                   for c in loaded.claims()),
                   "status": loaded.get("C1").status,
                   "ref_matches_header": refs[0] == first_episode,
                   "store_ok": verified["ok"]})
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
