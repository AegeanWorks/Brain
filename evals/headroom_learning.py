"""Can the brain *learn* the deadline rule instead of being handed it?

ADR-193 proved headroom exists and that a hand-built earliest-deadline plan
reaches the optimum. The open question is whether a policy can be learned
from outcomes and carry to seeds it never trained on.

The policy family is one number: order items by
``distance_rank + weight * deadline_rank``. ``weight=0`` is the shortest-tour
ablation's distance order; a large weight is earliest-deadline-first.

    weight      0  0.5    1    2    4    8   16
    tour items 3.0  3.0  3.0  3.0 4.0 4.0 4.0     (mean over seeds 0-19)

The learner is the project's own ``OnlinePredictor`` behind a deterministic
UCB1 bandit: an arm is a weight, an episode evaluates that weight on every
training seed, and the outcome is "collected every item, yes or no". After
one trial per arm it picks the first arm with the best success rate, then
that single choice is scored on held-out seeds. The shipped planner now
schedules per item, so the learned scalar ties it on 4 items (4.00 vs 4.00)
and still does not carry to 5 or 6 items, where the schedule collects all.
"""

import json
import math

from worlds.deadline import DeadlineWorld

from evals.headroom import _plan_actions

DEFAULT_WEIGHTS = (0.0, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0)
TRAIN_SEEDS = tuple(range(10))
HOLDOUT_SEEDS = tuple(range(10, 20))


def _world(seed, items=None):
    """The deadline world for a seed, optionally with a different item count."""
    return DeadlineWorld(seed) if items is None else DeadlineWorld(seed, items=items)


def order_for_weight(seed, weight, items=None):
    """Visit order under ``distance_rank + weight * deadline_rank``."""
    items = list(_world(seed, items).items)
    cells = [tuple(item["cell"]) for item in items]
    by_distance = sorted(items, key=lambda item: (
        abs(item["cell"][0]) + abs(item["cell"][1]), item["cell"]))
    by_deadline = sorted(items, key=lambda item: (item["deadline"], item["cell"]))
    distance_rank = {tuple(item["cell"]): rank
                     for rank, item in enumerate(by_distance)}
    deadline_rank = {tuple(item["cell"]): rank
                     for rank, item in enumerate(by_deadline)}
    return sorted(cells,
                  key=lambda cell: distance_rank[cell] + weight * deadline_rank[cell])


def run_order(seed, actions, items=None):
    """Execute one action list on the real world; return items collected."""
    world = _world(seed, items)
    world.reset()
    collected = 0
    for action in actions:
        _state, reward, done = world.step(action)
        collected += reward
        if done:
            break
    return collected


def evaluate_weight(seed, weight, items=None):
    """Items collected when this weight chooses the order for ``seed``."""
    return run_order(seed, _plan_actions(order_for_weight(seed, weight, items)),
                     items=items)


def success_rate(weight, seeds, items=None):
    """Fraction of seeds where this weight collects every item."""
    full = float(_world(seeds[0], items).item_count)
    hits = sum(1 for seed in seeds
               if evaluate_weight(seed, weight, items) == full)
    return hits / len(seeds)


def _ucb(predict, counts, total, arm):
    """UCB1 score; an untried arm wins, which makes exploration explicit."""
    seen = counts.get(arm, 0)
    if seen == 0:
        return float("inf")
    return predict(arm) + math.sqrt(2.0 * math.log(max(1, total)) / seen)


def learn(train_seeds=TRAIN_SEEDS, arms=DEFAULT_WEIGHTS, episodes=None):
    """Choose a weight from outcomes alone, with the brain's own predictor.

    Returns the chosen weight, the trials per arm and the observations the
    predictor accumulated, so a caller can audit what was learned rather
    than trusting a scalar.
    """
    from self_model.online import OnlinePredictor

    predictor = OnlinePredictor()
    counts = {}
    trials = 0
    history = []
    limit = episodes if episodes is not None else len(arms)
    for _episode in range(limit):
        scores = {arm: _ucb(lambda a: predictor.predict(("T6_deadline", str(a))),
                            counts, trials, arm)
                  for arm in arms}
        arm = max(arms, key=lambda a: (scores[a], -arms.index(a)))
        rate = success_rate(arm, train_seeds)
        predictor.observe(("T6_deadline", str(arm)), rate >= 1.0)
        counts[arm] = counts.get(arm, 0) + 1
        trials += 1
        history.append({"arm": arm, "train_success": rate})
    chosen = max(arms, key=lambda a: (predictor.predict(("T6_deadline", str(a))),
                                      -arms.index(a)))
    return {
        "chosen": chosen,
        "trials": history,
        "table": {arm: predictor.predict(("T6_deadline", str(arm)))
                  for arm in arms},
    }


def measure():
    """Learn on train seeds, score on held-out seeds, compare both rules."""
    from evals.headroom import rule_collected, tour_rule_collected

    learned = learn()
    chosen = learned["chosen"]
    tour_mean = sum(tour_rule_collected(seed)["collected"]
                    for seed in HOLDOUT_SEEDS) / len(HOLDOUT_SEEDS)
    shipped_mean = sum(rule_collected(seed)["collected"]
                       for seed in HOLDOUT_SEEDS) / len(HOLDOUT_SEEDS)
    held_mean = sum(evaluate_weight(seed, chosen)
                    for seed in HOLDOUT_SEEDS) / len(HOLDOUT_SEEDS)
    return {
        "chosen_weight": chosen,
        "episodes": len(learned["trials"]),
        "arms_tried": sorted({row["arm"] for row in learned["trials"]}),
        "train_success": {str(arm): rate
                          for arm, rate in ((arm, success_rate(arm, TRAIN_SEEDS))
                                            for arm in DEFAULT_WEIGHTS)},
        "holdout_items": held_mean,
        "holdout_tour_items": tour_mean,
        "holdout_shipped_items": shipped_mean,
        "holdout_tour_gain": held_mean - tour_mean,
        "holdout_shipped_gain": held_mean - shipped_mean,
        "table": learned["table"],
    }


def main():
    """Print the learning report; 0 when the learned weight beats the tour."""
    report = measure()
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["holdout_tour_gain"] <= 0:
        print("headroom_learning: the learned weight did not beat the tour")
        raise SystemExit(1)
    print("headroom_learning: chose weight %s after %d episodes; held-out "
          "%.2f vs tour %.2f and shipped %.2f items."
          % (report["chosen_weight"], report["episodes"],
             report["holdout_items"], report["holdout_tour_items"],
             report["holdout_shipped_items"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
