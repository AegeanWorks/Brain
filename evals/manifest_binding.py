"""Generation-manifest binding battery: behavior plus model-seam trace.

Every backend call can compute a manifest over (model_id, checkpoint,
prompt, observation, sampling). The planner copies its SHA-256 into the
step's ``model_decision`` so a run log binds each action to the exact
generation input. This battery uses a deterministic declining backend:
the rule acts, the action trace is identical across modes, and only the
manifest readout changes.

Modes:
- ``intact``: the manifest digest is recorded on every decision.
- ``ablate``: ``probe_manifest=False`` removes the digest; the binding
  dies while actions stay identical.
- ``swap``: same backend code and observation with checkpoint B; the
  action trace is identical but every manifest digest differs.

No weights, binaries, or committed logs: the battery uses a temporary
directory and reports hashes only.
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
    ("T3_navigate", 15),
)

MODES = ("intact", "ablate", "swap")

SAMPLING = {"temperature": 0.0, "seed": 0,
            "n_predict": 0, "cache_prompt": True}


class ManifestBackend(ModelBackend):
    """Decline every proposal while recording its generation manifest."""

    def __init__(self, checkpoint="manifest-A", model_id="manifest-stub"):
        self.checkpoint = checkpoint
        self.model_id = model_id
        self.calls = 0
        self.seen = []
        self.manifests = []
        self.last_manifest = None

    def generate(self, observation):
        self.calls += 1
        obs = json.loads(json.dumps(observation, sort_keys=True))
        self.seen.append(obs)
        self.last_manifest = manifest_for(
            build_prompt(obs), obs, model_id=self.model_id,
            checkpoint=self.checkpoint, sampling=SAMPLING)
        self.manifests.append(self.last_manifest["sha256"])
        return None


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


def measure_case(task, seed, directory, mode="intact", checkpoint="manifest-A",
                 max_steps=200):
    backend = ManifestBackend(checkpoint=checkpoint)
    planner = Planner(backend=backend, probe_manifest=(mode != "ablate"))
    log_path = os.path.join(directory, "%s-%d-%s.jsonl" % (task, seed, mode))
    tel = Telemetry(log_path)
    tel.write_header(task, max_steps, policy="manifest-binding-battery",
                     policy_sha256=policy_digest(),
                     model=model_label(backend))
    agent = Agent(planner=planner, telemetry_log=tel)
    trace = agent.run_task(task, seed, max_steps=max_steps)
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
    digests = [item.get("model_manifest_sha256") for item in decisions]
    covered = sum(1 for value in digests if isinstance(value, str))
    return {
        "task": task,
        "seed": seed,
        "mode": mode,
        "checkpoint": checkpoint,
        "steps": len(trace),
        "reward": reward,
        "success": success,
        "model_calls": backend.calls,
        "action_sha256": _actions_digest(trace),
        "first_manifest_sha256": backend.manifests[0] if backend.manifests else None,
        "manifest_coverage": (covered / len(digests)) if digests else 0.0,
        "decision_first": decisions[0] if decisions else None,
        "decision_last": decisions[-1] if decisions else None,
        "model_obs_keys": sorted(backend.seen[0]) if backend.seen else [],
        "trace": _trace_slot(recompute(log_path)),
    }


def run_battery(cases=CASES, mode="intact", max_steps=200):
    """Measure every case under one mode in one temporary directory."""
    checkpoint = "manifest-B" if mode == "swap" else "manifest-A"
    with tempfile.TemporaryDirectory() as directory:
        results = [measure_case(task, seed, directory, mode=mode,
                                checkpoint=checkpoint, max_steps=max_steps)
                   for task, seed in cases]
        return {
            "policy_sha256": policy_digest(),
            "model": "ManifestBackend",
            "mode": mode,
            "checkpoint": checkpoint,
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
    parser.add_argument("--mode", choices=MODES, default="intact")
    parser.add_argument("--max-steps", type=int, default=200)
    args = parser.parse_args()
    cases = tuple(_parse_case(text) for text in args.case) if args.case else CASES
    print(json.dumps(run_battery(cases, mode=args.mode,
                                 max_steps=args.max_steps),
                     indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
