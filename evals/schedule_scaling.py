"""Measure where the exact deadline schedule still wins as items grow.

ADR-195's enumeration stopped at seven items. ADR-196 replaced it with an
exact bitmask program capped at twelve, so this eval compares the shipped
scheduler with the ``deadline_ordering=False`` tour ablation on the counts
that used to fall back. It deliberately does not compute the factorial
optimum: the shipped helper is already pinned against brute force up to
seven items in ``tests/test_schedule_scaling.py``.

Usage: ``python -m evals.schedule_scaling``
"""

import json

from agent import Agent, Planner
from worlds.deadline import DeadlineWorld

COUNTS = (8, 9, 10, 11, 12)
SEEDS = tuple(range(3))


def _reward(trace):
    return sum(float(step.get("reward", 0.0)) for step in trace)


def measure(items, seeds=SEEDS):
    """Shipped vs ablated collection over ``seeds`` for one item count."""
    shipped = ablation = 0.0
    shipped_steps = ablation_steps = 0
    for seed in seeds:
        trace = Agent(planner=Planner(),
                      world=DeadlineWorld(seed, items=items)).run(max_steps=200)
        shipped += _reward(trace)
        shipped_steps += len(trace)
        trace = Agent(planner=Planner(deadline_ordering=False),
                      world=DeadlineWorld(seed, items=items)).run(max_steps=200)
        ablation += _reward(trace)
        ablation_steps += len(trace)
    total = len(seeds)
    return {
        "items": items,
        "seeds": total,
        "shipped_mean": shipped / total,
        "ablation_mean": ablation / total,
        "shipped_steps": shipped_steps,
        "ablation_steps": ablation_steps,
        "shipped_collects_all": shipped == items * total,
    }


def main():
    rows = [measure(count) for count in COUNTS]
    print(json.dumps(rows, indent=2, sort_keys=True))
    # The world's own deadlines cap the reachable count from 11 items on, so
    # the claim is strictly more collected than the tour ablation, not a full
    # sweep. The helper-level full sweep is pinned separately in the tests.
    ok = all(row["shipped_mean"] > row["ablation_mean"] for row in rows)
    print("schedule_scaling: %s" % (
        "the exact schedule beats the tour ablation at every measured count"
        if ok else "the schedule no longer beats the tour ablation"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
