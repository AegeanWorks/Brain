#!/usr/bin/env python3
"""Ten-second demo: run a real episode and print what actually happened.

    python demo.py                     human-readable trace
    python demo.py --scripted [--seed] machine-readable WORLD-DELTA lines

The earlier version printed hardcoded ``WORLD-DELTA`` lines and never
touched a world, a policy or a step counter, so it proved nothing. Both
modes now come from one real episode: the deltas are the position and item
counts the agent actually produced, which makes the seeded replay check in
``.aikit/compat.json`` meaningful rather than decorative.

No model and no network are needed; use ``brain.py`` for the model.
"""

import argparse

from agent import Agent
from worlds.grid import TASKS


def _parse(argv):
    parser = argparse.ArgumentParser(
        prog="demo", description="Run one real episode and print the trace.")
    parser.add_argument("--task", default="T3_navigate", choices=TASKS)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-steps", type=int, default=200)
    parser.add_argument("--scripted", action="store_true",
                        help="print WORLD-DELTA lines instead of a trace")
    return parser.parse_args(argv)


def deltas(previous, state):
    """Return ``[(key, old, new)]`` for the world facts that changed."""
    rows = []
    for key in ("x", "y", "items"):
        before, after = previous.get(key), state.get(key)
        if before != after:
            rows.append((key, before, after))
    return rows


def scripted_lines(task, seed, trace):
    """Render one machine-readable line per changed world fact."""
    lines = []
    previous = {"x": None, "y": None, "items": 0}
    for step in trace:
        state = step.get("state") or {}
        for key, before, after in deltas(previous, state):
            lines.append("WORLD-DELTA: %s=%s->%s" % (key, before, after))
        previous = {"x": state.get("x"), "y": state.get("y"),
                    "items": state.get("items", previous["items"])}
    lines.append("WORLD-DELTA: steps=0->%d" % len(trace))
    return ["task=%s seed=%d" % (task, seed)] + lines


def human_lines(trace):
    """Render the same episode as something a person can read."""
    lines = []
    for index, step in enumerate(trace, 1):
        state = step.get("state") or {}
        reward = float(step.get("reward", 0.0))
        marker = " +%.1f" % reward if reward > 0 else ""
        lines.append("  %2d %-8s [%s,%s]%s"
                     % (index, step.get("action"), state.get("x"),
                        state.get("y"), marker))
    return lines


def main(argv=None):
    """Run the episode and print it; 0 when the task finished."""
    args = _parse(argv)
    agent = Agent()
    trace = agent.run_task(args.task, args.seed, max_steps=args.max_steps)
    if args.scripted:
        for line in scripted_lines(args.task, args.seed, trace):
            print(line)
    else:
        print("task %s, seed %d" % (args.task, args.seed))
        for line in human_lines(trace):
            print(line)
        verdict, reason = agent._episode_verdict(trace, args.max_steps)
        total = sum(float(step.get("reward", 0.0)) for step in trace)
        print("%s (%s), total reward %.1f" % (verdict, reason, total))
        return 0 if verdict == "done" else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
