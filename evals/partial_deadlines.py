"""Measure graceful degradation when a world hides some item deadlines.

The planner now infers the reward rule's slack from the deadlines it can see
and uses it for the missing ones, naming them in ``probe.deadline.assumed``.
This eval holds the item count fixed and varies only how many deadlines the
world emits, comparing the shipped schedule with the tour ablation.

Usage: ``python -m evals.partial_deadlines``
"""

import json

from agent import Agent, Planner
from worlds.deadline import DeadlineWorld

ITEMS = 12
VISIBILITIES = (1.0, 0.75, 0.5, 0.25)
SEEDS = tuple(range(3))


def _reward(trace):
    return sum(float(step.get("reward", 0.0)) for step in trace)


def measure(visibility, seeds=SEEDS):
    """Shipped vs ablated collection for one deadline visibility."""
    shipped = ablation = 0.0
    shipped_steps = ablation_steps = 0
    for seed in seeds:
        world = DeadlineWorld(seed, items=ITEMS,
                              deadline_visibility=visibility)
        trace = Agent(world=world).run(max_steps=200)
        shipped += _reward(trace)
        shipped_steps += len(trace)
        world = DeadlineWorld(seed, items=ITEMS,
                              deadline_visibility=visibility)
        trace = Agent(planner=Planner(deadline_ordering=False),
                      world=world).run(max_steps=200)
        ablation += _reward(trace)
        ablation_steps += len(trace)
    total = len(seeds)
    return {
        "items": ITEMS,
        "visibility": visibility,
        "seeds": total,
        "shipped_mean": shipped / total,
        "ablation_mean": ablation / total,
        "shipped_steps": shipped_steps,
        "ablation_steps": ablation_steps,
    }


def main():
    rows = [measure(visibility) for visibility in VISIBILITIES]
    print(json.dumps(rows, indent=2, sort_keys=True))
    ok = all(row["shipped_mean"] >= row["ablation_mean"] for row in rows)
    print("partial_deadlines: %s" % (
        "the schedule never falls below the tour ablation as deadlines are hidden"
        if ok else "a partial deadline map made the schedule worse than the ablation"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
