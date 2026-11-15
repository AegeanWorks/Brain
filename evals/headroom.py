"""Measure the one task where a shortest tour is beatable, and show it beaten.

ADR-192 found no headroom on the shipped tasks, so no policy could improve
them. `worlds.deadline.DeadlineWorld` is built to have headroom: the farthest
item expires at the moment a direct approach reaches it, so a shortest-tour
order spends its early steps on patient items and loses it.

Measured over seeds 0-19 with four items:

    tour ablation         3.00 items, 200.00 steps
    shipped rule          4.00 items,  26.65 steps
    hand deadline plan    4.00 items,  30.35 steps
    optimum (brute force) 4.00 items
    tour gap on 20 of 20 seeds; shipped and hand plan gap 0

The shipped rule schedules against the world's ``deadlines`` map; the
``tour_rule_collected`` function builds the shortest-tour ablation. The hand
plan is still replayed through the real backend seam (`StubBackend`), so the
battery measures both a rule integration and a non-rule plan.
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


def deadline_actions(seed, items=4):
    """Earliest-deadline-first plan for one seed, as action tokens."""
    world = DeadlineWorld(seed, items=items)
    order = [tuple(item["cell"]) for item in
             sorted(world.items, key=lambda item: (item["deadline"], item["cell"]))]
    return _plan_actions(order)


def rule_collected(seed, items=4):
    """What the shipped, deadline-scheduling rule achieves on this world."""
    trace = Agent(world=DeadlineWorld(seed, items=items)).run(max_steps=200)
    return {
        "collected": sum(float(step.get("reward", 0.0)) for step in trace),
        "steps": len(trace),
    }


def tour_rule_collected(seed, items=4):
    """The shortest-tour ablation: no deadline scheduling."""
    planner = Planner(deadline_ordering=False)
    trace = Agent(planner=planner,
                  world=DeadlineWorld(seed, items=items)).run(max_steps=200)
    return {
        "collected": sum(float(step.get("reward", 0.0)) for step in trace),
        "steps": len(trace),
    }


def policy_collected(seed, items=4):
    """Replay the hand deadline plan through the backend seam."""
    planner = Planner(backend=StubBackend(script=deadline_actions(seed, items)),
                      noop_guard=False, progress_guard=False)
    trace = Agent(planner=planner,
                  world=DeadlineWorld(seed, items=items)).run(max_steps=200)
    return {
        "collected": sum(float(step.get("reward", 0.0)) for step in trace),
        "steps": len(trace),
        "accepted": planner.accepted,
        "rejected": planner.fallbacks,
    }


def headroom(seeds=DEFAULT_SEEDS, items=4):
    """Compare shipped rule, tour ablation, hand plan and optimum per seed."""
    rows = []
    for seed in seeds:
        world = DeadlineWorld(seed, items=items)
        item_rows = [(tuple(item["cell"]), item["deadline"])
                     for item in world.items]
        rule = rule_collected(seed, items)
        tour = tour_rule_collected(seed, items)
        policy = policy_collected(seed, items)
        optimum = optimal_collected(item_rows)
        rows.append({
            "seed": seed,
            "rule": rule["collected"],
            "tour_rule": tour["collected"],
            "policy": policy["collected"],
            "optimal": optimum,
            "rule_steps": rule["steps"],
            "tour_rule_steps": tour["steps"],
            "policy_steps": policy["steps"],
        })
    tour_gaps = [row["optimal"] - row["tour_rule"] for row in rows]
    rule_gaps = [row["optimal"] - row["rule"] for row in rows]
    policy_gaps = [row["optimal"] - row["policy"] for row in rows]
    return {
        "seeds": len(rows),
        "items": items,
        "rule_mean": sum(row["rule"] for row in rows) / len(rows),
        "tour_rule_mean": sum(row["tour_rule"] for row in rows) / len(rows),
        "policy_mean": sum(row["policy"] for row in rows) / len(rows),
        "optimal_mean": sum(row["optimal"] for row in rows) / len(rows),
        "tour_rule_gap_seeds": sum(1 for gap in tour_gaps if gap > 0),
        "rule_gap_seeds": sum(1 for gap in rule_gaps if gap > 0),
        "policy_gap_seeds": sum(1 for gap in policy_gaps if gap > 0),
        "rule_reaches_optimum": all(row["rule"] == row["optimal"]
                                    for row in rows),
        "policy_reaches_optimum": all(row["policy"] == row["optimal"]
                                      for row in rows),
        "rule_steps_mean": sum(row["rule_steps"] for row in rows) / len(rows),
        "tour_rule_steps_mean": (sum(row["tour_rule_steps"] for row in rows)
                                 / len(rows)),
        "policy_steps_mean": sum(row["policy_steps"] for row in rows) / len(rows),
        "rows": rows,
    }


def main():
    """Print the headroom report; 0 when the shipped rule and plan win."""
    report = headroom()
    printable = {key: value for key, value in report.items() if key != "rows"}
    print(json.dumps(printable, indent=2, sort_keys=True))
    ok = (report["rule_reaches_optimum"]
          and report["policy_reaches_optimum"]
          and report["rule_mean"] > report["tour_rule_mean"])
    if not ok:
        print("headroom: the deadline schedule did not preserve the win")
        raise SystemExit(1)
    print("headroom: the tour ablation loses %.2f items per episode; the "
          "shipped schedule and hand plan recover them (%d/%d seeds show "
          "the tour gap)."
          % (report["optimal_mean"] - report["tour_rule_mean"],
             report["tour_rule_gap_seeds"], report["seeds"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
