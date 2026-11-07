"""Cold-start recovery battery: behavior plus trace, before/after.

Warm phase: run each task/seed with a persistent store. Cold phase:
close and reopen the store, hide the task's goal fields from every
observation, and run again with no in-memory episode history. The
harness reports the numbers the cycle records: success, steps/cost,
recovery and transfer estimates, recomputed synergy/phi, planner
source probes, and the exact first observation handed to a capture
backend at the model seam.

No weights, binaries, or committed logs: each run uses a temporary
directory and the caller prints JSON or redirects it outside the repo.
"""

import argparse
import hashlib
import json
import os
import tempfile

from agent import Agent, Planner, model_label, policy_digest
from evals.recompute import recompute
from memory.store import MemoryStore
from models.backend import ModelBackend
from models.llamacpp import build_prompt
from models.manifest import canonical, manifest_for
from telemetry.log import Telemetry
from worlds.grid import GridWorld

CASES = (
    ("T1_forage", 71, 16, 3.0),
    ("T2_delayed_match", 3, 8, 1.0),
    ("T3_navigate", 15, 13, 1.0),
    ("T3_navigate", 65, 6, 1.0),
)

STRIP = {
    "T1_forage": ("items_positions",),
    "T2_delayed_match": ("cue", "target"),
    "T3_navigate": ("target", "obstacles"),
}


class ColdWorld(GridWorld):
    """GridWorld whose observations omit the task's goal fields."""

    def _state(self):
        state = super()._state()
        for key in STRIP[self.task_id]:
            state.pop(key, None)
        return state


class CaptureBackend(ModelBackend):
    """Record every observation and decline, forcing the rule fallback."""

    def __init__(self):
        self.seen = []

    def generate(self, observation):
        self.seen.append(json.loads(json.dumps(observation, sort_keys=True)))
        return None


def warm_run(store, task, seed, max_steps=200):
    """Run the full-information episode and persist its layout."""
    return Agent(memory_store=store).run_task(task, seed, max_steps=max_steps)


def cold_run(store, task, seed, max_steps=200, ablate=False, log_path=None,
             capture=False):
    """Run the hidden-observation episode after a simulated restart."""
    backend = CaptureBackend() if capture else None
    planner = Planner(backend=backend) if backend is not None else None
    agent = Agent(planner=planner, memory_store=store,
                  world=ColdWorld(task, seed))
    bind = getattr(agent.planner, "bind_recall_source", None)
    if ablate and callable(bind):
        bind(None)
    if log_path is not None:
        tel = Telemetry(log_path)
        tel.write_header(task, max_steps, policy="coldstart-battery",
                         policy_sha256=policy_digest(),
                         model=model_label(agent.planner.backend))
        agent.telemetry_log = tel
    trace = agent.run(max_steps=max_steps)
    if log_path is not None:
        done = bool(trace[-1]["done"])
        success = done and sum(record["reward"] for record in trace) > 0.0
        agent.telemetry_log.append_action(
            9001, "eval_transfer",
            {"naive_steps": float(max_steps), "reuse_steps": float(len(trace))})
        agent.telemetry_log.append_action(
            9002, "eval_recovery",
            {"time_outside": 0.0 if success else float(len(trace)),
             "window": float(max_steps)})
        agent.telemetry_log.write_verdict(
            "done" if success else "truncated", "steps=%d" % len(trace))
    return agent, trace, backend


def _actions_digest(trace):
    body = canonical([record["action"] for record in trace])
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _probe_summary(steps):
    probes = [record.get("args", {}).get("probe") for record in steps]
    probes = [probe for probe in probes if isinstance(probe, dict)]
    if not probes:
        return None
    return {
        "state": sorted({key for probe in probes for key in probe.get("state", [])}),
        "memory": sorted({key for probe in probes for key in probe.get("memory", [])}),
        "persistent": sorted({key for probe in probes
                              for key in probe.get("persistent", [])}),
        "store_reads": max(probe.get("store_reads", 0) for probe in probes),
        "model_obs_keys": sorted({key for probe in probes
                                  for key in probe.get("model_obs_keys", [])}),
    }


def _model_summary(backend, seed):
    if backend is None:
        return {"label": model_label(None), "calls": 0,
                "obs_keys_first": [], "prompt_sha256": None}
    seen = getattr(backend, "seen", [])
    first = seen[0] if seen else None
    prompt = build_prompt(first) if first is not None else None
    manifest = None
    if first is not None:
        manifest = manifest_for(
            prompt, first, model_id="capture", checkpoint="capture",
            sampling={"temperature": 0.0, "seed": seed,
                      "n_predict": 0, "cache_prompt": True},
        )["sha256"]
    return {
        "label": model_label(backend),
        "calls": len(seen),
        "obs_keys_first": sorted(first) if first is not None else [],
        "prompt_sha256": manifest,
    }


def measure_case(task, seed, want_steps, want_reward, directory,
                 ablate=False, capture=False, max_steps=200):
    """Run one warm/cold pair and return the recorded slots."""
    stem = "%s-%d" % (task, seed)
    db_path = os.path.join(directory, stem + ".db")
    log_path = os.path.join(directory, stem + ".jsonl")
    store = MemoryStore(db_path)
    try:
        warm = warm_run(store, task, seed, max_steps=max_steps)
    finally:
        store.close()
    cold = MemoryStore(db_path)
    try:
        agent, trace, backend = cold_run(
            cold, task, seed, max_steps=max_steps, ablate=ablate,
            log_path=log_path, capture=capture)
    finally:
        cold.close()
    records = Telemetry(log_path).read_all()
    steps = [record for record in records
             if record.get("type") == "action" and record.get("kind") == "step"]
    stats = recompute(log_path)
    cold_reward = sum(record["reward"] for record in trace)
    cold_done = bool(trace[-1]["done"])
    return {
        "task": task,
        "seed": seed,
        "warm_steps": len(warm),
        "warm_reward": sum(record["reward"] for record in warm),
        "cold_steps": len(trace),
        "cold_reward": cold_reward,
        "cold_done": cold_done,
        "cold_success": cold_done and cold_reward > 0.0,
        "want_steps": want_steps,
        "want_reward": want_reward,
        "action_sha256": _actions_digest(trace),
        "probe": _probe_summary(steps),
        "model": _model_summary(backend, seed),
        "trace": {
            "syn": stats["syn"],
            "syn_n": stats["syn_n"],
            "phi": stats["phi"],
            "gain": stats["gain"],
            "recovery": stats["recovery"],
            "n_records": stats["n_records"],
        },
    }


def run_battery(cases=CASES, ablate=False, capture=False, max_steps=200):
    """Measure every case in one temporary directory."""
    with tempfile.TemporaryDirectory() as directory:
        results = []
        for task, seed, want_steps, want_reward in cases:
            results.append(measure_case(
                task, seed, want_steps, want_reward, directory,
                ablate=ablate, capture=capture, max_steps=max_steps))
        return {
            "policy_sha256": policy_digest(),
            "model": model_label(None),
            "ablate": bool(ablate),
            "capture": bool(capture),
            "max_steps": max_steps,
            "cases": results,
        }


def _parse_case(text):
    task, seed = text.rsplit(":", 1)
    for known, known_seed, want_steps, want_reward in CASES:
        if known == task and known_seed == int(seed):
            return known, known_seed, want_steps, want_reward
    raise ValueError("unknown case: %s" % text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", action="append", default=[],
                        help="task:seed; repeatable (default: all cases)")
    parser.add_argument("--ablate", action="store_true",
                        help="cut the persistent recall source")
    parser.add_argument("--capture", action="store_true",
                        help="record the model-seam observations")
    parser.add_argument("--max-steps", type=int, default=200)
    args = parser.parse_args()
    cases = tuple(_parse_case(text) for text in args.case) if args.case else CASES
    print(json.dumps(run_battery(cases, ablate=args.ablate,
                                 capture=args.capture,
                                 max_steps=args.max_steps),
                     indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
