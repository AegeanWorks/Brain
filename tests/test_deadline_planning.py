"""Failing-first harness: the planner should schedule items by deadline.

Cycle 199 closed with a boundary: a scalar weight fitted to the 4-item
deadline world does not carry to 5 or 6 items.  The per-item rule that does
carry is a schedule: choose the first item of the visit order that collects
the most items before their deadlines, then finishes soonest.

This module pins the integration, not just the helper:

* the shipped planner collects every item on the 4-item family;
* ``deadline_ordering=False`` restores the shortest-tour loss (3/200);
* the schedule generalises to 5 and 6 items where the scalar does not;
* the model observation and prompt carry the deadlines;
* standing T1/T2/T3 behavior is byte-identical.
"""

import unittest

from agent import (PLANNER_POLICY, Agent, Planner, _first_of_deadline_tour,
                   policy_digest)
from models.llamacpp import build_prompt
from worlds.deadline import DeadlineWorld


class CaptureBackend:
    """Record the observation and always propose a legal no-op."""

    def __init__(self):
        self.observations = []

    def generate(self, observation):
        self.observations.append(observation)
        return "wait"

    def identity(self):
        return "capture:deadline"


def _collected(trace):
    return sum(float(step.get("reward", 0.0)) for step in trace)


def _run(seed, items=4, planner=None):
    return Agent(planner=planner, world=DeadlineWorld(seed, items=items)).run(
        max_steps=200)


class TestDeadlinePlanIntegration(unittest.TestCase):
    def test_the_shipped_planner_collects_every_item(self):
        steps = 0
        for seed in range(20):
            trace = _run(seed)
            self.assertEqual(_collected(trace), 4.0, seed)
            self.assertLess(len(trace), 100, seed)
            steps += len(trace)
        self.assertEqual(steps, 533)

    def test_the_ablation_restores_the_shortest_tour_loss(self):
        trace = _run(0, planner=Planner(deadline_ordering=False))
        self.assertEqual(_collected(trace), 3.0)
        self.assertEqual(len(trace), 200)

    def test_the_schedule_generalises_to_five_and_six_items(self):
        expected = {5: 310, 6: 336}
        for items in (5, 6):
            steps = 0
            for seed in range(10):
                trace = _run(seed, items=items)
                self.assertEqual(_collected(trace), float(items),
                                 (items, seed))
                steps += len(trace)
            self.assertEqual(steps, expected[items], items)

    def test_the_learned_scalar_does_not_generalise_where_the_schedule_does(self):
        from evals.headroom import _plan_actions
        from evals.headroom_learning import order_for_weight

        def scalar_items(seed, weight, count=6):
            world = DeadlineWorld(seed, items=count)
            world.reset()
            total = 0.0
            for action in _plan_actions(
                    order_for_weight(seed, weight, items=count)):
                _state, reward, done = world.step(action)
                total += reward
                if done:
                    break
            return total

        learned = sum(scalar_items(seed, 4.0) for seed in range(10)) / 10
        better = sum(scalar_items(seed, 8.0) for seed in range(10)) / 10
        shipped = sum(_collected(_run(seed, items=6)) for seed in range(10)) / 10
        self.assertEqual(shipped, 6.0)
        self.assertLess(learned, 6.0)
        self.assertLess(better, 6.0)


class TestDeadlineReadout(unittest.TestCase):
    def test_the_probe_names_the_scheduled_item(self):
        world = DeadlineWorld(0)
        state = world.reset()
        planner = Planner()
        planner.plan(state, [state])
        probe = planner.last_probe["deadline"]
        self.assertEqual(probe["chosen"], [7, 6])
        self.assertEqual(probe["deadline"], 14)
        self.assertEqual(probe["collectible"], 4)
        self.assertEqual(len(probe["schedule"]), 4)
        self.assertGreaterEqual(probe["slack"], 0)
        self.assertEqual(planner.last_probe["rule"]["goal"], [7, 6])

    def test_the_ablation_emits_no_deadline_readout(self):
        world = DeadlineWorld(0)
        state = world.reset()
        planner = Planner(deadline_ordering=False)
        planner.plan(state, [state])
        self.assertNotIn("deadline", planner.last_probe)
        self.assertNotIn("deadlines", planner.last_probe["resolved"])

    def test_the_model_observation_and_prompt_carry_deadlines(self):
        world = DeadlineWorld(0)
        state = world.reset()
        backend = CaptureBackend()
        Planner(backend=backend).plan(state, [state])
        observation = backend.observations[0]
        self.assertIn("deadlines", observation)
        self.assertIn([7, 6, 14], observation["deadlines"])
        prompt = build_prompt(observation)
        self.assertIn("Deadlines", prompt)
        self.assertIn("[7, 6, 14]", prompt)


class TestStandingBehavior(unittest.TestCase):
    def test_the_nine_pins_are_unchanged(self):
        cases = (("T1_forage", 71, 16, 3.0),
                 ("T2_delayed_match", 3, 8, 1.0),
                 ("T3_navigate", 15, 13, 1.0),
                 ("T3_navigate", 65, 6, 1.0),
                 ("T3_navigate", 74, 9, 1.0),
                 ("T3_navigate", 202, 7, 1.0),
                 ("T3_navigate", 272, 14, 1.0),
                 ("T3_navigate", 307, 6, 1.0),
                 ("T3_navigate", 479, 10, 1.0))
        for task, seed, steps, reward in cases:
            trace = Agent().run_task(task, seed, max_steps=200)
            self.assertEqual(len(trace), steps, (task, seed))
            self.assertEqual(_collected(trace), reward, (task, seed))

    def test_the_thirty_seed_totals_are_unchanged(self):
        totals = {"T1_forage": 0, "T2_delayed_match": 0,
                  "T3_navigate": 0}
        for task in totals:
            for seed in range(30):
                totals[task] += len(Agent().run_task(task, seed))
        self.assertEqual(totals, {"T1_forage": 466,
                                  "T2_delayed_match": 240,
                                  "T3_navigate": 217})


class TestDeadlinePolicy(unittest.TestCase):
    def test_the_declared_policy_matches_the_schedule(self):
        self.assertEqual(PLANNER_POLICY.get("deadline_ordering"),
                         "max-collected-then-shortest")
        legacy = dict(PLANNER_POLICY)
        legacy.pop("deadline_ordering", None)
        self.assertNotEqual(policy_digest(), policy_digest(legacy))

    def test_the_flag_is_validated(self):
        with self.assertRaises(ValueError):
            Planner(deadline_ordering="yes")


class TestScheduleHelper(unittest.TestCase):
    def test_it_picks_the_urgent_item_before_a_nearer_patient_one(self):
        goal, info = _first_of_deadline_tour(
            (0, 0), [[1, 0], [7, 0]], {(1, 0): 20, (7, 0): 8}, steps=0)
        self.assertEqual(goal, [7, 0])
        self.assertEqual(info["collectible"], 2)

    def test_it_falls_back_when_there_are_too_many_items(self):
        # ADR-196 raised the exact-schedule cap from 7 to 12 items; the
        # fallback now starts one item past that cap.
        cells = [[x, 0] for x in range(13)]
        deadlines = {(x, 0): 200 for x in range(13)}
        goal, info = _first_of_deadline_tour((0, 0), cells, deadlines)
        self.assertIsNone(goal)
        self.assertEqual(info["reason"], "item-limit")
        self.assertEqual(info["limit"], 12)


if __name__ == "__main__":
    unittest.main()
