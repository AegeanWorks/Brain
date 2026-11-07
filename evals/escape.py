"""Repeated-position cycle-escape battery: behavior plus model-seam trace.

Two three-obstacle layouts loop under the local viability/pooling rule
and consume the 200-step cap with 0.0 reward. The shipped planner
counts full-episode visits to the current cell; on the second visit it
takes one deterministic BFS step toward the goal, so the episode
completes. The same deterministic backend declines every proposal on
every run, which exercises the model seam without weights: the planner
rule is the actor, and the first observation (therefore the first
prompt hash) is identical across modes.

Modes:
- ``intact``: memory plus cycle escape.
- ``ablate``: ``cycle_escape=False`` restores the loop.
- ``blind``: planner receives no memories; the repeat trigger cannot
  fire, so the loop is restored and the coupling is proven.

Reports success, steps/cost, reward, transfer gain, recovery, fallback
and call counts, first prompt hash, decision readouts, the
``cycle_escape`` probe, and recomputed trace statistics. No weights,
binaries, or committed logs: the battery uses a temporary directory.
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
    ("cycle-a", (6, 5), ((6, 4), (5, 5), (3, 5))),
    ("cycle-b", (6, 4), ((5, 4), (6, 0), (6, 3))),
)

MODES = ("intact", "ablate", "blind")


class _ForcedWorld(GridWorld):
    def __init__(self, target, obstacles):
        self._forced_target = [int(target[0]), int(target[1])]
        self._forced_obstacles = [[int(o[0]), int(o[1])] for o in obstacles]
        super().__init__("T3_navigate", 0)

    def _build_layout(self, rng):
        self._target = list(self._forced_target)
        self._obstacles = [list(o) for o in self._forced_obstacles]
        self._initial_items = []
        self._remaining = []
        self._cue = 0


class DeclineBackend(ModelBackend):
    """Record every observation and decline, forcing the rule action."""

    def __init__(self):
        self.calls = 0
        self.seen = []

    def generate(self, observation):
        self.calls += 1
        self.seen.append(json.loads(json.dumps(observation, sort_keys=True)))
        return None


class BlindPlanner(Planner):
    """Executable memory cut: the planner never sees episode memories."""

    def plan(self, state, memories=None):
        return super().plan(state, None)


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


def _escapes(steps):
    out = []
    for record in steps:
        probe = record.get("args", {}).get("probe")
        if isinstance(probe, dict) and isinstance(probe.get("cycle_escape"), dict):
            out.append(probe["cycle_escape"])
    return out


def _prompt_sha256(observation, seed, model_id):
    prompt = build_prompt(observation)
    return manifest_for(
        prompt, observation, model_id=model_id, checkpoint=model_id,
        sampling={"temperature": 0.0, "seed": seed,
                  "n_predict": 0, "cache_prompt": True},
    )["sha256"]


def measure_case(name, target, obstacles, directory, mode="intact",
                 max_steps=200):
    backend = DeclineBackend()
    if mode == "blind":
        planner = BlindPlanner(backend=backend)
    else:
        planner = Planner(backend=backend, cycle_escape=(mode != "ablate"))
    agent = Agent(planner=planner, world=_ForcedWorld(target, obstacles))
    log_path = os.path.join(directory, "%s-%s.jsonl" % (name, mode))
    tel = Telemetry(log_path)
    tel.write_header(name, max_steps, policy="cycle-escape-battery",
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
                      "steps=%d reward=%.1f" % (len(trace), reward))
    steps = [record for record in Telemetry(log_path).read_all()
             if record.get("type") == "action" and record.get("kind") == "step"]
    decisions = _decisions(steps)
    escapes = _escapes(steps)
    first_obs = backend.seen[0]
    return {
        "name": name,
        "mode": mode,
        "target": list(target),
        "obstacles": [list(cell) for cell in obstacles],
        "steps": len(trace),
        "reward": reward,
        "success": success,
        "fallbacks": planner.fallbacks,
        "model_calls": backend.calls,
        "action_sha256": _actions_digest(trace),
        "prompt_sha256": _prompt_sha256(first_obs, 0,
                                       type(backend).__name__),
        "decision_first": decisions[0] if decisions else None,
        "decision_last": decisions[-1] if decisions else None,
        "escape_count": len(escapes),
        "escape_first": escapes[0] if escapes else None,
        "model_obs_keys": sorted(first_obs),
        "trace": _trace_slot(recompute(log_path)),
    }


def run_battery(cases=CASES, mode="intact", max_steps=200):
    """Measure every case under one mode in one temporary directory."""
    with tempfile.TemporaryDirectory() as directory:
        results = [measure_case(name, target, obstacles, directory,
                                mode=mode, max_steps=max_steps)
                   for name, target, obstacles in cases]
        return {
            "policy_sha256": policy_digest(),
            "model": "DeclineBackend",
            "mode": mode,
            "max_steps": max_steps,
            "cases": results,
        }


def _parse_case(text):
    for name, target, obstacles in CASES:
        if name == text:
            return name, target, obstacles
    raise ValueError("unknown case: %s" % text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", action="append", default=[],
                        help="case name; repeatable (default: all cases)")
    parser.add_argument("--mode", choices=MODES, default="intact")
    parser.add_argument("--max-steps", type=int, default=200)
    args = parser.parse_args()
    cases = tuple(_parse_case(text) for text in args.case) if args.case else CASES
    print(json.dumps(run_battery(cases, mode=args.mode,
                                 max_steps=args.max_steps),
                     indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
