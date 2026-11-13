"""How much room is there above the rule policy? Measured: none.

Wiring a model into a task is only worth doing if the rule leaves something
on the table. This battery computes the shortest possible episode for each
task and compares it with what the rule policy actually does, so a claim that
"the model could help here" has to survive a number.

Measured over seeds 0-19 on the shipped 8x8 tasks:

    T1_forage          rule 15.40   optimal 15.40   gap 0 on 20/20
    T2_delayed_match   rule  8.00   optimal  8.00   gap 0 on 20/20
    T3_navigate        rule  7.15   optimal  7.15   gap 0 on 20/20

``main`` exits 0 when the rule is optimal everywhere (the pinned finding)
and 1 when headroom appears, which is the signal that a task was changed
enough to make a learned policy worth measuring.
"""

import itertools
import json
from collections import deque

from agent import Agent
from worlds.grid import SIZE, TASKS, GridWorld

DEFAULT_SEEDS = tuple(range(20))


def bfs_distance(start, goal, blocked=()):
    """Shortest path length on the grid, or None when unreachable."""
    start, goal = tuple(start), tuple(goal)
    blocked = {tuple(cell) for cell in blocked}
    if start == goal:
        return 0
    if goal in blocked:
        return None
    seen = {start}
    queue = deque([(start, 0)])
    while queue:
        (x, y), distance = queue.popleft()
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            nx, ny = x + dx, y + dy
            if not (0 <= nx < SIZE and 0 <= ny < SIZE):
                continue
            cell = (nx, ny)
            if cell in blocked or cell in seen:
                continue
            if cell == goal:
                return distance + 1
            seen.add(cell)
            queue.append((cell, distance + 1))
    return None


def optimal_steps(task, seed):
    """Shortest episode the task allows, or None when it is unreachable."""
    world = GridWorld(task, seed)
    world.reset()
    if task == "T1_forage":
        return _forage_optimum([tuple(cell) for cell in world._initial_items])
    if task == "T2_delayed_match":
        return _match_optimum(tuple(world._target))
    return bfs_distance((0, 0), tuple(world._target),
                        [tuple(cell) for cell in world._obstacles])


def _forage_optimum(items):
    """Best visiting order; each item costs its path plus one ``collect``."""
    best = None
    for order in itertools.permutations(items):
        total, current = 0, (0, 0)
        for item in order:
            hop = bfs_distance(current, item)
            if hop is None:
                total = None
                break
            total += hop + 1
            current = item
        if total is not None and (best is None or total < best):
            best = total
    return best


def _match_optimum(target):
    """Reach the target, then collect; the reward needs two elapsed steps."""
    hop = bfs_distance((0, 0), target)
    return None if hop is None else max(hop + 1, 2)


def headroom(seeds=DEFAULT_SEEDS):
    """Compare rule steps with the optimum, per task and overall."""
    report = {}
    for task in TASKS:
        rows = []
        for seed in seeds:
            rule = len(Agent().run_task(task, seed, max_steps=200))
            rows.append({"seed": seed, "rule": rule,
                         "optimal": optimal_steps(task, seed)})
        gaps = [row["rule"] - row["optimal"] for row in rows]
        report[task] = {
            "seeds": len(rows),
            "rule_mean": sum(row["rule"] for row in rows) / len(rows),
            "optimal_mean": sum(row["optimal"] for row in rows) / len(rows),
            "max_gap": max(gaps),
            "suboptimal_seeds": [row["seed"] for row, gap in zip(rows, gaps)
                                 if gap > 0],
        }
    report["optimal_everywhere"] = all(
        not task_row["suboptimal_seeds"]
        for name, task_row in report.items() if name in TASKS)
    return report


def main():
    """Print the ceiling report; 0 when the rule is already optimal."""
    report = headroom()
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["optimal_everywhere"]:
        print("policy_ceiling: the rule leaves steps on the table; a learned "
              "policy now has somewhere to win.")
        raise SystemExit(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
