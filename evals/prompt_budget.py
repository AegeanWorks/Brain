"""Prompt-budget battery: capped model prompts, unchanged rule actions.

The synthetic observation carries 64 visits. Uncapped, the prompt is
228 estimated tokens; at a 60-token budget the anchor (task, position,
legal, target, obstacles) is kept, the visits line is dropped and the
prompt stays at or under the budget. The agent case runs T3 seed 15
with a declining capture backend so the rule acts: uncapped and
budgeted actions/steps/rewards must match, while the prompt tokens,
omitted count and generation-manifest hash change.
"""

import argparse
import json
import tempfile

from agent import Agent, Planner
from models.backend import ModelBackend
from models.llamacpp import build_prompt, estimate_tokens, prompt_stats
from models.manifest import manifest_for

MODES = ("uncapped", "budgeted")
BUDGET = 60
SAMPLING = {"temperature": 0.0, "seed": 0,
            "n_predict": 0, "cache_prompt": True}

MANY = {
    "task": "T3_navigate", "x": 5, "y": 0, "steps": 7,
    "legal": ["up", "down", "left", "right", "collect", "wait"],
    "target": [7, 7],
    "obstacles": [[6, 1]],
    "visits": [[x, y, 1] for y in range(8) for x in range(8)],
}


class PromptBackend(ModelBackend):
    """Record the rendered prompt/manifest, then decline to the rule."""

    def __init__(self, budget):
        self.budget = budget
        self.calls = 0
        self.prompts = []
        self.seen = []
        self.manifests = []
        self.last_manifest = None

    def generate(self, observation):
        self.calls += 1
        obs = json.loads(json.dumps(observation, sort_keys=True))
        self.seen.append(obs)
        prompt = build_prompt(obs, max_tokens=self.budget)
        self.prompts.append(prompt)
        self.last_manifest = manifest_for(
            prompt, obs, model_id="PromptBudget", checkpoint="PromptBudget",
            sampling=SAMPLING)
        self.manifests.append(self.last_manifest["sha256"])
        return None


def _synthetic(mode):
    budget = None if mode == "uncapped" else BUDGET
    text = build_prompt(MANY, max_tokens=budget)
    stats = prompt_stats(MANY, max_tokens=budget)
    return {
        "tokens": stats["tokens"],
        "omitted": stats["omitted"],
        "lines": stats["lines"],
        "target": "Target: [7, 7]." in text,
        "obstacles": "Obstacles: [[6, 1]]." in text,
        "visits": "Visits:" in text,
        "marker": "OMITTED:%d" % stats["omitted"] if stats["omitted"] else None,
    }


def measure_case(mode="uncapped"):
    budget = None if mode == "uncapped" else BUDGET
    backend = PromptBackend(budget)
    planner = Planner(backend=backend)
    trace = Agent(planner=planner).run_task("T3_navigate", 15)
    rule = Agent().run_task("T3_navigate", 15)
    actions_match = ([record["action"] for record in trace]
                     == [record["action"] for record in rule])
    return {
        "mode": mode,
        "budget": budget,
        "steps": len(trace),
        "reward": sum(record["reward"] for record in trace),
        "success": bool(trace[-1]["done"]) and sum(
            record["reward"] for record in trace) > 0.0,
        "actions_match_rule": actions_match,
        "model_calls": backend.calls,
        "prompt_max_tokens": max(
            (estimate_tokens(prompt) for prompt in backend.prompts),
            default=0),
        "prompt_omitted_total": sum(
            prompt_stats(observation, budget)["omitted"]
            for observation in backend.seen),
        "prompt_first_sha256": (backend.manifests[0]
                                if backend.manifests else None),
        "synthetic": _synthetic(mode),
    }


def run_battery(modes=MODES):
    return {"model": "PromptBackend", "modes": list(modes),
            "cases": [measure_case(mode=mode) for mode in modes]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", action="append", choices=MODES, default=[],
                        help="repeatable (default: all modes)")
    args = parser.parse_args()
    modes = tuple(args.mode) if args.mode else MODES
    print(json.dumps(run_battery(modes), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
