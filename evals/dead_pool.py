"""Dead-pool guard battery: behavior plus the dead_pool probe.

Five two-blocker pins. The guard drops a dead goal step from the pool
only when a live candidate is at least as close to the goal by BFS, so
the (7,5) layout stops entering the dead (7,1) probe and completes in
16 steps instead of 18. The ablation restores the 18-step detour with
the same backend, seed and prompt; the first prompt hash is unchanged.

Modes:
- ``intact``: BFS-distance dead-pool guard on.
- ``ablate``: ``dead_pool_filter=False`` restores the old pool.

Reports steps/reward/success, action and first-prompt hashes, the
dead-pool probe readout, and recomputed trace statistics. No weights,
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
    ((5, 0), ((2, 0), (1, 1)), 9),
    ((7, 5), ((6, 1), (7, 2)), 16),
    ((3, 6), ((2, 2), (3, 2)), 11),
    ((5, 6), ((4, 4), (5, 5)), 13),
    ((5, 7), ((5, 6), (4, 2)), 14),
)

MODES = ("intact", "ablate")


class _ForcedMultiWorld(GridWorld):
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


def _actions_digest(trace):
    body = canonical([record["action"] for record in trace])
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _prompt_sha256(observation):
    prompt = build_prompt(observation)
    return manifest_for(
        prompt, observation, model_id="DeclineBackend",
        checkpoint="DeclineBackend",
        sampling={"temperature": 0.0, "seed": 0,
                  "n_predict": 0, "cache_prompt": True},
    )["sha256"]


def _decisions(steps):
    out = []
    for record in steps:
        probe = record.get("args", {}).get("probe")
        if isinstance(probe, dict) and isinstance(probe.get("model_decision"), dict):
            out.append(probe["model_decision"])
    return out


def _dead_pools(steps):
    out = []
    for record in steps:
        probe = record.get("args", {}).get("probe")
        if isinstance(probe, dict) and isinstance(probe.get("dead_pool"), dict):
            out.append(probe["dead_pool"])
    return out


def measure_case(target, obstacles, want_steps, directory, mode="intact",
                 max_steps=200):
    backend = DeclineBackend()
    planner = Planner(backend=backend,
                      dead_pool_filter=(mode != "ablate"))
    world = _ForcedMultiWorld(target, obstacles)
    log_path = os.path.join(directory, "%s-%s-%s.jsonl"
                            % ("multi", "-".join(map(str, target)), mode))
    tel = Telemetry(log_path)
    tel.write_header("T3_navigate", max_steps, policy="dead-pool-battery",
                     policy_sha256=policy_digest(),
                     model=model_label(backend))
    agent = Agent(planner=planner, world=world, telemetry_log=tel)
    trace = agent.run(max_steps=max_steps)
    reward = sum(record["reward"] for record in trace)
    success = bool(trace[-1]["done"]) and reward > 0.0
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
    pools = _dead_pools(steps)
    first_obs = backend.seen[0]
    return {
        "target": list(target),
        "obstacles": [list(cell) for cell in obstacles],
        "mode": mode,
        "want_steps": want_steps,
        "steps": len(trace),
        "reward": reward,
        "success": success,
        "model_calls": backend.calls,
        "action_sha256": _actions_digest(trace),
        "prompt_sha256": _prompt_sha256(first_obs),
        "decision_first": decisions[0] if decisions else None,
        "dead_pool_count": len(pools),
        "dead_pool_first": pools[0] if pools else None,
        "model_obs_keys": sorted(first_obs),
        "trace": _trace_slot(recompute(log_path)),
    }


def run_battery(cases=CASES, mode="intact", max_steps=200):
    """Measure every case under one mode in one temporary directory."""
    with tempfile.TemporaryDirectory() as directory:
        results = [measure_case(target, obstacles, want_steps, directory,
                                mode=mode, max_steps=max_steps)
                   for target, obstacles, want_steps in cases]
        return {
            "policy_sha256": policy_digest(),
            "model": "DeclineBackend",
            "mode": mode,
            "max_steps": max_steps,
            "cases": results,
        }


def _parse_case(text):
    target_text, obstacle_text = text.split("|", 1)
    target = tuple(int(v) for v in target_text.split(","))
    obstacles = []
    for chunk in obstacle_text.split(";"):
        obstacles.append(tuple(int(v) for v in chunk.split(",")))
    for known_target, known_obstacles, want in CASES:
        if (tuple(known_target) == target
                and tuple(tuple(o) for o in known_obstacles) == tuple(obstacles)):
            return known_target, known_obstacles, want
    raise ValueError("unknown case: %s" % text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", action="append", default=[],
                        help="target|obs1;obs2; repeatable (default: all cases)")
    parser.add_argument("--mode", choices=MODES, default="intact")
    parser.add_argument("--max-steps", type=int, default=200)
    args = parser.parse_args()
    cases = tuple(_parse_case(text) for text in args.case) if args.case else CASES
    print(json.dumps(run_battery(cases, mode=args.mode,
                                 max_steps=args.max_steps),
                     indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
