"""Claim-store battery: durable snapshots vs the in-memory ledger.

The in-memory ClaimLedger is lost on exit. The store writes one
checksummed snapshot, keeps the previous snapshot as ``.bak``, recovers
from a corrupt primary, and refuses to write behind a fresh lock.
Modes: roundtrip, corrupt-primary, tampered, missing, stale-lock,
fresh-lock and in-memory (the before/after ablation). Claims are the
same six T3 verdicts used by ``evals.claims``.
"""

import argparse
import json
import os
import tempfile
import time
from pathlib import Path

from claims import ClaimLedger
from claims_store import load_ledger, save_ledger, verify_ledger_file

MODES = ("in-memory", "roundtrip", "corrupt-primary", "tampered",
         "missing", "stale-lock", "fresh-lock")
STAMP = 1700000000.0
AT = "2026-11-07T00:00:00Z"


def _ledger(limit=None):
    ledger = ClaimLedger()
    ledger.add("T3:15 takes 13 steps", "steps != 13", 0.9)
    ledger.record("C1", "supports", "actual=13", at=AT)
    ledger.add("T3:65 takes 13 steps", "steps != 13", 0.8)
    ledger.record("C2", "refutes", "actual=6", at=AT)
    ledger.add("T3:15 reward is 1.0", "reward != 1.0", 0.95)
    ledger.record("C3", "supports", "actual=1.0", at=AT)
    ledger.add("T3:65 reward is 0.0", "reward != 0.0", 0.7)
    ledger.record("C4", "refutes", "actual=1.0", at=AT)
    ledger.add("T3:65 takes 6 steps", "steps != 6", 0.6)
    ledger.record("C5", "supports", "actual=6", at=AT)
    ledger.add("T3:15 energy is zero", "energy != 0", 0.5)
    ledger.record("C6", "inconclusive", "no energy observation", at=AT)
    if limit is None:
        return ledger
    return ClaimLedger(claims=ledger.claims()[:limit])


def _summary(ledger):
    claims = ledger.claims()
    statuses = {"proposed": 0, "supported": 0, "refuted": 0,
                "inconclusive": 0}
    for claim in claims:
        statuses[claim.status] += 1
    return {
        "claims": len(claims),
        "verdicts": sum(len(claim.verdicts) for claim in claims),
        "statuses": statuses,
    }


def measure_case(mode="roundtrip", directory=None):
    if directory is None:
        raise ValueError("directory is required")
    path = os.path.join(directory, "claims-%s.json" % mode)
    result = {"mode": mode, "claims": 0, "verdicts": 0, "ok": None,
              "findings": [], "sha256": None, "loaded_claims": None,
              "quarantine": False, "lock_exists": None,
              "file_before": False, "file_after": False, "error": None}
    if mode == "in-memory":
        ledger = _ledger()
        result.update(_summary(ledger))
        result["file_before"] = Path(path).exists()
        result["loaded_claims"] = 0
        save_ledger(ledger, path, saved_at=STAMP)
        loaded = load_ledger(path)
        verified = verify_ledger_file(path)
        result.update({"claims": verified["claims"],
                       "verdicts": verified["verdicts"],
                       "ok": verified["ok"],
                       "findings": verified["findings"],
                       "sha256": verified["sha256"],
                       "loaded_claims": len(loaded.claims()),
                       "file_after": Path(path).exists()})
        return result
    if mode == "missing":
        loaded = load_ledger(path)
        verified = verify_ledger_file(path)
        result.update({"ok": verified["ok"],
                       "findings": verified["findings"],
                       "loaded_claims": len(loaded.claims())})
        return result
    if mode == "stale-lock":
        lock = Path(path + ".lock")
        lock.write_text("1:1\n", encoding="utf-8")
        old = time.time() - 60
        os.utime(lock, (old, old))
        save_ledger(_ledger(), path, saved_at=STAMP)
        verified = verify_ledger_file(path)
        result.update({"ok": verified["ok"],
                       "findings": verified["findings"],
                       "claims": verified["claims"],
                       "verdicts": verified["verdicts"],
                       "sha256": verified["sha256"],
                       "loaded_claims": len(load_ledger(path).claims())})
        result["lock_exists"] = lock.exists()
        return result
    if mode == "fresh-lock":
        lock = Path(path + ".lock")
        lock.write_text("1:1\n", encoding="utf-8")
        try:
            save_ledger(_ledger(), path, saved_at=STAMP, lock_timeout=0.0)
        except TimeoutError as exc:
            result["error"] = str(exc)
        result["file_after"] = Path(path).exists()
        return result
    if mode == "corrupt-primary":
        save_ledger(_ledger(limit=3), path, saved_at=STAMP)
        save_ledger(_ledger(), path, saved_at=STAMP)
        Path(path).write_text("{not json\n", encoding="utf-8")
        broken = verify_ledger_file(path)
        loaded = load_ledger(path)
        result.update({"ok": broken["ok"],
                       "findings": broken["findings"],
                       "loaded_claims": len(loaded.claims()),
                       "quarantine": Path(path + ".corrupt").exists(),
                       "claims": len(loaded.claims()),
                       "verdicts": sum(len(c.verdicts)
                                      for c in loaded.claims())})
        return result
    if mode == "tampered":
        save_ledger(_ledger(), path, saved_at=STAMP)
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        payload["claims"][0]["text"] = "tampered"
        Path(path).write_text(json.dumps(payload, sort_keys=True) + "\n",
                              encoding="utf-8")
        verified = verify_ledger_file(path)
        try:
            load_ledger(path)
        except ValueError as exc:
            result["error"] = str(exc)
        result.update({"ok": verified["ok"],
                       "findings": verified["findings"],
                       "quarantine": Path(path + ".corrupt").exists()})
        return result
    ledger = _ledger()
    save_ledger(ledger, path, saved_at=STAMP)
    loaded = load_ledger(path)
    verified = verify_ledger_file(path)
    result.update(_summary(loaded))
    result.update({"ok": verified["ok"],
                   "findings": verified["findings"],
                   "sha256": verified["sha256"],
                   "loaded_claims": len(loaded.claims()),
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
