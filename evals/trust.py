"""Backend-trust battery: stalled legal proposals versus the rule fallback.

A deterministic backend returns the legal token "wait" every step. With
the default trust window the planner accepts it until the hub reports
20 consecutive unrewarded steps, then rejects it in favor of the rule
action and stays match-only for the rest of the episode. ``trust_window=None``
is the ablation: the same backend and prompts run, but every legal
proposal is accepted, so the run stalls at the cap.

Reports behavior (success, steps, reward, transfer, recovery) and the
model-seam trace (proposed/rule/steps_since_reward/accepted, fallback
and call counts, first prompt hash). No weights or committed logs.
"""

import argparse
import hashlib
import json
import os
import tempfile

from agent import Agent, Planner, model_label, policy_digest
from evals.coldstart import _trace_slot
from evals.recompute import recompute
from models.backend import ModelBackend
from models.llamacpp import build_prompt
from models.manifest import canonical, manifest_for
from telemetry.log import Telemetry
from worlds.grid import GridWorld

CASES = (
    ("T1_forage", 71),
    ("T2_delayed_match", 3),
    ("T3_navigate", 15),
    ("T3_navigate", 65),
)

DEFAULT_TRUST_WINDOW = 20


class WaitingBackend(ModelBackend):
    """Legal but stalled proposal: never moves or rewards."""

    def __init__(self):
        self.calls = 0
        self.seen = []

    def generate(self, observation):
        self.calls += 1
        self.seen.append(json.loads(json.dumps(observation, sort_keys=True)))
        return "wait"


def _actions_digest(trace):
    body = canonical([record["action"] for record in trace])
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _decisions(steps):
    out = []
    for record in steps:
        probe = record.get("args", {}).get("probe")
        if isinstance(probe, dict) and isinstance(probe.get("model_decision"), dict):
            out.append(probe["model_decision"])
    return out


def _prompt_sha256(observation, seed):
    prompt = build_prompt(observation)
    return manifest_for(
        prompt, observation, model_id="WaitingBackend",
        checkpoint="WaitingBackend",
        sampling={"temperature": 0.0, "seed": seed,
                  "n_predict": 0, "cache_prompt": True},
    )["sha256"]


def measure_case(task, seed, directory, trust_window=DEFAULT_TRUST_WINDOW,
                 max_steps=200):
    backend = WaitingBackend()
    planner = Planner(backend=backend, trust_window=trust_window)
    agent = Agent(planner=planner, world=GridWorld(task, seed))
    log_path = os.path.join(directory, "%s-%d.jsonl" % (task, seed))
    tel = Telemetry(log_path)
    tel.write_header(task, max_steps, policy="trust-battery",
                     policy_sha256=policy_digest(),
                     model=model_label(backend))
    agent.telemetry_log = tel
    trace = agent.run(max_steps=max_steps)
    reward = sum(record["reward"] for record in trace)
    done = bool(trace[-1]["done"])
    success = done and reward > 0.0
    tel.append_action(9001, "eval_transfer",
                      {"naive_steps": float(max_steps),
                       "reuse_steps": float(len(trace))})
    tel.append_action(9002, "eval_recovery",
                      {"time_outside": 0.0 if success else float(len(trace)),
                       "window": float(max_steps)})
    tel.write_verdict("done" if success else "truncated",
                      "steps=%d" % len(trace))
    steps = [record for record in Telemetry(log_path).read_all()
             if record.get("type") == "action" and record.get("kind") == "step"]
    decisions = _decisions(steps)
    first_obs = backend.seen[0]
    return {
        "task": task,
        "seed": seed,
        "steps": len(trace),
        "reward": reward,
        "success": success,
        "fallbacks": planner.fallbacks,
        "model_calls": backend.calls,
        "rejected_steps": sum(1 for item in decisions if not item["accepted"]),
        "decision_first": decisions[0] if decisions else None,
        "decision_last": decisions[-1] if decisions else None,
        "action_sha256": _actions_digest(trace),
        "prompt_sha256": _prompt_sha256(first_obs, seed),
        "trace": _trace_slot(recompute(log_path)),
    }


def run_battery(cases=CASES, trust_window=DEFAULT_TRUST_WINDOW, max_steps=200):
    """Measure every case in one temporary directory."""
    with tempfile.TemporaryDirectory() as directory:
        results = [measure_case(task, seed, directory,
                                trust_window=trust_window,
                                max_steps=max_steps)
                   for task, seed in cases]
        return {
            "policy_sha256": policy_digest(),
            "model": "WaitingBackend",
            "trust_window": trust_window,
            "max_steps": max_steps,
            "cases": results,
        }


def _parse_case(text):
    task, seed = text.rsplit(":", 1)
    for known, known_seed in CASES:
        if known == task and known_seed == int(seed):
            return known, known_seed
    raise ValueError("unknown case: %s" % text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", action="append", default=[],
                        help="task:seed; repeatable (default: all cases)")
    parser.add_argument("--ablate", action="store_true",
                        help="disable the trust window (raw backend control)")
    parser.add_argument("--max-steps", type=int, default=200)
    args = parser.parse_args()
    cases = tuple(_parse_case(text) for text in args.case) if args.case else CASES
    trust_window = None if args.ablate else DEFAULT_TRUST_WINDOW
    print(json.dumps(run_battery(cases, trust_window=trust_window,
                                 max_steps=args.max_steps),
                     indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
