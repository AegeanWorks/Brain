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
from models.backend import ModelBackend
from worlds.grid import SIZE

CASES = (("T3_navigate", 15), ("T3_navigate", 65),
         ("T2_delayed_match", 3), ("T1_forage", 71))
MODES = ("guard-off", "guard-on", "skip-on")
SKIP_AFTER = 3


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", action="append", choices=MODES, default=[],
                        help="repeatable (default: all modes)")
    args = parser.parse_args()
    modes = tuple(args.mode) if args.mode else MODES
    print(json.dumps(run_battery(modes), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
