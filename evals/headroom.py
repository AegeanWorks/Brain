"""Measure the one task where the rule is beatable, and show it being beaten.

ADR-192 found no headroom on the shipped tasks, so no policy could improve
them. `worlds.deadline.DeadlineWorld` is built to have headroom: the farthest
item expires at the moment a direct approach reaches it, so the rule's
shortest-tour order spends its early steps on patient items and loses it.

Measured over seeds 0-19:

    rule (shortest tour)   3.00 items, 200.00 steps
    deadline-aware plan    4.00 items,  30.35 steps
    optimum (brute force)  4.00 items
    rule gap on 20 of 20 seeds

`deadline_actions` produces the plan the rule cannot, and it is replayed
through the real backend seam (`StubBackend`), so this is the first measured
case of a non-rule policy winning on this substrate.
"""

import itertools
import json

from agent import Agent, Planner
from models.backend import StubBackend
from worlds.deadline import DeadlineWorld

DEFAULT_SEEDS = tuple(range(20))
DELTAS = ((0, -1), (0, 1), (-1, 0), (1, 0))


def _manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _moves_toward(start, goal):
    """Deterministic axis-by-axis action list from start to goal.

    Moves one cell at a time, so the world's clamping never absorbs a step
    and the resulting plan has exactly the planned length.
    """
    actions = []
    x, y = start
    while x != goal[0]:
        if goal[0] > x:
            x += 1
            actions.append("right")
        else:
            x -= 1
            actions.append("left")
    while y != goal[1]:
        if goal[1] > y:
            y += 1
            actions.append("down")
        else:
            y -= 1
            actions.append("up")
    return actions


def _plan_actions(order):
    """Actions visiting ``order`` in sequence, collecting at each cell."""
    actions = []
    position = (0, 0)
    for cell in order:
        actions.extend(_moves_toward(position, cell))
        actions.append("collect")
        position = tuple(cell)
    return actions


def optimal_collected(items):
    """Max items collectible over every visit order, honoring deadlines."""
    best = 0
    for order in itertools.permutations(items):
        position, step, got = (0, 0), 0, 0
        for cell, deadline in order:
            step += _manhattan(position, cell) + 1
            if step <= deadline:
                got += 1
                position = cell
        best = max(best, got)
    return best


def deadline_actions(seed):
    """Earliest-deadline-first plan for one seed, as action tokens."""
    world = DeadlineWorld(seed)
    order = [tuple(item["cell"]) for item in
             sorted(world.items, key=lambda item: (item["deadline"], item["cell"]))]
    return _plan_actions(order)


def rule_collected(seed):
    """What the shipped rule policy actually achieves on this world."""
    trace = Agent(world=DeadlineWorld(seed)).run(max_steps=200)
    return {
        "collected": sum(float(step.get("reward", 0.0)) for step in trace),
        "steps": len(trace),
    }


def policy_collected(seed):
    """Replay the deadline plan through the backend seam."""
    planner = Planner(backend=StubBackend(script=deadline_actions(seed)),
                      noop_guard=False, progress_guard=False)
    trace = Agent(planner=planner, world=DeadlineWorld(seed)).run(max_steps=200)
    return {
        "collected": sum(float(step.get("reward", 0.0)) for step in trace),
        "steps": len(trace),
        "accepted": planner.accepted,
        "rejected": planner.fallbacks,
    }


def headroom(seeds=DEFAULT_SEEDS):
    """Compare rule, deadline plan and optimum per seed."""
    rows = []
    for seed in seeds:
        world = DeadlineWorld(seed)
        items = [(tuple(item["cell"]), item["deadline"])
                 for item in world.items]
        rule = rule_collected(seed)
        policy = policy_collected(seed)
        optimum = optimal_collected(items)
        rows.append({
            "seed": seed,
            "rule": rule["collected"],
            "policy": policy["collected"],
            "optimal": optimum,
            "rule_steps": rule["steps"],
            "policy_steps": policy["steps"],
        })
    gaps = [row["optimal"] - row["rule"] for row in rows]
    return {
        "seeds": len(rows),
        "rule_mean": sum(row["rule"] for row in rows) / len(rows),
        "policy_mean": sum(row["policy"] for row in rows) / len(rows),
        "optimal_mean": sum(row["optimal"] for row in rows) / len(rows),
        "seeds_with_rule_gap": sum(1 for gap in gaps if gap > 0),
        "policy_reaches_optimum": all(row["policy"] == row["optimal"]
                                      for row in rows),
        "rule_steps_mean": sum(row["rule_steps"] for row in rows) / len(rows),
        "policy_steps_mean": sum(row["policy_steps"] for row in rows) / len(rows),
        "rows": rows,
    }


def main():
    """Print the headroom report; 0 when a non-rule policy actually wins."""
    report = headroom()
    printable = {key: value for key, value in report.items() if key != "rows"}
    print(json.dumps(printable, indent=2, sort_keys=True))
    ok = (report["policy_reaches_optimum"]
          and report["policy_mean"] > report["rule_mean"])
    if not ok:
        print("headroom: the deadline plan did not beat the rule")
        raise SystemExit(1)
    print("headroom: the rule loses %.2f items per episode and a deadline-"
          "ordered plan recovers them all (%d/%d seeds show the rule gap)."
          % (report["optimal_mean"] - report["rule_mean"],
             report["seeds_with_rule_gap"], report["seeds"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
