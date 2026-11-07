"""Model-seam visit coverage: backend sees loop-avoidance memory.

Failing-first harness: Planner computes visits from recent episode
memory for tie-breaks but omits it from backend obs, so obs-limited
policies cycle on tie-trap seeds (T3 seed 74: rule 9 vs obs-only 200).
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
        return "north"


def _obs_for(state, memories):
    cap = _Capture()
    Planner(backend=cap).plan(dict(state), list(memories))
    return cap.seen[0]


def _visits_from_obs(obs):
    raw = obs.get("visits", [])
    out = {}
    for entry in raw:
        x, y, c = entry
        out[(int(x), int(y))] = int(c)
    return out


def _oracle_action(obs):
    x, y = obs["x"], obs["y"]
    pos = [x, y]
    obstacles = list(obs.get("obstacles", []))
    visits = _visits_from_obs(obs)
    if obs.get("items_positions"):
        cells = [list(c) for c in obs["items_positions"]]
        if pos in cells:
            return "collect"
        goal = _first_of_best_tour(pos, cells)
        return _step_toward(pos, goal, obstacles, visits)
    target = obs.get("target")
    if target is not None:
        target = list(target)
        if pos == target:
            if obs.get("task") == "T2_delayed_match" and obs.get("steps", 0) < 2:
                return "wait"
            return "collect"
        return _step_toward(pos, target, obstacles, visits)
    return "wait"


class _VisitOracle(ModelBackend):
    def generate(self, observation):
        return _oracle_action(dict(observation))


def _oracle_steps(task, seed, max_steps=200):
    from worlds.grid import GridWorld
    world = GridWorld(task, seed)
    planner = Planner(backend=_VisitOracle())
    agent = Agent(planner=planner, world=world)
    return agent.run(max_steps=max_steps)


class TestObsVisits(unittest.TestCase):
    def test_planner_obs_carries_visits(self):
        state = {"task": "T3_navigate", "x": 5, "y": 0, "steps": 4,
                 "target": [6, 7], "obstacles": [[6, 1]]}
        memories = [{"x": 5, "y": 0}, {"x": 5, "y": 0}, {"x": 4, "y": 0}]
        obs = _obs_for(state, memories)
        self.assertIn("visits", obs)
        visits = {tuple(e[:2]): e[2] for e in obs["visits"]}
        self.assertEqual(visits.get((5, 0)), 2)
        self.assertEqual(visits.get((4, 0)), 1)

    def test_build_prompt_mentions_visits(self):
        obs = {"task": "T3_navigate", "x": 5, "y": 0, "steps": 4,
               "legal": ["up", "down", "left", "right", "collect", "wait"],
               "target": [6, 7], "obstacles": [[6, 1]],
               "visits": [[[5, 0, 2]], [[4, 0, 1]]][0]}
        # visits encoding is a sorted list of [x, y, count]
        obs["visits"] = [[4, 0, 1], [5, 0, 2]]
        text = build_prompt(obs)
        self.assertIn("Visits", text)
        self.assertIn("[5, 0]", text)

    def test_visit_oracle_matches_rule_on_tie_trap(self):
        expected = {("T3_navigate", 74): 9, ("T3_navigate", 15): 13,
                    ("T3_navigate", 65): 6, ("T1_forage", 71): 16,
                    ("T2_delayed_match", 3): 8}
        for (task, seed), want in expected.items():
            trace = _oracle_steps(task, seed)
            self.assertTrue(trace[-1]["done"], "%s:%d not done" % (task, seed))
            self.assertEqual(len(trace), want, "%s:%d steps" % (task, seed))


if __name__ == "__main__":
    unittest.main()
