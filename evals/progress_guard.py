"""Progress-guard battery: wrong-way moves, the guard, and the skip.

A deterministic backend proposes the legal free-cell movement that
maximises BFS distance to the fixed target (or the first remaining item
when no target exists). Without the guard the proposal is accepted until
the 20-step trust window expires: T3:15 costs 33 steps/21 calls, T3:65
26/21, T2:3 34/21. With the guard each strictly increasing movement is
rejected immediately as ``no-progress``: 13/13, 6/6, 8/8. With
``progress_skip_after=3`` the backend is called only until three
consecutive progress rejections (4/4/3 calls here because one
equal-distance move is accepted), then the rest of the episode is
rule-only as ``skipped-progress``. The T1 item tour is unchanged at 36
steps/22 calls because the guard only applies to a fixed target with no
remaining items. Rule actions, rewards and seeds are identical in every
mode.
"""

import argparse
import json

from agent import Agent, Planner, policy_digest
from evals.battery_check import exit_code_for, format_findings
from models.backend import ModelBackend
from worlds.grid import SIZE

CASES = (("T3_navigate", 15), ("T3_navigate", 65),
         ("T2_delayed_match", 3), ("T1_forage", 71))
MODES = ("guard-off", "guard-on", "skip-on")
SKIP_AFTER = 3

#: Pre-registered expected ``(steps, backend_calls)`` per mode, from the
#: docstring numbers this battery was written against. The guard's whole
#: claim is that these differ per mode; pinning them here makes a planner
#: change fail the battery instead of only changing its printed output.
EXPECTED = {
    ("guard-off", "T3_navigate", 15): (33, 21),
    ("guard-off", "T3_navigate", 65): (26, 21),
    ("guard-off", "T2_delayed_match", 3): (34, 21),
    ("guard-off", "T1_forage", 71): (36, 22),
    ("guard-on", "T3_navigate", 15): (13, 13),
    ("guard-on", "T3_navigate", 65): (6, 6),
    ("guard-on", "T2_delayed_match", 3): (8, 8),
    ("guard-on", "T1_forage", 71): (36, 22),
    ("skip-on", "T3_navigate", 15): (13, 4),
    ("skip-on", "T3_navigate", 65): (6, 4),
    ("skip-on", "T2_delayed_match", 3): (8, 3),
    ("skip-on", "T1_forage", 71): (36, 22),
}


class WrongWayBackend(ModelBackend):
    """Legal free-cell movement away from the fixed target."""

    def __init__(self):
        self.calls = 0

    @staticmethod
    def _distance(start, target, obstacles):
        blocked = {tuple(cell) for cell in obstacles}
        queue = [(tuple(start), 0)]
        seen = {tuple(start)}
        while queue:
            cell, distance = queue.pop(0)
            if cell == tuple(target):
                return distance
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                nxt = (cell[0] + dx, cell[1] + dy)
                if not (0 <= nxt[0] < SIZE and 0 <= nxt[1] < SIZE):
                    continue
                if nxt in blocked or nxt in seen:
                    continue
                seen.add(nxt)
                queue.append((nxt, distance + 1))
        return 10 ** 6

    def generate(self, observation):
        self.calls += 1
        target = observation.get("target")
        if target is None:
            items = observation.get("items_positions") or []
            target = items[0] if items else None
        if target is None:
            return "wait"
        x, y = int(observation["x"]), int(observation["y"])
        obstacles = observation.get("obstacles") or []
        blocked = {tuple(cell) for cell in obstacles}
        best = None
        for action, dx, dy in (("up", 0, -1), ("down", 0, 1),
                               ("left", -1, 0), ("right", 1, 0)):
            nx, ny = x + dx, y + dy
            if not (0 <= nx < SIZE and 0 <= ny < SIZE):
                continue
            if (nx, ny) in blocked:
                continue
            distance = self._distance((nx, ny), target, obstacles)
            if best is None or distance > best[0]:
                best = (distance, action)
        return best[1] if best is not None else "wait"


def measure_case(mode, task, seed):
    backend = WrongWayBackend()
    guard = mode != "guard-off"
    skip_after = SKIP_AFTER if mode == "skip-on" else None
    planner = Planner(backend=backend, progress_guard=guard,
                      progress_skip_after=skip_after)
    trace = Agent(planner=planner).run_task(task, seed, max_steps=200)
    reward = sum(record["reward"] for record in trace)
    decision = planner.last_probe.get("model_decision", {})
    return {
        "mode": mode,
        "task": task,
        "seed": seed,
        "steps": len(trace),
        "reward": reward,
        "success": bool(trace[-1]["done"]) and reward > 0.0,
        "backend_calls": backend.calls,
        "fallbacks": planner.fallbacks,
        "progress_rejections": planner.progress_rejections,
        "progress_streak": decision.get("progress_streak"),
        "progress_distrusted": decision.get("progress_distrusted"),
        "progress_skip_after": decision.get("progress_skip_after"),
        "distrusted": decision.get("distrusted"),
        "last_reason": decision.get("reason"),
        "progress": decision.get("progress"),
    }


def run_battery(modes=MODES):
    return {
        "model": "wrong-way",
        "policy_sha256": policy_digest(),
        "modes": list(modes),
        "cases": [measure_case(mode, task, seed)
                  for mode in modes for task, seed in CASES],
    }


def checks(report):
    """Compare a battery report with the pre-registered expectations.

    Every documented number is a claim. This returns one finding per
    disagreement, plus structural findings when a case is missing, a reward
    moved, or the guard stopped separating itself from its absence.
    """
    findings = []
    by_key = {}
    for case in report.get("cases", []):
        key = (case.get("mode"), case.get("task"), case.get("seed"))
        by_key[key] = case
    for (mode, task, seed), (steps, calls) in EXPECTED.items():
        case = by_key.get((mode, task, seed))
        if case is None:
            findings.append("missing-case:%s:%s:%d" % (mode, task, seed))
            continue
        if case.get("steps") != steps:
            findings.append("steps:%s:%s:%d:%s!=%s"
                            % (mode, task, seed, case.get("steps"), steps))
        if case.get("backend_calls") != calls:
            findings.append("calls:%s:%s:%d:%s!=%s"
                            % (mode, task, seed, case.get("backend_calls"),
                               calls))
        if case.get("reward", 0.0) <= 0.0:
            findings.append("reward:%s:%s:%d:%s"
                            % (mode, task, seed, case.get("reward")))
    # Rewards must not depend on the guard; it only rejects proposals.
    for task, seed in CASES:
        rewards = {by_key[(mode, task, seed)]["reward"]
                   for mode in MODES if (mode, task, seed) in by_key}
        if len(rewards) > 1:
            findings.append("reward-varies:%s:%d:%s"
                            % (task, seed, sorted(rewards)))
    # The guard must actually reject; an inert guard is a vacuous control.
    for task, seed in CASES:
        off = by_key.get(("guard-off", task, seed))
        on = by_key.get(("guard-on", task, seed))
        if off is None or on is None:
            continue
        if task == "T1_forage":
            continue  # the docstring states the guard does not apply here
        if on["progress_rejections"] <= 0:
            findings.append("guard-inert:%s:%d" % (task, seed))
        if on["steps"] >= off["steps"]:
            findings.append("guard-no-saving:%s:%d:%d>=%d"
                            % (task, seed, on["steps"], off["steps"]))
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
        print(format_findings("progress_guard", findings), end="")
    raise SystemExit(exit_code_for(findings))


if __name__ == "__main__":
    main()
