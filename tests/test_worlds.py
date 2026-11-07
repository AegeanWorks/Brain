"""World determinism and viability checks."""

import json
import os
import tempfile
import unittest

from worlds.grid import ACTIONS, MAX_STEPS, GridWorld, stable_hash, viability


class TestDeterminism(unittest.TestCase):
    def test_same_seed_same_hash(self):
        for task in ("T1_forage", "T2_delayed_match", "T3_navigate"):
            a = GridWorld(task, 7)
            b = GridWorld(task, 7)
            sa, sb = a.reset(), b.reset()
            self.assertEqual(stable_hash(sa), stable_hash(sb))
            seq = ["right", "down", "collect", "wait", "left", "up"]
            for act in seq:
                ra = a.step(act)
                rb = b.step(act)
                self.assertEqual(stable_hash(ra[0]), stable_hash(rb[0]))
                self.assertEqual(ra[1], rb[1])
                self.assertEqual(ra[2], rb[2])

    def test_reset_reproducible(self):
        w = GridWorld("T1_forage", 3)
        first = stable_hash(w.reset())
        for _ in range(5):
            w.step("wait")
        self.assertEqual(stable_hash(w.reset()), first)

    def test_seed_sensitivity(self):
        hashes = set()
        for seed in range(20):
            w = GridWorld("T1_forage", seed)
            hashes.add(stable_hash(w.reset()))
            # each seed reproduces its own layout
            again = GridWorld("T1_forage", seed)
            self.assertEqual(stable_hash(again.reset()), stable_hash(w.reset()))
        self.assertGreater(len(hashes), 1)

    def test_base_state_keys_and_actions(self):
        w = GridWorld("T1_forage", 0)
        s = w.reset()
        for key in ("x", "y", "energy", "items", "steps"):
            self.assertIn(key, s)
        self.assertTrue(viability(s))
        self.assertTrue(w.is_viable())
        for act in ACTIONS:
            w2 = GridWorld("T2_delayed_match", 1)
            w2.reset()
            state, reward, done = w2.step(act)
            self.assertIn("steps", state)
            self.assertIsInstance(reward, float)
            self.assertIsInstance(done, bool)
        with self.assertRaises(ValueError):
            w.step("fly")

    def test_viability_bounds(self):
        w = GridWorld("T3_navigate", 0)
        w.reset()
        done = False
        for _ in range(MAX_STEPS + 5):
            _, _, done = w.step("wait")
            if done:
                break
        self.assertTrue(done)
        self.assertFalse(w.is_viable())

    def test_tempdir_hash_log(self):
        w = GridWorld("T1_forage", 11)
        lines = [stable_hash(w.reset())]
        for act in ("right", "collect", "wait"):
            state, _, _ = w.step(act)
            lines.append(stable_hash(state))
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "hashes.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(lines, fh)
            with open(path, encoding="utf-8") as fh:
                back = json.load(fh)
        self.assertEqual(lines, back)


if __name__ == "__main__":
    unittest.main()
