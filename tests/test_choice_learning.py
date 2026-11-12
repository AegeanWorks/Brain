"""Learning to act on an interaction, not only to predict it.

ADR-183 planted an interaction and showed the pair scan recovers it. That is
a measurement result: the agent still acted with a fixed rule. ``T5_choice``
makes the interaction actionable — the rewarded action is the XOR of two
independent latents — so the only way to beat the 0.5 base rate is to learn
the mapping from observed context and action to reward, then act on it.

Measured over 40 episodes x 4 phases with one persistent online table:

    blind (shipped feature key)   first half 0.3875   last half 0.4875
    learned (context in the key)  first half 0.9750   last half 1.0000

These tests pin the policy, the prequential key plumbing, and the ablation.
"""

import unittest

from agent import Agent
from evals.context_channel import measure_choice
from planner.plan import LearnedPlanner
from self_model.online import OnlinePredictor, context_feature_key, feature_key
from worlds.dual import PHASES, ChoiceDualWorld

STATE = {"x": 0, "y": 0, "task": "T5_choice", "target": [0, 0], "context": [1, 0]}


class TestChoiceWorld(unittest.TestCase):
    def test_the_correct_action_is_the_xor_of_the_latents(self):
        for seed in range(20):
            world = ChoiceDualWorld(seed)
            state = world.reset()
            for _ in range(PHASES):
                a, b = state["a"], state["b"]
                expected = "right" if a ^ b else "left"
                self.assertEqual(world.correct_action(), expected)
                state, _reward, _done = world.step(expected)

    def test_a_wrong_action_scores_zero_and_the_right_one_scores_one(self):
        world = ChoiceDualWorld(0)
        state = world.reset()
        wrong = "left" if world.correct_action() == "right" else "right"
        _state, reward, _done = world.step(wrong)
        self.assertEqual(reward, 0.0)
        world.reset()
        _state, reward, _done = world.step(world.correct_action())
        self.assertEqual(reward, 1.0)

    def test_context_is_the_pre_action_latent_pair(self):
        world = ChoiceDualWorld(5)
        state = world.reset()
        for index in range(PHASES):
            self.assertEqual(state["context"],
                             [float(world.latents[index][0]),
                              float(world.latents[index][1])])
            state, _reward, _done = world.step("left")


class TestContextKey(unittest.TestCase):
    def test_no_context_returns_the_shipped_key(self):
        self.assertEqual(context_feature_key("T5_choice", STATE, "left", None),
                         feature_key("T5_choice", STATE, "left"))

    def test_context_appends_a_float_tuple(self):
        key = context_feature_key("T5_choice", STATE, "left", [1, 0])
        self.assertEqual(key, feature_key("T5_choice", STATE, "left") + ((1.0, 0.0),))

    def test_unreadable_context_falls_back_to_the_plain_key(self):
        self.assertEqual(context_feature_key("T5_choice", STATE, "left", ["x"]),
                         feature_key("T5_choice", STATE, "left"))

    def test_learn_context_defaults_off_and_validates(self):
        agent = Agent(world=ChoiceDualWorld(0))
        self.assertFalse(agent._learn_context)
        with self.assertRaises(ValueError):
            Agent(world=ChoiceDualWorld(0), learn_context="yes")


class TestLearnedPolicy(unittest.TestCase):
    def test_no_predictor_is_a_deterministic_prior(self):
        planner = LearnedPlanner()
        self.assertEqual(planner.plan(STATE, []), "left")
        self.assertEqual(planner.scores(STATE), {"left": 0.5, "right": 0.5})

    def test_agent_binds_the_predictor_to_the_planner(self):
        planner = LearnedPlanner()
        Agent(planner=planner, world=ChoiceDualWorld(0))
        self.assertIsInstance(planner._predictor, OnlinePredictor)

    def test_the_learned_policy_beats_the_blind_policy(self):
        learned = measure_choice(use_context=True, episodes=10)
        blind = measure_choice(use_context=False, episodes=10)
        self.assertGreaterEqual(learned["last_half_accuracy"], 0.9)
        self.assertLessEqual(blind["last_half_accuracy"], 0.65)
        self.assertGreater(learned["last_half_accuracy"],
                           blind["last_half_accuracy"] + 0.2)

    def test_learning_keys_carry_context_only_when_enabled(self):
        aware = Agent(planner=LearnedPlanner(), world=ChoiceDualWorld(0),
                      learn_context=True)
        aware.run(max_steps=PHASES)
        self.assertTrue(all(len(key) == 4 for key in aware.online_predictions()))

        plain = Agent(planner=LearnedPlanner(), world=ChoiceDualWorld(0))
        plain.run(max_steps=PHASES)
        self.assertTrue(all(len(key) == 3 for key in plain.online_predictions()))

    def test_default_agent_pins_are_unchanged(self):
        # A world without the context field keeps the shipped three-part key.
        plain = Agent(planner=LearnedPlanner(), world=ChoiceDualWorld(0))
        plain.run(max_steps=PHASES)
        for key in plain.online_predictions():
            self.assertEqual(len(key), 3)


if __name__ == "__main__":
    unittest.main()
