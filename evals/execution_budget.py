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
from evals.battery_check import exit_code_for, format_findings
from models.backend import ModelBackend

MODES = ("generous", "step", "llm", "token", "time")

#: The dimension each mode must name when it raises; ``None`` means the
#: mode must complete. A budget that stops enforcing, or enforces the wrong
#: dimension, is caught by comparing against this table.
EXPECTED_KIND = {
    "generous": None,
    "step": "steps",
    "llm": "llm_calls",
    "token": "tokens",
    "time": "seconds",
}


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


def checks(report):
    """Return the claims this battery's own output contradicts.

    A budget either enforces its own dimension or it does not. These
    findings check that each capped mode names the right kind, that its
    usage exceeded its limit, that a capped run is not a success, and that
    a generous budget left the rule run byte-identical.
    """
    findings = []
    by_mode = {case.get("mode"): case for case in report.get("cases", [])}
    for mode, kind in EXPECTED_KIND.items():
        case = by_mode.get(mode)
        if case is None:
            findings.append("missing-mode:%s" % mode)
            continue
        if case.get("kind") != kind:
            findings.append("kind:%s:%s!=%s" % (mode, case.get("kind"), kind))
        if kind is None:
            if not case.get("actions_match_rule"):
                findings.append("generous-changed-actions:%s"
                                % case.get("actions_match_rule"))
            if not case.get("success"):
                findings.append("generous-not-success")
            if case.get("steps") != 13:
                findings.append("generous-steps:%s!=13" % case.get("steps"))
            if case.get("reward") != 1.0:
                findings.append("generous-reward:%s!=1.0"
                                % case.get("reward"))
            continue
        if case.get("success"):
            findings.append("capped-reported-success:%s" % mode)
        limit, used = case.get("limit"), case.get("used")
        if kind != "seconds":
            if limit is None or used is None:
                findings.append("missing-usage:%s" % mode)
            elif not float(used) > float(limit):
                findings.append("not-exceeded:%s:%s<=%s" % (mode, used, limit))
    return findings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", action="append", choices=MODES, default=[],
                        help="repeatable (default: all modes)")
    args = parser.parse_args()
    modes = tuple(args.mode) if args.mode else MODES
    report = run_battery(modes)
    print(json.dumps(report, indent=2, sort_keys=True))
    findings = checks(report)
    if findings:
        print(format_findings("execution_budget", findings), end="")
    raise SystemExit(exit_code_for(findings))


if __name__ == "__main__":
    main()
