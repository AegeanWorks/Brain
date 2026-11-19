"""Test ADR-197's boundary: is the high-count gap a rule limit or a planner limit?

The exact deadline schedule wins at every measured count, but its full sweep
stops at ten items with ``DeadlineWorld``'s default ``patience=40``. This eval
varies only that rule parameter and holds the planner fixed. If a longer
patience restores the full sweep while the tour ablation still loses the
urgent item, the boundary belongs to the reward rule, not the scheduler.

Usage: ``python -m evals.deadline_patience``
"""

import json

from agent import Agent, Planner
from worlds.deadline import DeadlineWorld

COUNTS = (11, 12)
PATIENCES = (40, 80, 120)
SEEDS = tuple(range(3))


def _reward(trace):
    return sum(float(step.get("reward", 0.0)) for step in trace)


def measure(items, patience, seeds=SEEDS):
    """Shipped vs ablated collection for one item count and patience."""
    shipped = ablation = 0.0
    shipped_steps = ablation_steps = 0
    for seed in seeds:
        trace = Agent(world=DeadlineWorld(seed, items=items,
                                          patience=patience)).run(max_steps=200)
        shipped += _reward(trace)
        shipped_steps += len(trace)
        trace = Agent(planner=Planner(deadline_ordering=False),
                      world=DeadlineWorld(seed, items=items,
                                          patience=patience)).run(max_steps=200)
        ablation += _reward(trace)
        ablation_steps += len(trace)
    total = len(seeds)
    return {
        "items": items,
        "patience": patience,
        "seeds": total,
        "shipped_mean": shipped / total,
        "ablation_mean": ablation / total,
        "shipped_steps": shipped_steps,
        "ablation_steps": ablation_steps,
        "shipped_collects_all": shipped == items * total,
    }


def main():
    rows = [measure(items, patience)
            for items in COUNTS for patience in PATIENCES]
    print(json.dumps(rows, indent=2, sort_keys=True))
    by_key = {(row["items"], row["patience"]): row for row in rows}
    ok = all(by_key[(items, 40)]["shipped_mean"] < items
             and by_key[(items, 120)]["shipped_collects_all"]
             and by_key[(items, 120)]["ablation_mean"] < items
             for items in COUNTS)
    print("deadline_patience: %s" % (
        "longer rule patience restores the full sweep; the tour ablation still loses"
        if ok else "the patience boundary did not behave as recorded"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
