"""A joint lookup memorises a context; an additive model cannot express it.

ADR-184 showed the learned policy beats a blind one on `T5_choice`. This
module asks the two follow-up questions a lookup table invites, and pins the
answers as a negative result:

1. Does the learned table carry to contexts it never saw? No. Trained on
   latent values 0/1 and tested on values 2/3, the joint table scores 0.25
   zero-shot — exactly the blind tie-break baseline — and 1.0 once each
   context has been observed once. ``backoff`` to the context-free marginal
   does not change a single number.
2. Is the interaction in the *representation*, not just in the policy? Yes.
   ``AdditivePredictor`` sums per-feature evidence over the same key and
   cannot fit XOR: 0.5 in-distribution while the joint table reads 1.0.
"""

import unittest

from agent import Agent
from evals.context_channel import (EVAL_CODES, TRAIN_CODES, _FrozenPredictor,
                                   _run_pinned, measure_choice_generalization)
from planner.plan import LearnedPlanner
from self_model.online import AdditivePredictor, OnlinePredictor
from worlds.dual import ChoiceDualWorld


def _blind_baseline(codes):
    """Accuracy of the deterministic tie-break on a pool of latent codes."""
    return sum(1 for a, b in codes if (a ^ b) == 0) / len(codes)


class TestPinnedLatents(unittest.TestCase):
    def test_a_pinned_world_rebuilds_the_same_latents_on_reset(self):
        world = ChoiceDualWorld(0, latents=[(2, 1), (3, 3)])
        first = world.latents
        world.reset()
        self.assertEqual(world.latents, first)
        self.assertEqual(world.reset()["context"], [2.0, 1.0])

    def test_pinned_latents_are_validated(self):
        with self.assertRaises(ValueError):
            ChoiceDualWorld(0, latents=[])
        with self.assertRaises(ValueError):
            ChoiceDualWorld(0, latents=[(1, 2, 3)])
        with self.assertRaises(TypeError):
            ChoiceDualWorld("0")


class TestFrozenPredictor(unittest.TestCase):
    def test_observe_is_a_no_op_but_predictions_survive(self):
        inner = OnlinePredictor()
        inner.observe(("T5_choice", "left", 0), True)
        frozen = _FrozenPredictor(inner)
        before = frozen.predict(("T5_choice", "left", 0))
        frozen.observe(("T5_choice", "left", 0), False)
        self.assertEqual(frozen.predict(("T5_choice", "left", 0)), before)
        self.assertEqual(frozen.seen(("T5_choice", "left", 0)), 1)


class TestBackoff(unittest.TestCase):
    def test_backoff_reads_the_marginal_for_an_unseen_context(self):
        predictor = OnlinePredictor()
        predictor.observe(("T5_choice", "right", 0), True)
        predictor.observe(("T5_choice", "right", 0), True)
        planner = LearnedPlanner(backoff=True)
        planner.bind_predictor(predictor)
        state = {"x": 0, "y": 0, "task": "T5_choice",
                 "target": [0, 0], "context": [2, 2]}
        scores = planner.scores(state)
        self.assertGreater(scores["right"], scores["left"])

    def test_without_backoff_an_unseen_context_is_the_prior(self):
        predictor = OnlinePredictor()
        predictor.observe(("T5_choice", "right", 0), True)
        planner = LearnedPlanner()
        planner.bind_predictor(predictor)
        state = {"x": 0, "y": 0, "task": "T5_choice",
                 "target": [0, 0], "context": [2, 2]}
        self.assertEqual(planner.scores(state), {"left": 0.5, "right": 0.5})


class TestGeneralization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.joint = measure_choice_generalization(train_episodes=10,
                                                 eval_episodes=8)
        cls.backoff = measure_choice_generalization(train_episodes=10,
                                                   eval_episodes=8,
                                                   backoff=True)
        cls.additive = measure_choice_generalization(train_episodes=10,
                                                    eval_episodes=8,
                                                    predictor="additive")

    def test_the_joint_table_memorises_the_training_contexts(self):
        self.assertGreater(self.joint["train_accuracy"], 0.9)
        self.assertGreater(self.joint["in_distribution_accuracy"], 0.9)

    def test_the_joint_table_does_not_generalise_to_unseen_contexts(self):
        self.assertLess(self.joint["zero_shot_accuracy"], 0.35)
        self.assertAlmostEqual(self.joint["zero_shot_accuracy"],
                               _blind_baseline(EVAL_CODES))

    def test_one_exposure_per_context_closes_the_gap(self):
        self.assertLess(self.joint["first_exposure_accuracy"], 0.35)
        self.assertGreater(self.joint["adapted_accuracy"], 0.9)

    def test_the_backoff_changes_no_number(self):
        for field in ("train_accuracy", "in_distribution_accuracy",
                      "zero_shot_accuracy", "first_exposure_accuracy",
                      "adapted_accuracy"):
            self.assertEqual(self.joint[field], self.backoff[field], field)

    def test_the_additive_model_cannot_represent_the_interaction(self):
        self.assertLess(self.additive["in_distribution_accuracy"], 0.65)
        self.assertGreater(self.joint["in_distribution_accuracy"]
                           - self.additive["in_distribution_accuracy"], 0.3)

    def test_the_additive_model_does_not_gain_from_the_context(self):
        self.assertLess(self.additive["adapted_accuracy"], 0.65)


class TestPredictorSwap(unittest.TestCase):
    def test_use_predictor_installs_and_returns_the_previous(self):
        agent = Agent(planner=LearnedPlanner(), world=ChoiceDualWorld(0),
                      learn_context=True)
        original = agent.online_predictor()
        replacement = AdditivePredictor()
        previous = agent.use_predictor(replacement)
        self.assertIs(previous, original)
        self.assertIs(agent.online_predictor(), replacement)
        self.assertEqual(agent.planner.scores({"x": 0, "y": 0,
                                               "task": "T5_choice",
                                               "target": [0, 0],
                                               "context": [1, 0]}),
                         {"left": 0.5, "right": 0.5})

    def test_a_swapped_predictor_persists_no_frozen_learning(self):
        agent = Agent(planner=LearnedPlanner(), world=ChoiceDualWorld(0),
                      learn_context=True)
        agent.run(max_steps=1)
        frozen = _FrozenPredictor(agent.online_predictor())
        agent.use_predictor(frozen)
        before = dict(agent.online_predictions())
        agent.run(max_steps=1)
        self.assertEqual(agent.online_predictions(), before)


class TestCodePools(unittest.TestCase):
    def test_no_eval_pair_was_seen_in_training(self):
        self.assertFalse(set(TRAIN_CODES) & set(EVAL_CODES))

    def test_the_unseenness_is_joint_not_marginal(self):
        # Value-level evidence for an additive model is available on both
        # sides; only the pair is new. That is what makes XOR the test.
        train_values = {value for pair in TRAIN_CODES for value in pair}
        eval_values = {value for pair in EVAL_CODES for value in pair}
        self.assertEqual(train_values, {0, 1})
        self.assertTrue(train_values & eval_values)
        self.assertIn(2, eval_values)


if __name__ == "__main__":
    unittest.main()
