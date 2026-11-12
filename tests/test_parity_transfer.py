"""A representation that matches the rule transfers; the same weights do not.

ADR-186 showed the factored learner needs full quadrant support. The open
question is what happens with values *outside* the training range. The world
rule here is parity-invariant, and the transfer pool reuses the training
parity combinations at larger magnitudes, so only the feature map decides:

    raw features      seen 1.0   transfer 0.5   (chance, and saturated)
    parity features   seen 1.0   transfer 1.0

The raw arm saturates both actions above 0.99 on unseen scale, so its
correctness probability reads ~1.0 while the argmax is wrong; accuracy is
the only trustworthy readout under extrapolation.
"""

import unittest

from agent import Agent
from evals.context_channel import (TRAIN_CODES, TRANSFER_CODES,
                                   _FrozenPredictor, _run_pinned,
                                   _parity_correct_action, measure_transfer)
from planner.plan import LearnedPlanner
from self_model.online import (AdditivePredictor, FactoredPredictor,
                               quadratic_features)
from worlds.dual import ChoiceDualWorld

PARITY_QUADRANTS = ((0, 0), (0, 1), (1, 0), (1, 1))


def _trained(mode="parity", episodes=80):
    predictor = FactoredPredictor(feature_mode=mode)
    for _episode in range(episodes):
        for first, second in PARITY_QUADRANTS:
            context = (float(first), float(second))
            predictor.observe(("T5_choice", "left", 0, context),
                              (first ^ second) == 0)
            predictor.observe(("T5_choice", "right", 0, context),
                              (first ^ second) == 1)
    predictor.flush()
    return predictor


def _scores(predictor, first, second):
    context = (float(first), float(second))
    return (predictor.predict(("T5_choice", "left", 0, context)),
            predictor.predict(("T5_choice", "right", 0, context)))


class TestParityRule(unittest.TestCase):
    def test_the_rule_rejects_an_unknown_name(self):
        with self.assertRaises(ValueError):
            ChoiceDualWorld(0, rule="majority")

    def test_parity_ignores_magnitude(self):
        world = ChoiceDualWorld(0, latents=[(2, 4), (2, 5), (3, 4), (3, 5)],
                                rule="parity")
        expected = ["left", "right", "right", "left"]
        for index, want in enumerate(expected):
            world.i = index
            self.assertEqual(world.correct_action(), want)

    def test_the_xor_rule_still_reads_raw_bits(self):
        world = ChoiceDualWorld(0, latents=[(2, 4), (2, 5)], rule="xor")
        world.i = 0
        self.assertEqual(world.correct_action(), "right" if 2 ^ 4 else "left")
        world.i = 1
        self.assertEqual(world.correct_action(), "right" if 2 ^ 5 else "left")

    def test_rewards_follow_the_selected_rule(self):
        world = ChoiceDualWorld(0, latents=[(2, 3)], rule="parity")
        world.reset()
        self.assertEqual(world.correct_action(), "right")
        _state, reward, _done = world.step("right")
        self.assertEqual(reward, 1.0)
        world.reset()
        _state, reward, _done = world.step("left")
        self.assertEqual(reward, 0.0)


class TestParityFeatures(unittest.TestCase):
    def test_parity_reduces_values_before_the_products(self):
        self.assertEqual(quadratic_features((2, 3), "parity"), [1.0, 0.0, 1.0, 0.0])
        self.assertEqual(quadratic_features((4, 6), "parity"), [1.0, 0.0, 0.0, 0.0])

    def test_raw_keeps_the_shipped_scale(self):
        self.assertEqual(quadratic_features((2, 3)), [1.0, 2.0, 3.0, 6.0])

    def test_an_unknown_mode_is_refused(self):
        with self.assertRaises(ValueError):
            quadratic_features((1, 0), "log")
        with self.assertRaises(ValueError):
            FactoredPredictor(feature_mode="log")

    def test_parity_weights_transfer_to_larger_values(self):
        predictor = _trained("parity")
        for first, second in ((2, 4), (2, 5), (3, 4), (3, 5), (6, 8)):
            left, right = _scores(predictor, first, second)
            if (first % 2) ^ (second % 2):
                self.assertGreater(right, left, (first, second))
            else:
                self.assertGreater(left, right, (first, second))

    def test_raw_weights_do_not_transfer(self):
        predictor = _trained("raw")
        # The parity rule wants right at (2,5); raw features were fitted on
        # 0/1 magnitudes, so every larger context collapses onto the same
        # decision and the rule's own cases separate wrongly.
        wrong = 0
        for first, second in ((2, 5), (3, 4)):
            left, right = _scores(predictor, first, second)
            wrong += 1 if right <= left else 0
        self.assertEqual(wrong, 2)


class TestTransferThroughTheAgent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = measure_transfer(feature_mode="raw", train_episodes=20,
                                   eval_episodes=6)
        cls.parity = measure_transfer(feature_mode="parity", train_episodes=20,
                                      eval_episodes=6)

    def test_both_modes_fit_the_seen_contexts(self):
        self.assertGreaterEqual(self.raw["seen_accuracy"], 0.9)
        self.assertGreaterEqual(self.parity["seen_accuracy"], 0.9)

    def test_only_the_matching_feature_map_transfers(self):
        self.assertEqual(self.parity["transfer_accuracy"], 1.0)
        self.assertLessEqual(self.raw["transfer_accuracy"], 0.6)

    def test_the_raw_arm_is_saturated_so_its_probability_is_meaningless(self):
        self.assertGreater(self.raw["transfer_correct_probability"], 0.99)
        self.assertEqual(self.raw["transfer_saturated_steps"],
                         self.raw["transfer_steps"])

    def test_the_parity_arm_is_not_wholly_saturated(self):
        self.assertLess(self.parity["transfer_saturated_steps"],
                        self.parity["transfer_steps"])

    def test_the_transfer_pool_shares_no_value_with_training(self):
        train_values = {value for pair in TRAIN_CODES for value in pair}
        transfer_values = {value for pair in TRANSFER_CODES for value in pair}
        self.assertEqual(train_values, {0, 1})
        self.assertFalse(train_values & transfer_values)

    def test_every_transfer_parity_combination_was_trained(self):
        trained = {(first % 2, second % 2) for first, second in TRAIN_CODES}
        for first, second in TRANSFER_CODES:
            self.assertIn((first % 2, second % 2), trained)

    def test_the_parity_scorer_agrees_with_the_world(self):
        for first, second in TRANSFER_CODES:
            world = ChoiceDualWorld(0, latents=[(first, second)], rule="parity")
            world.reset()
            self.assertEqual(_parity_correct_action([first, second]),
                             world.correct_action())


class TestNoDefaultDrift(unittest.TestCase):
    def test_the_shipped_predictor_defaults_are_unchanged(self):
        self.assertEqual(FactoredPredictor()._mode, "raw")
        self.assertEqual(AdditivePredictor().predict(("T5_choice", "left", 0,
                                                      (1.0, 0.0))), 0.5)

    def test_a_frozen_parity_model_keeps_its_weights(self):
        inner = _trained("parity", episodes=2)
        frozen = _FrozenPredictor(inner)
        before = _scores(inner, 2, 4)
        frozen.observe(("T5_choice", "left", 0, (2.0, 4.0)), True)
        self.assertEqual(_scores(inner, 2, 4), before)


if __name__ == "__main__":
    unittest.main()
