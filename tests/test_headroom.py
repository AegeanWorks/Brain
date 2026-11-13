"""A task where the rule is beatable, and a plan that beats it.

ADR-192 measured no headroom on the shipped tasks, so nothing could improve
them. `DeadlineWorld` creates the missing case: the farthest item expires
exactly when a direct approach reaches it, so the rule's shortest-tour order
spends its early steps on patient items and loses it.

Measured over seeds 0-19 (see `evals.headroom`):

    rule                 3.00 items, 200.00 steps
    deadline plan        4.00 items,  30.35 steps
    optimum              4.00 items
    rule gap on 20 of 20 seeds

The deadline plan is replayed through the real backend seam, so this is the
first measured case of a non-rule policy winning on this substrate.
"""

import unittest

from agent import Agent, Planner
from evals.headroom import (DEFAULT_SEEDS, _manhattan, _moves_toward,
                            _plan_actions, deadline_actions, headroom,
                            optimal_collected, policy_collected, rule_collected)
from models.backend import StubBackend
from worlds.deadline import DeadlineWorld


class TestDeadlineWorld(unittest.TestCase):
    def test_the_layout_is_deterministic_and_seeded(self):
        first = DeadlineWorld(3)
        second = DeadlineWorld(3)
        self.assertEqual([item["cell"] for item in first.items],
                         [item["cell"] for item in second.items])
        self.assertNotEqual([item["cell"] for item in first.items],
                            [item["cell"] for item in DeadlineWorld(4).items])

    def test_the_farthest_item_is_the_urgent_one(self):
        for seed in DEFAULT_SEEDS:
            world = DeadlineWorld(seed)
            ordered = sorted(world.items,
                             key=lambda item: _manhattan((0, 0), item["cell"]))
            nearest, farthest = ordered[0], ordered[-1]
            self.assertLess(farthest["deadline"], nearest["deadline"], seed)
            # Urgent means: reachable only by heading there directly.
            self.assertEqual(farthest["deadline"],
                             _manhattan((0, 0), farthest["cell"]) + 1, seed)

    def test_collecting_before_the_deadline_rewards_one(self):
        world = DeadlineWorld(0)
        target = max(world.items, key=lambda item: item["deadline"])["cell"]
        world.x, world.y = target
        state, reward, done = world.step("collect")
        self.assertEqual(reward, 1.0)
        self.assertEqual(state["items"], 1)
        self.assertFalse(done)

    def test_an_expired_item_cannot_be_collected(self):
        world = DeadlineWorld(0)
        target = max(world.items, key=lambda item: item["deadline"])["cell"]
        world.steps = world.items[0]["deadline"] + 50
        world.x, world.y = target
        _state, reward, _done = world.step("collect")
        self.assertEqual(reward, 0.0)
        self.assertEqual(world.collected, 0)

    def test_expiry_removes_the_item_from_the_observation(self):
        world = DeadlineWorld(0)
        world.reset()
        before = len(world._state()["items_positions"])
        world.steps = 200
        world._expire()
        self.assertLess(len(world._state()["items_positions"]), before)

    def test_the_state_has_no_fixed_target_or_obstacles(self):
        state = DeadlineWorld(0).reset()
        self.assertNotIn("target", state)
        self.assertNotIn("obstacles", state)
        self.assertIn("items_positions", state)
        self.assertIn("deadlines", state)

    def test_movement_clamps_at_the_board_edge(self):
        world = DeadlineWorld(0)
        world.reset()
        world.step("up")
        self.assertEqual((world.x, world.y), (0, 0))
        world.step("left")
        self.assertEqual((world.x, world.y), (0, 0))

    def test_an_unknown_action_is_refused(self):
        with self.assertRaises(ValueError):
            DeadlineWorld(0).step("jump")

    def test_the_episode_ends_when_all_items_are_collected(self):
        world = DeadlineWorld(0)
        world.reset()
        for item in world.items:
            world.x, world.y = item["cell"]
            world.steps = 0
            _state, _reward, done = world.step("collect")
        self.assertTrue(done)
        self.assertEqual(world.collected, world.item_count)

    def test_the_fingerprint_survives_reset_and_tracks_the_seed(self):
        world = DeadlineWorld(1)
        first = world.layout_fingerprint()
        world.reset()
        self.assertEqual(world.layout_fingerprint(), first)
        self.assertNotEqual(world.layout_fingerprint(),
                            DeadlineWorld(2).layout_fingerprint())

    def test_a_bad_item_count_is_refused(self):
        for bad in (0, 1, "4"):
            with self.assertRaises((ValueError, TypeError)):
                DeadlineWorld(0, items=bad)


class TestPlanActions(unittest.TestCase):
    def test_moves_toward_walks_one_cell_at_a_time(self):
        actions = _moves_toward((0, 0), (2, 1))
        self.assertEqual(actions, ["right", "right", "down"])

    def test_moves_toward_handles_every_direction(self):
        self.assertEqual(_moves_toward((3, 3), (1, 2)), ["left", "left", "up"])

    def test_the_plan_reaches_every_cell_in_order(self):
        actions = _plan_actions([(1, 0), (1, 1)])
        world = DeadlineWorld(0)
        world.reset()
        for action in actions:
            world.step(action)
        self.assertEqual((world.x, world.y), (1, 1))

    def test_deadline_actions_start_with_the_urgent_item(self):
        for seed in DEFAULT_SEEDS:
            world = DeadlineWorld(seed)
            urgent = min(world.items, key=lambda item: item["deadline"])
            actions = deadline_actions(seed)
            first_collect = actions.index("collect")
            world.reset()
            for action in actions[:first_collect]:
                world.step(action)
            self.assertEqual((world.x, world.y), tuple(urgent["cell"]), seed)


class TestHeadroom(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = headroom()

    def test_the_rule_loses_an_item_on_every_seed(self):
        self.assertEqual(self.report["seeds_with_rule_gap"], self.report["seeds"])

    def test_the_deadline_plan_reaches_the_optimum_everywhere(self):
        self.assertTrue(self.report["policy_reaches_optimum"])

    def test_the_policy_beats_the_rule_on_average(self):
        self.assertGreater(self.report["policy_mean"],
                           self.report["rule_mean"] + 0.5)

    def test_the_optimum_is_every_item(self):
        self.assertEqual(self.report["optimal_mean"],
                         float(DeadlineWorld(0).item_count))

    def test_the_policy_is_also_far_shorter(self):
        self.assertLess(self.report["policy_steps_mean"],
                        self.report["rule_steps_mean"] / 3.0)

    def test_optimal_collected_caps_at_the_item_count(self):
        # Both reachable when deadlines are loose.
        items = [((0, 1), 20), ((1, 0), 20)]
        self.assertEqual(optimal_collected(items), 2)
        # Two urgent items cannot both be reached from the start in time.
        impossible = [((7, 7), 1), ((0, 7), 1)]
        self.assertEqual(optimal_collected(impossible), 0)

    def test_a_single_seed_agrees_with_the_batch(self):
        seed = DEFAULT_SEEDS[0]
        self.assertEqual(rule_collected(seed)["collected"],
                         self.report["rows"][0]["rule"])
        self.assertEqual(policy_collected(seed)["collected"],
                         self.report["rows"][0]["policy"])

    def test_the_replayed_plan_is_accepted_by_the_seam(self):
        result = policy_collected(DEFAULT_SEEDS[0])
        self.assertGreater(result["accepted"], 0)
        self.assertEqual(result["rejected"], 0)


class TestTheRuleItself(unittest.TestCase):
    def test_the_rule_run_is_deterministic(self):
        first = [step["action"] for step in
                 Agent(world=DeadlineWorld(2)).run(max_steps=200)]
        second = [step["action"] for step in
                  Agent(world=DeadlineWorld(2)).run(max_steps=200)]
        self.assertEqual(first, second)

    def test_the_deadline_plan_wins_through_the_real_seam(self):
        seed = DEFAULT_SEEDS[0]
        planner = Planner(backend=StubBackend(script=deadline_actions(seed)),
                          noop_guard=False, progress_guard=False)
        trace = Agent(planner=planner, world=DeadlineWorld(seed)).run(max_steps=200)
        won = sum(float(step.get("reward", 0.0)) for step in trace)
        self.assertGreater(won, rule_collected(seed)["collected"])


if __name__ == "__main__":
    unittest.main()
