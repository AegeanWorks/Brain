"""Model-seam observation coverage: backend sees the goal state.

Failing-first harness for the impoverished-obs gap: Planner.plan builds
obs with only task/x/y/steps/legal, and build_prompt renders only those,
so two states with different goals collide to identical obs/prompt and an
obs-constrained policy cannot steer.
"""

import unittest

from agent import Agent, Planner, _first_of_best_tour, _step_toward
from models.backend import ModelBackend
from models.llamacpp import build_prompt


class _Capture(ModelBackend):
    def __init__(self):
        self.seen = []

    def generate(self, observation):
        self.seen.append(dict(observation))
        return "north"  # invalid -> rule fallback carries the run


def _obs_for(state):
    cap = _Capture()
    Planner(backend=cap).plan(dict(state), [])
    return cap.seen[0]


def _oracle_action(obs):
    """Obs-only policy: same geometry helpers, no episode memory."""
    x, y = obs["x"], obs["y"]
    pos = [x, y]
    obstacles = list(obs.get("obstacles", []))
    if obs.get("items_positions"):
        cells = [list(c) for c in obs["items_positions"]]
        if pos in cells:
            return "collect"
        goal = _first_of_best_tour(pos, cells)
        return _step_toward(pos, goal, obstacles, {})
    target = obs.get("target")
    if target is not None:
        target = list(target)
        if pos == target:
            if obs.get("task") == "T2_delayed_match" and obs.get("steps", 0) < 2:
                return "wait"
            return "collect"
        return _step_toward(pos, target, obstacles, {})
    return "wait"


class _ObsOracle(ModelBackend):
    def generate(self, observation):
        return _oracle_action(dict(observation))


def _oracle_steps(task, seed, max_steps=200):
    from worlds.grid import GridWorld
    world = GridWorld(task, seed)
    planner = Planner(backend=_ObsOracle())
    agent = Agent(planner=planner, world=world)
    return agent.run(max_steps=max_steps)


class TestObsCoverage(unittest.TestCase):
    def test_planner_obs_carries_goal_state(self):
        t3 = {"task": "T3_navigate", "x": 5, "y": 0, "steps": 7,
              "target": [6, 7], "obstacles": [[6, 1]]}
        obs = _obs_for(t3)
        self.assertEqual(obs.get("target"), [6, 7])
        self.assertEqual(obs.get("obstacles"), [[6, 1]])
        t1 = {"task": "T1_forage", "x": 0, "y": 0, "steps": 0,
              "items_positions": [[1, 2], [3, 4], [5, 6]]}
        obs1 = _obs_for(t1)
        self.assertEqual(obs1.get("items_positions"), [[1, 2], [3, 4], [5, 6]])
        t2 = {"task": "T2_delayed_match", "x": 0, "y": 0, "steps": 0,
              "cue": 1, "target": [7, 0]}
        obs2 = _obs_for(t2)
        self.assertEqual(obs2.get("cue"), 1)
        self.assertEqual(obs2.get("target"), [7, 0])

    def test_build_prompt_mentions_goal_state(self):
        obs = {"task": "T3_navigate", "x": 5, "y": 0, "steps": 7,
               "legal": ["up", "down", "left", "right", "collect", "wait"],
               "target": [6, 7], "obstacles": [[6, 1]]}
        text = build_prompt(obs)
        self.assertIn("[6, 7]", text)
        self.assertIn("[6, 1]", text)
        obs1 = {"task": "T1_forage", "x": 0, "y": 0, "steps": 0,
                "legal": ["up", "down", "left", "right", "collect", "wait"],
                "items_positions": [[1, 2], [3, 4]]}
        text1 = build_prompt(obs1)
        self.assertIn("[1, 2]", text1)

    def test_obs_oracle_matches_rule_on_steerable_seeds(self):
        expected = {("T1_forage", 71): 16, ("T2_delayed_match", 3): 8,
                    ("T3_navigate", 15): 13, ("T3_navigate", 65): 6}
        for (task, seed), want in expected.items():
            trace = _oracle_steps(task, seed)
            self.assertTrue(trace[-1]["done"], "%s:%d not done" % (task, seed))
            self.assertEqual(len(trace), want, "%s:%d steps" % (task, seed))


if __name__ == "__main__":
    unittest.main()
