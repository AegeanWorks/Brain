"""Episode-header battery: recompute episode_sha256 from the logged seed.

A T3:15 header carries seed 15, budget 200, the policy digest and the
episode digest; rebuilding GridWorld(task, 15) and input_digest
reproduces it. Changing the seed or episode, or omitting the seed/header,
is named. Claim refs can opt into the same check; membership-only still
passes the tampered header. An optional expected-policy pin catches a
forged policy whose episode digest is internally consistent.
"""

import argparse
import json
import os
import tempfile
from pathlib import Path

from agent import Agent, policy_digest
from claims import ClaimLedger
from claims_verify import verify_claim_refs
from episode_verify import verify_episode_header
from identity import input_digest
from telemetry.log import Telemetry
from worlds.grid import GridWorld

MODES = ("intact", "wrong-seed", "wrong-episode", "missing-seed",
         "missing-header", "claims", "claims-tampered", "policy-current",
         "policy-wrong", "policy-forged", "claims-policy")
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
              "internal_ok": None, "error": None}
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
    if mode == "policy-forged":
        path = os.path.join(directory, "policy-forged.jsonl")
        fake_policy = "f" * 64
        state = GridWorld("T3_navigate", 15).reset()
        fake_episode, _projection = input_digest(state, {
            "task": "T3_navigate", "seed": 15, "max_steps": 200,
            "policy_sha256": fake_policy,
        })
        Telemetry(path).write_header(
            "T3_navigate", 200, seed=15, policy_sha256=fake_policy,
            episode_sha256=fake_episode)
        internal = verify_episode_header(path)
        pinned = verify_episode_header(
            path, expected_policy_sha256=policy_digest())
        result.update({"headers": pinned["headers"], "seed": 15,
                       "episode_prefix": fake_episode[:12],
                       "recomputed_prefix": fake_episode[:12],
                       "ok": pinned["ok"],
                       "findings": pinned["findings"],
                       "internal_ok": internal["ok"]})
        return result
    path = _run(directory, mode)
    header = Telemetry(path).read_all()[0]
    episode = header["episode_sha256"]
    if mode == "wrong-seed":
        _rewrite_header(path, lambda value: value.__setitem__("seed", 16))
    elif mode in ("wrong-episode", "claims-tampered"):
        _rewrite_header(path, lambda value:
                        value.__setitem__("episode_sha256", "0" * 64))
    expected = None
    if mode == "policy-current":
        expected = policy_digest()
    elif mode == "policy-wrong":
        expected = "0" * 64
    verified = verify_episode_header(
        path, expected_policy_sha256=expected)
    result.update({"headers": verified["headers"],
                   "seed": header.get("seed"),
                   "episode_prefix": episode[:12],
                   "recomputed_prefix": (
                       verified["results"][0]["recomputed"][:12]
                       if verified["results"] else None),
                   "ok": verified["ok"],
                   "findings": verified["findings"]})
    if mode in ("claims", "claims-tampered", "claims-policy"):
        ref = "0" * 64 if mode == "claims-tampered" else episode
        ledger = _ledger(ref)
        if mode == "claims":
            checked = verify_claim_refs(ledger, path, verify_episodes=True)
            result["verified"] = checked["verified"]
        elif mode == "claims-policy":
            checked = verify_claim_refs(
                ledger, path, verify_episodes=True,
                expected_policy_sha256=policy_digest())
            result["verified"] = checked["verified"]
            try:
                verify_claim_refs(
                    ledger, path, verify_episodes=True,
                    expected_policy_sha256="0" * 64)
            except ValueError as exc:
                result["error"] = str(exc)
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
