"""Layout fingerprints: distinct worlds sharing (task, seed) must not collide.

Recovery keyed only by (task, seed) lets a complete layout from one
custom world block a different world's layout, so a warmed world cannot
persist and its cold run recovers the wrong goal. A deterministic
geometry fingerprint closes the collision: a different world replaces a
stale complete row, and a mismatched row is never recalled. The ablation
(blind fingerprint) restores the collision.
"""

import os
import tempfile
import unittest
from unittest import mock

import agent
from agent import Agent
from memory.store import MemoryStore
from worlds.grid import GridWorld


class _World(GridWorld):
    """T3 world with forced geometry, optionally hiding goal fields."""

    def __init__(self, target, obstacles, hidden):
        self._forced_target = [int(target[0]), int(target[1])]
        self._forced_obstacles = [[int(o[0]), int(o[1])] for o in obstacles]
        self._hidden = bool(hidden)
        super().__init__("T3_navigate", 0)

    def _build_layout(self, rng):
        self._target = list(self._forced_target)
        self._obstacles = [list(o) for o in self._forced_obstacles]
        self._initial_items = []
        self._remaining = []
        self._cue = 0

    def _state(self):
        state = super()._state()
        if self._hidden:
            state.pop("target", None)
            state.pop("obstacles", None)
        return state


def _run(store, target, obstacles, hidden, max_steps=200):
    world = _World(target, obstacles, hidden)
    return Agent(memory_store=store, world=world).run(max_steps=max_steps)


class TestLayoutFingerprint(unittest.TestCase):
    def test_distinct_worlds_same_key_do_not_collide(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = MemoryStore(os.path.join(tmp, "mem.db"))
            try:
                first = _run(store, (6, 7), [(6, 1)], hidden=False)
                self.assertEqual(len(first), 13)
                self.assertEqual(sum(r["reward"] for r in first), 1.0)
                second = _run(store, (3, 3), [(3, 2)], hidden=False)
                self.assertEqual(len(second), 6)
                cold = _run(store, (3, 3), [(3, 2)], hidden=True)
                self.assertEqual(len(cold), 6)
                self.assertEqual(sum(r["reward"] for r in cold), 1.0)
            finally:
                store.close()

    def test_builtin_fingerprint_stable_across_reset(self):
        world = GridWorld("T3_navigate", 15)
        world.reset()
        first = world.layout_fingerprint()
        world.reset()
        self.assertEqual(first, world.layout_fingerprint())
        other = GridWorld("T3_navigate", 65)
        other.reset()
        self.assertNotEqual(first, other.layout_fingerprint())

    def test_blind_fingerprint_ablation_restores_collision(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = MemoryStore(os.path.join(tmp, "mem.db"))
            try:
                with mock.patch.object(agent, "world_fingerprint",
                                       return_value=None):
                    _run(store, (6, 7), [(6, 1)], hidden=False)
                    _run(store, (3, 3), [(3, 2)], hidden=False)
                    cold = _run(store, (3, 3), [(3, 2)], hidden=True)
                self.assertEqual(len(cold), 200)
                self.assertEqual(sum(r["reward"] for r in cold), 0.0)
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
