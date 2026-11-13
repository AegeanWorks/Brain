"""A bounded policy and a world must agree on the action alphabet.

`LearnedPlanner` chooses from a fixed action set (by default ``left`` and
``right``, the `T5_choice` alphabet). Pointed at a grid task it cannot emit
``up``/``down``/``collect``, so before this guard it spent all 200 steps and
scored 0.0 on every seed — a configuration error reported as a bad run.

    rule planner on T1_forage        16 steps, reward 1.0+  (works)
    LearnedPlanner on T1_forage      raised before step 1

The guard only fires when both sides declare an action set, so the rule
planner and custom worlds keep their behaviour.
"""

import unittest

from agent import Agent
from planner.plan import LearnedPlanner
from worlds.dual import ChoiceDualWorld
from worlds.grid import ACTIONS, GridWorld


class _NoDeclaredActions:
    """A world that accepts any action and declares no alphabet."""

    def __init__(self):
        self.steps = 0

    def reset(self):
        self.steps = 0
        return {"x": 0, "y": 0, "energy": 1, "items": 0, "steps": 0}

    def step(self, action):
        self.steps += 1
        return {"x": 0, "y": 0, "energy": 1, "items": 0, "steps": self.steps}, 0.0, self.steps >= 2


class _NarrowPlanner(LearnedPlanner):
    """Declares the full alphabet but only ever emits two actions.

    This is the shape of the original bug: a policy that claims an action
    set large enough for the world while actually proposing a narrower one.
    The coverage guard cannot see it, so the run burns the step cap.
    """

    def __init__(self, actions=ACTIONS):
        super().__init__(actions=actions)

    def plan(self, state, memories):
        return "left"


class TestWorldAlphabet(unittest.TestCase):
    def test_the_grid_world_declares_its_actions(self):
        self.assertEqual(GridWorld.ACTIONS, ACTIONS)
        self.assertEqual(set(ACTIONS), {"up", "down", "left", "right",
                                        "collect", "wait"})

    def test_the_choice_world_declares_two_actions(self):
        self.assertEqual(ChoiceDualWorld.ACTIONS, ("left", "right"))


class TestPlannerAlphabet(unittest.TestCase):
    def test_the_default_alphabet_is_left_and_right(self):
        self.assertEqual(LearnedPlanner().actions, ("left", "right"))

    def test_an_empty_alphabet_is_refused(self):
        with self.assertRaises(ValueError):
            LearnedPlanner(actions=[])

    def test_a_duplicate_action_is_refused(self):
        with self.assertRaises(ValueError):
            LearnedPlanner(actions=["left", "left"])
        with self.assertRaises(ValueError):
            LearnedPlanner(actions=["up", "down", "up"])

    def test_coverage_is_reported_not_guessed(self):
        planner = LearnedPlanner(actions=("left", "right", "wait"))
        self.assertTrue(planner.covers(("left", "wait")))
        self.assertFalse(planner.covers(("left", "collect")))
        self.assertTrue(planner.covers(()))


class TestAgentCoverageGuard(unittest.TestCase):
    def test_a_mismatched_policy_raises_before_the_first_step(self):
        agent = Agent(planner=LearnedPlanner())
        with self.assertRaises(ValueError) as caught:
            agent.run_task("T1_forage", 0)
        message = str(caught.exception)
        self.assertIn("LearnedPlanner", message)
        self.assertIn("T1_forage", message)
        self.assertIn("up", message)
        self.assertIn("Why:", message)
        self.assertIn("Fix:", message)

    def test_the_error_is_raised_for_every_grid_task(self):
        for task in ("T1_forage", "T2_delayed_match", "T3_navigate"):
            with self.assertRaises(ValueError, msg=task):
                Agent(planner=LearnedPlanner()).run_task(task, 0)

    def test_a_policy_that_covers_the_world_runs(self):
        agent = Agent(planner=LearnedPlanner(actions=ACTIONS),
                      world=GridWorld("T3_navigate", 0))
        trace = agent.run(max_steps=5)
        self.assertEqual(len(trace), 5)

    def test_the_choice_world_is_unaffected(self):
        agent = Agent(planner=LearnedPlanner(), world=ChoiceDualWorld(0))
        self.assertEqual(len(agent.run(max_steps=4)), 4)

    def test_the_rule_planner_is_unaffected(self):
        self.assertEqual(len(Agent().run_task("T1_forage", 0)), 16)

    def test_a_world_without_a_declared_alphabet_is_unaffected(self):
        agent = Agent(planner=LearnedPlanner(), world=_NoDeclaredActions())
        self.assertEqual(len(agent.run(max_steps=2)), 2)

    def test_a_zero_reward_baseline_confirms_the_old_failure_mode(self):
        # The reason the guard exists. This policy *declares* the full
        # alphabet, so the coverage check passes, but it only ever emits
        # left — the shape of the old silent failure. It burns the cap.
        agent = Agent(planner=_NarrowPlanner(), world=GridWorld("T1_forage", 0))
        trace = agent.run(max_steps=40)
        reward = sum(float(step.get("reward", 0.0)) for step in trace)
        self.assertEqual(len(trace), 40)
        self.assertEqual(reward, 0.0)


if __name__ == "__main__":
    unittest.main()
