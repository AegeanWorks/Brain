"""The dual world carries two independent latents and rewards their XOR."""

import unittest

from worlds.dual import DualWorld, NoiseDualWorld, PHASES


class TestDualWorld(unittest.TestCase):
    def test_latents_are_deterministic_and_reset_reproduces(self):
        first = DualWorld(7)
        second = DualWorld(7)
        self.assertEqual(first.latents, second.latents)
        before = first.latents
        first.reset()
        self.assertEqual(first.latents, before)
        self.assertNotEqual(DualWorld(7).latents, DualWorld(8).latents)

    def test_latents_are_independent(self):
        pairs = []
        for seed in range(200):
            pairs.extend(DualWorld(seed).latents)
        self.assertEqual(len(pairs), 200 * PHASES)
        self.assertEqual(set(pairs), {(0, 0), (0, 1), (1, 0), (1, 1)})
        counts = {cell: pairs.count(cell) for cell in ((0, 0), (0, 1), (1, 0), (1, 1))}
        for cell, count in counts.items():
            self.assertAlmostEqual(count / len(pairs), 0.25, delta=0.05)

    def test_reward_is_the_xor_of_the_pre_action_latents(self):
        world = DualWorld(3)
        state = world.reset()
        for index in range(PHASES):
            a, b = state["a"], state["b"]
            new_state, reward, done = world.step("wait")
            self.assertEqual(reward, float(a ^ b))
            self.assertEqual(done, index == PHASES - 1)
            state = new_state

    def test_context_is_the_current_latent_pair(self):
        world = DualWorld(11)
        state = world.reset()
        self.assertEqual(world.signal_context(state), [float(state["a"]), float(state["b"])])
        self.assertTrue(all(isinstance(value, float)
                            for value in world.signal_context(state)))

    def test_noise_world_reward_ignores_both_latents(self):
        rewards = []
        for seed in range(10):
            world = NoiseDualWorld(seed)
            world.reset()
            step_rewards = [world.step("wait")[1] for _ in range(PHASES)]
            rewards.append(step_rewards)
        self.assertEqual(rewards, [[0.0, 0.0, 1.0, 0.0]] * 10)


if __name__ == "__main__":
    unittest.main()
