"""The deadline rule can be learned from outcomes, within its configuration.

`evals.headroom_learning` treats the policy as one number -- order items by
``distance_rank + weight * deadline_rank`` -- and lets the brain's own
`OnlinePredictor` behind a UCB1 bandit choose that number from success rates.

Measured (train seeds 0-9, held-out 10-19):

    weight     0   0.5   1    2    4    8   16
    train    0.0   0.0  0.0  0.0  1.0  1.0  1.0   (fraction collecting all 4)
    chosen   4.0 after 7 episodes
    held-out 4.00 items vs the shortest-tour ablation's 3.00
    shipped  4.00 items at weight 4.0: the learned scalar ties the schedule

The boundary is part of the result: a *scalar* fitted to the 4-item task does
not carry to other item counts (at 6 items weight 4 gives 4.95 against the
tour rule's 5.00, while weight 8 gives 5.80). The shipped per-item schedule
collects 6/6 at the same count, so the missing piece was urgency per item,
not a constant tuned to one layout.
"""

import unittest

from evals.headroom_learning import (DEFAULT_WEIGHTS, HOLDOUT_SEEDS,
                                     TRAIN_SEEDS, evaluate_weight, learn,
                                     measure, order_for_weight, run_order,
                                     success_rate)
from worlds.deadline import DeadlineWorld

from evals.headroom import _plan_actions, rule_collected, tour_rule_collected


class TestOrderForWeight(unittest.TestCase):
    def test_weight_zero_is_the_distance_order(self):
        seed = 0
        items = DeadlineWorld(seed).items
        nearest = min(items, key=lambda item: (
            abs(item["cell"][0]) + abs(item["cell"][1]), item["cell"]))
        self.assertEqual(order_for_weight(seed, 0.0)[0], tuple(nearest["cell"]))

    def test_a_large_weight_starts_with_the_urgent_item(self):
        for seed in range(10):
            items = DeadlineWorld(seed).items
            urgent = min(items, key=lambda item: item["deadline"])
            self.assertEqual(order_for_weight(seed, 16.0)[0],
                             tuple(urgent["cell"]), seed)

    def test_the_order_is_a_permutation_of_the_items(self):
        seed = 3
        items = {tuple(item["cell"]) for item in DeadlineWorld(seed).items}
        for weight in DEFAULT_WEIGHTS:
            self.assertEqual(set(order_for_weight(seed, weight)), items)

    def test_the_order_is_deterministic(self):
        self.assertEqual(order_for_weight(5, 4.0), order_for_weight(5, 4.0))


class TestEvaluation(unittest.TestCase):
    def test_weight_zero_matches_the_tour_rule_on_a_known_seed(self):
        self.assertEqual(evaluate_weight(0, 0.0),
                         tour_rule_collected(0)["collected"])

    def test_a_deadline_weight_collects_every_item(self):
        for seed in (0, 1, 2):
            self.assertEqual(evaluate_weight(seed, 8.0),
                             DeadlineWorld(seed).item_count, seed)

    def test_run_order_never_exceeds_the_item_count(self):
        for seed in range(5):
            actions = _plan_actions(order_for_weight(seed, 8.0))
            self.assertLessEqual(run_order(seed, actions),
                                 DeadlineWorld(seed).item_count)

    def test_the_success_rates_separate_the_arms(self):
        self.assertEqual(success_rate(0.0, TRAIN_SEEDS), 0.0)
        self.assertEqual(success_rate(8.0, TRAIN_SEEDS), 1.0)

    def test_success_is_a_fraction(self):
        for weight in DEFAULT_WEIGHTS:
            rate = success_rate(weight, TRAIN_SEEDS)
            self.assertGreaterEqual(rate, 0.0)
            self.assertLessEqual(rate, 1.0)


class TestLearning(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.learned = learn()

    def test_every_arm_is_tried_once_before_any_is_repeated(self):
        tried = [row["arm"] for row in self.learned["trials"]]
        self.assertEqual(sorted(tried), sorted(DEFAULT_WEIGHTS))
        self.assertEqual(len(tried), len(DEFAULT_WEIGHTS))

    def test_the_chosen_weight_collects_everything_on_training_seeds(self):
        self.assertEqual(success_rate(self.learned["chosen"], TRAIN_SEEDS), 1.0)

    def test_the_chosen_weight_is_one_of_the_working_arms(self):
        self.assertIn(self.learned["chosen"], (4.0, 8.0, 16.0))

    def test_the_table_records_what_was_learned(self):
        table = self.learned["table"]
        self.assertEqual(set(table), set(DEFAULT_WEIGHTS))
        self.assertLess(table[0.0], table[8.0])


class TestHeldOut(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = measure()

    def test_the_learned_weight_beats_the_tour_rule_on_unseen_seeds(self):
        self.assertGreater(self.report["holdout_tour_gain"], 0.5)
        self.assertEqual(self.report["holdout_items"], 4.0)
        self.assertEqual(self.report["holdout_tour_items"], 3.0)

    def test_the_learned_scalar_ties_the_shipped_schedule(self):
        self.assertEqual(self.report["holdout_shipped_items"], 4.0)
        self.assertEqual(self.report["holdout_shipped_gain"], 0.0)

    def test_the_holdout_and_training_seeds_do_not_overlap(self):
        self.assertFalse(set(TRAIN_SEEDS) & set(HOLDOUT_SEEDS))

    def test_every_arm_was_tried(self):
        self.assertEqual(self.report["episodes"], len(DEFAULT_WEIGHTS))


class TestBoundary(unittest.TestCase):
    def test_the_scalar_does_not_carry_to_a_larger_item_count(self):
        # Fitted on 4 items; at 6 items the scalar buys less than the
        # per-item schedule. Recorded, not wished away.
        def mean_items(weight, count):
            total = 0.0
            for seed in range(10):
                world = DeadlineWorld(seed, items=count)
                world.reset()
                actions = _plan_actions(order_for_weight(seed, weight,
                                                         items=count))
                collected = 0.0
                for action in actions:
                    _state, reward, done = world.step(action)
                    collected += reward
                    if done:
                        break
                total += collected
            return total / 10

        rule_six = mean_items(0.0, 6)
        learned_six = mean_items(4.0, 6)
        better_six = mean_items(8.0, 6)
        shipped_six = sum(rule_collected(seed, items=6)["collected"]
                          for seed in range(10)) / 10
        # The learned constant does not reach the schedule's 6/6, while the
        # shipped per-item schedule does; the missing piece was urgency per
        # item, not a larger constant.
        self.assertEqual(shipped_six, 6.0)
        self.assertLess(better_six, shipped_six)
        self.assertLessEqual(learned_six, rule_six)


if __name__ == "__main__":
    unittest.main()
