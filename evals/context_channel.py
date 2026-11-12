"""Measure a world-provided context channel against the pair gate.

ADR-182 left one reopening condition: a task with independent, non-leaky
state. ``worlds.dual.DualWorld`` is that task — two independent latent bits
per phase, reward ``a XOR b`` — and it exports the pair through the agent's
optional ``G`` signal block. This module asks the measurement question:
does the signed pair scan recover the planted interaction from real agent
traces, and does a noise world with the same latents select nothing?

Run ``python -m evals.context_channel`` for the numbers.
"""

import json

from agent import Agent
from evals.module_state import signals_from_trace
from evals.replication import scan_with_holdout
from worlds.dual import DualWorld, NoiseDualWorld


def collect_rows(world_factory, seeds, include_context=True):
    """Run one agent per seed and return extended signal rows plus targets."""
    rows = []
    for seed in seeds:
        agent = Agent(world=world_factory(seed))
        rows.extend(signals_from_trace(agent.run(max_steps=4),
                                       include_context=include_context))
    return rows, [row[-1] for row in rows]


def measure(world_class=DualWorld, train_seeds=range(20),
            holdout_seeds=range(20, 40), trials=200, include_context=True):
    """Return the signed holdout result for a world class.

    ``include_context=False`` is the executable ablation: the context block
    is still emitted by the world, but the reader drops it, so the planted
    pair must disappear from the selection.
    """
    train_rows, train_target = collect_rows(world_class, train_seeds,
                                            include_context=include_context)
    holdout_rows, holdout_target = collect_rows(world_class, holdout_seeds,
                                                include_context=include_context)
    result = scan_with_holdout(train_rows, train_target,
                               holdout_rows, holdout_target,
                               trials=trials, direction="positive")
    selected = sorted(item["candidate"]["columns"]
                      for item in result["selected"])
    return {
        "world": world_class.task_id,
        "rows": len(train_rows),
        "selected": selected,
        "rejected": len(result["rejected"]),
        "g_pair_selected": [6, 7] in selected,
    }


def measure_choice(use_context=True, episodes=40, phases=4):
    """Learn to *act* on the XOR: the rewarded action needs both latents.

    One agent runs every episode, so the online table persists and the
    policy can improve. ``use_context=False`` keys the predictor on the
    shipped ``(task, action, distance)`` feature and is the blind ablation:
    the same planner, the same world, no context.
    """
    from agent import Agent
    from planner.plan import LearnedPlanner
    from worlds.dual import ChoiceDualWorld

    planner = LearnedPlanner(use_context=use_context)
    agent = Agent(planner=planner, learn_context=use_context)
    per_episode = []
    for seed in range(episodes):
        agent.world = ChoiceDualWorld(seed)
        trace = agent.run(max_steps=phases)
        per_episode.append(sum(float(step.get("reward", 0.0))
                               for step in trace) / max(1, len(trace)))
    half = max(1, len(per_episode) // 2)
    return {
        "world": ChoiceDualWorld.task_id,
        "episodes": episodes,
        "steps": episodes * phases,
        "accuracy": sum(per_episode) / len(per_episode),
        "first_half_accuracy": sum(per_episode[:half]) / half,
        "last_half_accuracy": sum(per_episode[-half:]) / half,
        "learned_keys": len(agent.online_predictions()),
    }


def main():
    result = {
        "planted": measure(DualWorld),
        "noise": measure(NoiseDualWorld),
        "choice": measure_choice(),
        "choice_blind": measure_choice(use_context=False),
    }
    print(json.dumps(result, sort_keys=True))
    ok = (result["planted"]["g_pair_selected"]
          and result["noise"]["selected"] == []
          and result["choice"]["last_half_accuracy"] > 0.85
          and result["choice_blind"]["last_half_accuracy"] < 0.65)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
