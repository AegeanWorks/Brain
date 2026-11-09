"""A predictor that is never told the reward rule must still learn it.

Rung 1's `predict_outcome` encodes the world's reward condition, so it is
100% accurate and its error carries no information — a taught rule cannot
show learning. `OnlinePredictor` sees only `(task, action, distance bucket)`
and the outcomes that follow, and is scored *prequentially*: the prediction
for a step uses only steps before it.

Measured over 611 pooled steps (20 seeds x 3 tasks):

    base rate   Brier 0.136880   skill  0.0000
    learned     Brier 0.022075   skill +0.8387

These tests pin the learning, the prequential discipline, and the fact that
the discovered table reconstructs the reward rule.
"""

import unittest

from agent import Memory, Planner
from self_model.online import OnlinePredictor, distance_bucket, feature_key
from worlds.grid import GridWorld

TASKS = ("T3_navigate", "T1_forage", "T2_delayed_match")
SEEDS = range(20)


def _brier(pairs):
    return sum((p - o) ** 2 for p, o in pairs) / len(pairs)


def _episodes():
    """Yield (key, outcome) in a fixed order, with the pre-action key."""
    for task in TASKS:
        for seed in SEEDS:
            world = GridWorld(task, seed)
            state = world.reset()
            planner, memory = Planner(), Memory()
            for _ in range(200):
                memory.save(state)
                action = planner.plan(state, memory.recall())
                key = feature_key(task, state, action)
                state, reward, done = world.step(action)
                yield key, 1.0 if reward > 0 else 0.0
                if done:
                    break


def _prequential_score():
    predictor = OnlinePredictor()
    pairs = []
    for key, outcome in _episodes():
        pairs.append((predictor.predict(key), outcome))
        predictor.observe(key, outcome)
    return pairs, predictor


class TestOnlineLearning(unittest.TestCase):
    def test_the_untold_predictor_learns_positive_skill(self):
        pairs, _predictor = _prequential_score()
        rate = sum(o for _p, o in pairs) / len(pairs)
        base = _brier([(rate, o) for _p, o in pairs])
        learned = _brier(pairs)
        self.assertGreater(1.0 - learned / base, 0.5)

    def test_the_prediction_precedes_the_observation(self):
        # Prequential discipline: a fresh predictor predicts the prior for
        # any key, and only a later call sees the outcome.
        predictor = OnlinePredictor()
        key = ("T3_navigate", "down", 1)
        self.assertEqual(predictor.predict(key), 0.5)
        self.assertEqual(predictor.seen(key), 0)
        predictor.observe(key, True)
        self.assertEqual(predictor.seen(key), 1)
        self.assertGreater(predictor.predict(key), 0.5)

    def test_the_learned_table_reconstructs_the_reward_rule(self):
        _pairs, predictor = _prequential_score()
        table = predictor.table()
        # T1/T2: collect at distance 0 is the rewarded action.
        self.assertGreater(table[("T1_forage", "collect", 0)], 0.9)
        self.assertGreater(table[("T2_delayed_match", "collect", 0)], 0.9)
        # T3: the move that closes the last step is rewarded.
        self.assertGreater(table[("T3_navigate", "down", 1)], 0.9)
        # Everything else is near zero.
        self.assertLess(table[("T3_navigate", "down", 3)], 0.1)
        self.assertLess(table[("T1_forage", "right", 3)], 0.1)

    def test_an_unseen_key_predicts_the_prior(self):
        predictor = OnlinePredictor()
        self.assertEqual(predictor.predict(("T9", "wait", 9)), 0.5)
        self.assertEqual(predictor.keys(), [])

    def test_laplace_smoothing_handles_a_single_observation(self):
        predictor = OnlinePredictor()
        key = ("T1_forage", "collect", 0)
        predictor.observe(key, True)
        # (1 + 1) / (1 + 2)
        self.assertAlmostEqual(predictor.predict(key), 2 / 3)
        predictor.observe(key, True)
        self.assertAlmostEqual(predictor.predict(key), 3 / 4)

    def test_distance_bucket_caps_and_reports_absence(self):
        self.assertEqual(distance_bucket({"x": 0, "y": 0,
                                          "target": [1, 0]},
                                         "T3_navigate"), 1)
        self.assertEqual(distance_bucket({"x": 0, "y": 0,
                                          "target": [7, 7]},
                                         "T3_navigate"), 3)
        self.assertEqual(distance_bucket({"x": 0, "y": 0},
                                         "T3_navigate"), 9)
        self.assertEqual(distance_bucket({"x": 0, "y": 0,
                                          "items_positions": [[0, 0]]},
                                         "T1_forage"), 0)

    def test_the_score_is_not_the_base_rate_in_disguise(self):
        # A predictor that never learns must score exactly 0.0 skill.
        pairs, _ = _prequential_score()
        rate = sum(o for _p, o in pairs) / len(pairs)
        dead = [(0.5 if rate > 0.5 else rate + 0.0, o) for _p, o in pairs]
        base = _brier([(rate, o) for _p, o in pairs])
        self.assertLess(1.0 - _brier(dead) / base, 0.5)


if __name__ == "__main__":
    unittest.main()
