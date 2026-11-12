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
from worlds.dual import ChoiceDualWorld, DualWorld, NoiseDualWorld


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


#: Latent pairs the policy trains on: every value is 0 or 1.
TRAIN_CODES = ((0, 0), (0, 1), (1, 0), (1, 1))

#: Latent pairs it is tested on: every value is >= 2, so no context key
#: seen in training can match one of them.
EVAL_CODES = ((2, 0), (2, 1), (2, 2), (2, 3),
              (3, 0), (3, 1), (3, 2), (3, 3))


def _run_pinned(agent, codes, episodes):
    """Run episodes over a fixed cycle of latent codes; return step rewards."""
    rewards = []
    for episode in range(episodes):
        batch = [codes[(episode * 4 + index) % len(codes)] for index in range(4)]
        agent.world = ChoiceDualWorld(episode, latents=batch)
        trace = agent.run(max_steps=4)
        rewards.extend(float(step.get("reward", 0.0)) for step in trace)
    return rewards


class _FrozenPredictor:
    """A predictor that predicts from its counts but learns nothing new.

    Freezing separates two questions the learned policy can answer: does the
    table carry to an unseen context at all (zero-shot), and how fast does
    the same policy pick a new context up once it sees the outcome?
    """

    def __init__(self, inner):
        self._inner = inner

    def predict(self, key):
        return self._inner.predict(key)

    def observe(self, key, outcome):
        return self._inner.seen(key), self._inner.seen(key)

    def table(self):
        return self._inner.table()

    def keys(self):
        return self._inner.keys()

    def seen(self, key):
        return self._inner.seen(key)


def measure_choice_generalization(train_episodes=40, eval_episodes=20,
                                  backoff=False, predictor="joint"):
    """Train on one set of latent codes and test on a disjoint set.

    The learned key is a lookup on the observed context, so the question is
    whether the policy carries to contexts it never saw. ``EVAL_CODES`` use
    latent values 2 and 3 while ``TRAIN_CODES`` use only 0 and 1, so every
    evaluation row is an unseen key. Three readings come out of one trained
    table: ``frozen`` accuracy on the training codes (control), ``frozen``
    accuracy on the unseen codes (zero-shot), and the learning curve on the
    unseen codes split into first exposure and everything after it.

    ``predictor="additive"`` swaps in ``AdditivePredictor``, which sums
    per-feature evidence instead of memorising the joint key. It is the
    representation ablation: an additive model cannot express XOR.
    """
    from agent import Agent
    from planner.plan import LearnedPlanner
    from self_model.online import AdditivePredictor, OnlinePredictor

    agent = Agent(planner=LearnedPlanner(backoff=backoff), learn_context=True)
    if predictor == "additive":
        agent.use_predictor(AdditivePredictor())
    elif predictor != "joint":
        raise ValueError(
            "Why: predictor must be joint or additive. "
            "Fix: pass predictor='joint'.")
    train_rewards = _run_pinned(agent, TRAIN_CODES, train_episodes)
    trained = agent.online_predictor()

    agent.use_predictor(_FrozenPredictor(trained))
    control = _run_pinned(agent, TRAIN_CODES, eval_episodes)
    zero_shot = _run_pinned(agent, EVAL_CODES, eval_episodes)

    agent.use_predictor(trained)
    curve = _run_pinned(agent, EVAL_CODES, eval_episodes)
    first_cycle = 8
    return {
        "world": ChoiceDualWorld.task_id,
        "predictor": predictor,
        "backoff": backoff,
        "train_steps": len(train_rewards),
        "train_accuracy": sum(train_rewards) / max(1, len(train_rewards)),
        "in_distribution_accuracy": sum(control) / max(1, len(control)),
        "zero_shot_accuracy": sum(zero_shot) / max(1, len(zero_shot)),
        "first_exposure_accuracy": sum(curve[:first_cycle]) / first_cycle,
        "adapted_accuracy": sum(curve[first_cycle:]) / max(1, len(curve) - first_cycle),
        "held_out_steps": len(curve),
        "learned_keys": len(trained.table()),
    }


def _correct_action(context):
    """The rewarded action for one observed latent pair (binary bits)."""
    first, second = int(context[0]), int(context[1])
    return "right" if (first ^ second) else "left"


def _correct_probabilities(agent, codes, episodes):
    """Run pinned episodes; return p(correct action) and the argmax hit rate.

    The context is read from the trace's pre-action ``G`` signal, so the
    score is what the policy believed before acting, not a post-hoc value.
    """
    probabilities = []
    hits = 0
    steps = 0
    for episode in range(episodes):
        code = codes[episode % len(codes)]
        agent.world = ChoiceDualWorld(episode, latents=[code] * 4)
        trace = agent.run(max_steps=4)
        for step in trace:
            context = (step.get("signals") or {}).get("G")
            if not context:
                continue
            scores = agent.planner.scores({"x": 0, "y": 0, "task": ChoiceDualWorld.task_id,
                                           "target": [0, 0], "context": list(context)})
            correct = _correct_action(context)
            probabilities.append(scores[correct])
            chosen = "right" if scores["right"] > scores["left"] else "left"
            hits += 1 if chosen == correct else 0
            steps += 1
    return {
        "correct_probability": sum(probabilities) / max(1, len(probabilities)),
        "argmax_accuracy": hits / max(1, steps),
        "steps": steps,
    }


def measure_factored(train_codes, eval_codes=(0, 0), train_episodes=40,
                     eval_episodes=8):
    """Train a quadratic-feature learner and score a held-out quadrant.

    ``train_codes`` is the quadrant coverage the learner sees; ``eval_codes``
    is the pool it is scored on *after* the table is frozen. Full coverage
    (all four quadrants) identifies the interaction; three of four does not.
    """
    from agent import Agent
    from planner.plan import LearnedPlanner
    from self_model.online import FactoredPredictor

    predictor = FactoredPredictor()
    agent = Agent(planner=LearnedPlanner(), learn_context=True)
    agent.use_predictor(predictor)
    _run_pinned(agent, tuple(train_codes), train_episodes)
    predictor.flush()

    agent.use_predictor(_FrozenPredictor(predictor))
    held = _correct_probabilities(agent, tuple(eval_codes), eval_episodes)
    return {
        "train_codes": [list(code) for code in train_codes],
        "eval_codes": [list(code) for code in eval_codes],
        "correct_probability": held["correct_probability"],
        "argmax_accuracy": held["argmax_accuracy"],
        "steps": held["steps"],
    }


def main():
    result = {
        "planted": measure(DualWorld),
        "noise": measure(NoiseDualWorld),
        "choice": measure_choice(),
        "choice_blind": measure_choice(use_context=False),
        "generalization": measure_choice_generalization(),
        "additive": measure_choice_generalization(predictor="additive"),
        "factored_full": measure_factored(
            ((0, 0), (0, 1), (1, 0), (1, 1)),
            ((0, 0), (0, 1), (1, 0), (1, 1))),
        "factored_three": measure_factored(
            ((0, 0), (0, 1), (1, 0)), ((1, 1),)),
    }
    print(json.dumps(result, sort_keys=True))
    ok = (result["planted"]["g_pair_selected"]
          and result["noise"]["selected"] == []
          and result["choice"]["last_half_accuracy"] > 0.85
          and result["choice_blind"]["last_half_accuracy"] < 0.65
          and result["generalization"]["in_distribution_accuracy"] > 0.9
          and result["generalization"]["zero_shot_accuracy"] < 0.35
          and result["generalization"]["adapted_accuracy"] > 0.9
          and result["additive"]["in_distribution_accuracy"] < 0.65
          and result["factored_full"]["argmax_accuracy"] > 0.99
          and result["factored_three"]["argmax_accuracy"] < 0.25)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
