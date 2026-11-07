"""Hidden-goal recovery: planner recalls missing goals from episode memory.

Failing-first harness: Planner reads target/items/cue/obstacles only
from the current state, so transient state dropout (target stripped
at plan-time, memories intact) truncates runs that episode memory
could have saved.
"""

import unittest

from agent import Agent, Planner
from models.backend import ModelBackend


def _hidden_steps(task, seed, strip, blind=False, max_steps=200):
    from worlds.grid import GridWorld
    world = GridWorld(task, seed)
    base = Planner()
    orig = base.plan

    def _stripped(self, state, memories=None):
        s = dict(state)
        for k in strip:
            s.pop(k, None)
        mems = [] if blind else memories
        return orig(s, mems)

    planner = Planner()
    import types
    planner.plan = types.MethodType(_stripped, planner)
    agent = Agent(planner=planner, world=world)
    return agent.run(max_steps=max_steps)


class _Capture(ModelBackend):
    def __init__(self):
        self.seen = []

    def generate(self, observation):
        self.seen.append(dict(observation))
        return "north"


def _hidden_obs(task, seed, strip, upto=3):
    from worlds.grid import GridWorld
    world = GridWorld(task, seed)
    state = world.reset()
    cap = _Capture()
    planner = Planner(backend=cap)
    # advance a few steps with full states so memories hold the goal,
    # then issue one hidden-state plan and capture its obs
    agent = Agent(planner=planner, world=world)
    agent._reset_episode()
    cur = state
    for _ in range(upto):
        agent.memory.save(cur)
        mems = agent.memory.recall()
        s = dict(cur)
        for k in strip:
            s.pop(k, None)
        if _ == upto - 1:
            planner.plan(s, mems)
        else:
            Planner().plan(s, mems)
        nxt, _, done = world.step(Planner().plan(cur, mems))
        cur = nxt
        if done:
            break
    return cap.seen[0] if cap.seen else {}


class TestHiddenGoal(unittest.TestCase):
    def test_hidden_target_recovered(self):
        trace = _hidden_steps("T3_navigate", 15, ["target"])
        self.assertTrue(trace[-1]["done"])
        self.assertEqual(sum(r["reward"] for r in trace), 1.0)
        self.assertEqual(len(trace), 13)

    def test_hidden_items_recovered(self):
        trace = _hidden_steps("T1_forage", 71, ["items_positions"])
        self.assertTrue(trace[-1]["done"])
        self.assertEqual(sum(r["reward"] for r in trace), 3.0)
        self.assertEqual(len(trace), 16)

    def test_memory_lesion_kills_hidden_recovery(self):
        intact = _hidden_steps("T3_navigate", 15, ["target"], blind=False)
        blind = _hidden_steps("T3_navigate", 15, ["target"], blind=True)
        self.assertEqual(len(intact), 13)
        self.assertEqual(len(blind), 200)
        self.assertEqual(sum(r["reward"] for r in blind), 0.0)


if __name__ == "__main__":
    unittest.main()
