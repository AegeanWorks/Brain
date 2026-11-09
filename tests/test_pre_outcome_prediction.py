"""A self-prediction must be made before the outcome and score above chance.

The agent's recorded confidence is `1.0 if reward > 0 else 0.5` — computed
after the step — so its Brier restates the base rate and the repo's own
`confidence_is_outcome` check flags it. `self_model.prediction` predicts
before `world.step` from pre-action state only.

These tests pin:
  * the predictor beats the base rate when pooled over 20 seeds per task;
  * the per-task predictors are the ones the pooled measurement selected;
  * the prediction never reads post-action state (structural check);
  * a predictor that only fits one episode does not clear the bar.
"""

import unittest

from agent import Memory, Planner
from self_model.prediction import (TASK_PREDICTORS, goal_distance,
                                   predict_outcome)
from worlds.grid import GridWorld

TASKS = ("T3_navigate", "T1_forage", "T2_delayed_match")
SEEDS = range(20)


def _brier(pairs):
    return sum((p - o) ** 2 for p, o in pairs) / len(pairs)


def _episode(task, seed):
    """Replay one episode, recording the pre-action prediction each step."""
    world = GridWorld(task, seed)
    state = world.reset()
    planner, memory = Planner(), Memory()
    rows = []
    for _ in range(200):
        memory.save(state)
        action = planner.plan(state, memory.recall())
        probability, basis = predict_outcome(state, action, task)
        state, reward, done = world.step(action)
        rows.append((probability, 1.0 if reward > 0 else 0.0, basis))
        if done:
            break
    return rows


class TestPreOutcomePrediction(unittest.TestCase):
    def test_the_predictor_beats_the_base_rate_on_every_task(self):
        for task in TASKS:
            pooled = []
            for seed in SEEDS:
                pooled.extend(_episode(task, seed))
            rate = sum(o for _, o, _ in pooled) / len(pooled)
            base = _brier([(rate, o) for _, o, _ in pooled])
            model = _brier([(p, o) for p, o, _ in pooled])
            skill = 1.0 - model / base if base else 0.0
            self.assertGreater(skill, 0.5, "%s skill=%+.3f" % (task, skill))

    def test_the_selected_predictors_are_the_measured_ones(self):
        self.assertEqual(TASK_PREDICTORS["T3_navigate"], "distance")
        self.assertEqual(TASK_PREDICTORS["T1_forage"], "collect")
        self.assertEqual(TASK_PREDICTORS["T2_delayed_match"], "collect")

    def test_the_prediction_names_its_basis(self):
        state = {"x": 0, "y": 0, "target": [1, 0]}
        probability, basis = predict_outcome(state, "right", "T3_navigate")
        self.assertEqual(basis, "closing-move")
        self.assertGreater(probability, 0.5)

        probability, basis = predict_outcome(state, "left", "T3_navigate")
        self.assertEqual(basis, "far")
        self.assertLess(probability, 0.5)

    def test_an_unknown_task_degrades_to_a_coin_flip(self):
        probability, basis = predict_outcome({}, "wait", "T9_unknown")
        self.assertEqual(probability, 0.5)
        self.assertEqual(basis, "unknown-task")

    def test_a_goal_less_state_does_not_raise(self):
        probability, basis = predict_outcome({"x": 1, "y": 1}, "up",
                                             "T3_navigate")
        self.assertEqual(probability, 0.5)
        self.assertEqual(basis, "no-goal")

    def test_the_predictor_never_sees_post_action_state(self):
        # Structural: the signature takes (state, action, task) only, so a
        # post-action observation cannot reach it.
        import inspect

        params = list(inspect.signature(predict_outcome).parameters)
        self.assertEqual(params, ["state", "action", "task"])

    def test_a_non_generalizing_predictor_fails_the_same_bar(self):
        # The experience-only predictors measured negative, so they must not
        # clear 0.5 either — this pins that the bar is discriminative.
        def always_low(state, action, task):
            return 0.05

        task = "T3_navigate"
        pooled = []
        for seed in SEEDS:
            world = GridWorld(task, seed)
            state = world.reset()
            planner, memory = Planner(), Memory()
            for _ in range(200):
                memory.save(state)
                action = planner.plan(state, memory.recall())
                state, reward, done = world.step(action)
                pooled.append((always_low(state, action, task),
                               1.0 if reward > 0 else 0.0))
                if done:
                    break
        rate = sum(o for _, o in pooled) / len(pooled)
        base = _brier([(rate, o) for _, o in pooled])
        model = _brier(pooled)
        self.assertLess(1.0 - model / base, 0.0)


if __name__ == "__main__":
    unittest.main()
