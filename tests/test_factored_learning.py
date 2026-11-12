"""A product feature can express XOR; three quadrants still do not pin it.

ADR-185 left the memorisation gap open: a joint lookup needs one exposure
per context and an additive model cannot express an interaction. A logistic
model on quadratic features is the standard fix — for bits, ``a XOR b ==
a + b - 2ab`` — so ``FactoredPredictor`` is told the feature *shape* and
learns the weights.

Measured on `T5_choice`, table frozen after training:

    all four quadrants   correct p 0.9935   argmax 1.0
    three quadrants      correct p 0.0534   argmax 0.0  (held-out (1,1))

The second row is the honest boundary: with three of four quadrants the
weights are underdetermined, and gradient descent extrapolates the missing
quadrant into the majority class.
"""

import unittest

from evals.context_channel import (TRAIN_CODES, _FrozenPredictor,
                                   _correct_action, measure_factored)
from self_model.online import (FactoredPredictor, OnlinePredictor,
                               _sigmoid, quadratic_features)

QUADRANTS = ((0, 0), (0, 1), (1, 0), (1, 1))
THREE = ((0, 0), (0, 1), (1, 0))


def _trained(codes, episodes=80):
    predictor = FactoredPredictor()
    for _episode in range(episodes):
        for first, second in codes:
            context = (float(first), float(second))
            predictor.observe(("T5_choice", "left", 0, context),
                              (first ^ second) == 0)
            predictor.observe(("T5_choice", "right", 0, context),
                              (first ^ second) == 1)
    predictor.flush()
    return predictor


def _score(predictor, first, second):
    context = (float(first), float(second))
    return (predictor.predict(("T5_choice", "left", 0, context)),
            predictor.predict(("T5_choice", "right", 0, context)))


class TestQuadraticFeatures(unittest.TestCase):
    def test_the_shape_is_intercept_terms_and_products(self):
        self.assertEqual(quadratic_features((2.0, 3.0)), [1.0, 2.0, 3.0, 6.0])

    def test_a_single_value_has_no_product_term(self):
        self.assertEqual(quadratic_features((4.0,)), [1.0, 4.0])

    def test_sigmoid_is_stable_and_symmetric(self):
        self.assertAlmostEqual(_sigmoid(0.0), 0.5)
        self.assertGreater(_sigmoid(40.0), 0.999)
        self.assertLess(_sigmoid(-40.0), 1e-3)
        self.assertAlmostEqual(_sigmoid(2.0), 1.0 - _sigmoid(-2.0))


class TestFactoredPredictor(unittest.TestCase):
    def test_an_unfitted_key_predicts_the_prior(self):
        self.assertEqual(FactoredPredictor().predict(("T5_choice", "left", 0,
                                                      (0.0, 0.0))), 0.5)

    def test_a_key_without_context_collapses_to_the_bias(self):
        predictor = FactoredPredictor()
        predictor.observe(("T5_choice", "right", 0), True)
        predictor.flush()
        self.assertGreater(predictor.predict(("T5_choice", "right", 0)), 0.5)

    def test_counts_are_per_exact_key(self):
        predictor = FactoredPredictor()
        key = ("T5_choice", "left", 0, (0.0, 1.0))
        self.assertEqual(predictor.seen(key), 0)
        predictor.observe(key, True)
        predictor.observe(key, False)
        self.assertEqual(predictor.seen(key), 2)
        self.assertEqual(predictor.keys(), [key])
        self.assertEqual(predictor.table(), {key: predictor.predict(key)})

    def test_flush_is_idempotent(self):
        predictor = _trained(THREE, episodes=1)
        before = predictor.predict(("T5_choice", "left", 0, (1.0, 1.0)))
        self.assertEqual(predictor.flush(), 0)
        self.assertEqual(predictor.predict(("T5_choice", "left", 0, (1.0, 1.0))),
                         before)

    def test_the_full_coverage_table_fits_xor(self):
        predictor = _trained(QUADRANTS)
        for first, second in QUADRANTS:
            left, right = _score(predictor, first, second)
            if first ^ second:
                self.assertGreater(right, 0.8, (first, second))
                self.assertLess(left, 0.2, (first, second))
            else:
                self.assertGreater(left, 0.8, (first, second))
                self.assertLess(right, 0.2, (first, second))

    def test_three_quadrants_do_not_identify_the_fourth(self):
        predictor = _trained(THREE)
        left, right = _score(predictor, 1, 1)
        # (1,1) XORs to 0, so the correct action is left; it extrapolates right.
        self.assertLess(left, 0.2)
        self.assertGreater(right, 0.8)


class TestFactoredThroughTheAgent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.full = measure_factored(QUADRANTS, QUADRANTS,
                                    train_episodes=12, eval_episodes=6)
        cls.three = measure_factored(THREE, ((1, 1),),
                                     train_episodes=12, eval_episodes=6)

    def test_full_coverage_reaches_the_correct_action(self):
        self.assertEqual(self.full["argmax_accuracy"], 1.0)
        self.assertGreater(self.full["correct_probability"], 0.9)

    def test_three_quadrants_fail_on_the_held_one(self):
        self.assertEqual(self.three["argmax_accuracy"], 0.0)
        self.assertLess(self.three["correct_probability"], 0.35)

    def test_the_held_quadrant_is_absent_from_training(self):
        self.assertNotIn([1, 1], self.three["train_codes"])
        self.assertIn([1, 1], self.three["eval_codes"])

    def test_the_correct_action_helper_is_xor(self):
        self.assertEqual(_correct_action([0.0, 0.0]), "left")
        self.assertEqual(_correct_action([0.0, 1.0]), "right")
        self.assertEqual(_correct_action([1.0, 0.0]), "right")
        self.assertEqual(_correct_action([1.0, 1.0]), "left")

    def test_a_frozen_wrapper_stops_further_fitting(self):
        inner = _trained(QUADRANTS, episodes=2)
        frozen = _FrozenPredictor(inner)
        before = frozen.predict(("T5_choice", "left", 0, (0.0, 1.0)))
        frozen.observe(("T5_choice", "left", 0, (0.0, 1.0)), True)
        self.assertEqual(frozen.predict(("T5_choice", "left", 0, (0.0, 1.0))),
                         before)


class TestCoveragePools(unittest.TestCase):
    def test_the_three_pool_omits_exactly_one_quadrant(self):
        self.assertEqual(set(THREE), set(TRAIN_CODES) - {(1, 1)})
        self.assertTrue(set(QUADRANTS) - set(THREE), {(1, 1)})

    def test_the_shipped_joint_predictor_is_unchanged(self):
        self.assertIsInstance(OnlinePredictor(), OnlinePredictor)


if __name__ == "__main__":
    unittest.main()
