"""Episode-header battery: recompute episode_sha256 from the logged seed.

A T3:15 header carries seed 15, budget 200, the policy digest and the
episode digest; rebuilding GridWorld(task, 15) and input_digest
reproduces it. Changing the seed or episode, or omitting the seed/header,
is named. Claim refs can opt into the same check; membership-only still
passes the tampered header.
"""

import argparse
import json
import os
import tempfile
from pathlib import Path

from agent import Agent
from claims import ClaimLedger
from claims_verify import verify_claim_refs
from episode_verify import verify_episode_header
from telemetry.log import Telemetry

MODES = ("intact", "wrong-seed", "wrong-episode", "missing-seed",
         "missing-header", "claims", "claims-tampered")
AT = "2026-11-07T00:00:00Z"


def _run(tmp, name):
    path = os.path.join(tmp, name + ".jsonl")
    Agent().run_task_logged("T3_navigate", 15, max_steps=200,
                            log_path=path)
    return path


def _rewrite_header(path, mutate):
    lines = Path(path).read_text(encoding="utf-8").splitlines(True)
    header = json.loads(lines[0])
    mutate(header)
    lines[0] = json.dumps(header, sort_keys=True) + "\n"
    Path(path).write_text("".join(lines), encoding="utf-8")


def _ledger(episode):
    ledger = ClaimLedger()
    ledger.add("T3:15 takes 13 steps", "steps != 13")
    ledger.record("C1", "supports", "actual=13", at=AT, ref=episode)
    return ledger


def measure_case(mode="intact", directory=None):
    if directory is None:
        raise ValueError("directory is required")
    result = {"mode": mode, "headers": 0, "seed": None,
              "episode_prefix": None, "recomputed_prefix": None,
              "ok": None, "findings": [], "verified": None,
              "error": None}
    if mode == "missing-seed":
        path = os.path.join(directory, "missing-seed.jsonl")
        Telemetry(path).write_header("T3_navigate", 200,
                                     episode_sha256="a" * 64)
        verified = verify_episode_header(path)
        result.update({"headers": verified["headers"],
                       "ok": verified["ok"],
                       "findings": verified["findings"]})
        return result
    if mode == "missing-header":
        path = os.path.join(directory, "missing-header.jsonl")
        Telemetry(path).append_action(0, "step", {"i": 0})
        verified = verify_episode_header(path)
        result.update({"headers": verified["headers"],
                       "ok": verified["ok"],
                       "findings": verified["findings"]})
        return result
    path = _run(directory, mode)
    header = Telemetry(path).read_all()[0]
    episode = header["episode_sha256"]
    if mode == "wrong-seed":
        _rewrite_header(path, lambda value: value.__setitem__("seed", 16))
    elif mode in ("wrong-episode", "claims-tampered"):
        _rewrite_header(path, lambda value:
                        value.__setitem__("episode_sha256", "0" * 64))
    verified = verify_episode_header(path)
    result.update({"headers": verified["headers"],
                   "seed": header.get("seed"),
                   "episode_prefix": episode[:12],
                   "recomputed_prefix": (
                       verified["results"][0]["recomputed"][:12]
                       if verified["results"] else None),
                   "ok": verified["ok"],
                   "findings": verified["findings"]})
    if mode in ("claims", "claims-tampered"):
        ref = "0" * 64 if mode == "claims-tampered" else episode
        ledger = _ledger(ref)
        if mode == "claims":
            checked = verify_claim_refs(ledger, path, verify_episodes=True)
            result["verified"] = checked["verified"]
        else:
            try:
                verify_claim_refs(ledger, path, verify_logs=False,
                                  verify_episodes=True)
            except ValueError as exc:
                result["error"] = str(exc)
            membership = verify_claim_refs(ledger, path, verify_logs=False)
            result["verified"] = membership["verified"]
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
