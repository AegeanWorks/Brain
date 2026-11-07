"""Execution-budget battery: generous, step, LLM, token and time caps.

A generous budget keeps T3:15 at 13 steps / 1.0 reward with actions
identical to rule-only and reports the spent dimensions. Tight budgets
raise ``BudgetExceeded`` before the next action/call: 3 steps, 2 LLM
calls, 8 prompt tokens and a zero-second wall clock each name their
dimension, limit and attempted usage. No budget remains a no-op.
"""

import argparse
import json

from agent import Agent, Planner
from budget import BudgetExceeded, budget_from_limits
from models.backend import ModelBackend

MODES = ("generous", "step", "llm", "token", "time")


class WaitingBackend(ModelBackend):
    def __init__(self):
        self.calls = 0

    def generate(self, observation):
        self.calls += 1
        return "wait"


class PromptBackend(ModelBackend):
    def __init__(self, tokens=5):
        self.calls = 0
        self.last_prompt_stats = {"tokens": tokens, "omitted": 0}

    def generate(self, observation):
        self.calls += 1
        return None


def _measure(mode):
    if mode == "step":
        budget = budget_from_limits({"max_steps": 3})
    elif mode == "llm":
        budget = budget_from_limits({"max_llm_calls": 2})
    elif mode == "token":
        budget = budget_from_limits({"max_tokens": 8})
    elif mode == "time":
        budget = budget_from_limits({"max_seconds": 0})
    else:
        budget = budget_from_limits({})
    if mode == "llm":
        backend = WaitingBackend()
        agent = Agent(planner=Planner(backend=backend))
    elif mode == "token":
        backend = PromptBackend(tokens=5)
        agent = Agent(planner=Planner(backend=backend))
    else:
        backend = None
        agent = Agent()
    result = {
        "mode": mode,
        "kind": None,
        "limit": None,
        "used": None,
        "steps": 0,
        "calls": backend.calls if backend is not None else 0,
        "pressure": None,
        "actions_match_rule": None,
        "success": False,
    }
    try:
        trace = agent.run_task("T3_navigate", 15, budget=budget)
    except BudgetExceeded as exc:
        result.update({
            "kind": exc.kind,
            "limit": exc.limit,
            "used": exc.used,
            "steps": len(agent.telemetry.events()),
            "calls": backend.calls if backend is not None else 0,
            "pressure": budget.snapshot()["pressure"],
            "success": False,
        })
        return result
    rule = Agent().run_task("T3_navigate", 15)
    result.update({
        "steps": len(trace),
        "calls": backend.calls if backend is not None else 0,
        "pressure": budget.snapshot()["pressure"],
        "actions_match_rule": ([r["action"] for r in trace]
                               == [r["action"] for r in rule]),
        "success": bool(trace[-1]["done"]) and sum(
            r["reward"] for r in trace) > 0.0,
        "reward": sum(r["reward"] for r in trace),
        "snapshot": budget.snapshot(),
    })
    return result


def run_battery(modes=MODES):
    return {"model": "rule", "modes": list(modes),
            "cases": [_measure(mode) for mode in modes]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", action="append", choices=MODES, default=[],
                        help="repeatable (default: all modes)")
    args = parser.parse_args()
    modes = tuple(args.mode) if args.mode else MODES
    print(json.dumps(run_battery(modes), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
