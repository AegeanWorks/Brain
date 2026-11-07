"""Exhaustive T3 coverage: every (target, obstacle) config optimal.

Transferred idea: Lattice evidence matrix + coverage gaps. T3 layouts
are exactly one target plus one obstacle on 63 free cells (3906
ordered pairs). Seeds sample this space; this battery enumerates it:
every config must equal BFS-optimal, with the grand total pinned.
No seed can hide a trap anymore.
"""

import unittest
from collections import deque

from agent import Agent, Planner
from worlds.grid import GridWorld


def _bfs_optimal(target, obstacle):
    start = (0, 0)
    queue = deque([(start, 0)])
    seen = {start}
    while queue:
        (x, y), dist = queue.popleft()
        if (x, y) == target:
            return dist
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if (0 <= nx < 8 and 0 <= ny < 8 and (nx, ny) != obstacle
                    and (nx, ny) not in seen):
                seen.add((nx, ny))
                queue.append(((nx, ny), dist + 1))
    raise AssertionError("unreachable target %r obstacle %r" % (target, obstacle))


class _ForcedLayoutWorld(GridWorld):
    """GridWorld with a fixed T3 layout, built through the class hook.

    Overrides _build_layout so no test reaches into another object's
    privates; the constructor and reset() paths stay untouched.
    """

    def __init__(self, target, obstacle):
        self._forced_target = [int(target[0]), int(target[1])]
        self._forced_obstacle = [int(obstacle[0]), int(obstacle[1])]
        super().__init__("T3_navigate", 0)

    def _build_layout(self, rng):
        self._target = list(self._forced_target)
        self._obstacles = [list(self._forced_obstacle)]
        self._initial_items = []
        self._remaining = []
        self._cue = 0


def _run_config(target, obstacle, max_steps=200):
    world = _ForcedLayoutWorld(target, obstacle)
    agent = Agent(planner=Planner(), world=world)
    agent._reset_episode()
    state = {"x": 0, "y": 0, "energy": 200, "items": 0, "steps": 0,
             "task": "T3_navigate", "target": [target[0], target[1]],
             "obstacles": [[obstacle[0], obstacle[1]]]}
    trace = []
    current = dict(state)
    for _ in range(int(max_steps)):
        agent.memory.save(current)
        memories = agent.memory.recall(limit=None)
        action = agent.planner.plan(current, memories)
        new_state, reward, done = world.step(action)
        trace.append({"action": action, "reward": reward, "done": done})
        current = new_state
        if done:
            break
    return trace


class TestExhaustiveT3(unittest.TestCase):
    def test_all_3906_configs_optimal(self):
        cells = [(x, y) for y in range(8) for x in range(8)
                 if (x, y) != (0, 0)]
        total = 0
        checked = 0
        for target in cells:
            for obstacle in cells:
                if obstacle == target:
                    continue
                trace = _run_config(target, obstacle)
                self.assertTrue(trace[-1]["done"], "%r %r" % (target, obstacle))
                self.assertEqual(sum(r["reward"] for r in trace), 1.0)
                want = _bfs_optimal(target, obstacle)
                self.assertEqual(len(trace), want, "%r %r" % (target, obstacle))
                total += len(trace)
                checked += 1
        self.assertEqual(checked, 3906)
        self.assertEqual(total, 27860)


if __name__ == "__main__":
    unittest.main()
