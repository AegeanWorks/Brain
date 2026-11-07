"""Rule-path confidence readout: BFS move ties in the planner probe.

Failing-first: the probe has no statement of how ambiguous the rule
action is. A unique best move should read confidence 1.0, a two-way tie
0.5, a collect/wait at the goal 1.0, and the readout must disappear with
``rule_readout=False`` without changing the action.
"""

import json
import unittest

from agent import Agent, PLANNER_POLICY, Planner, policy_digest


def _state(x, y, target=None, obstacles=None, task="T3_navigate",
           items=None, steps=0):
    state = {"task": task, "x": x, "y": y, "steps": steps}
    if target is not None:
        state["target"] = target
    if obstacles is not None:
        state["obstacles"] = obstacles
    if items is not None:
        state["items_positions"] = items
    return state


def _plan(planner, state):
    action = planner.plan(state, [])
    return action, planner.last_probe


class TestRuleConfidence(unittest.TestCase):
    def test_unique_move_has_full_confidence(self):
        action, probe = _plan(Planner(), _state(0, 0, [2, 0]))
        rule = probe["rule"]
        self.assertEqual(action, "right")
        self.assertEqual(rule["goal"], [2, 0])
        self.assertEqual(rule["ties"], 1)
        self.assertEqual(rule["distance"], 1)
        self.assertEqual(rule["rule_distance"], 1)
        self.assertAlmostEqual(rule["confidence"], 1.0)
        self.assertTrue(rule["optimal"])

    def test_two_way_tie_has_half_confidence(self):
        action, probe = _plan(Planner(), _state(0, 0, [2, 2]))
        rule = probe["rule"]
        self.assertEqual(action, "right")
        self.assertEqual(rule["ties"], 2)
        self.assertEqual(rule["distance"], 3)
        self.assertEqual(rule["rule_distance"], 3)
        self.assertAlmostEqual(rule["confidence"], 0.5)
        self.assertTrue(rule["optimal"])

    def test_tie_alternatives_are_listed(self):
        action, probe = _plan(Planner(), _state(0, 0, [2, 2]))
        rule = probe["rule"]
        alternatives = {item["action"]: item
                        for item in rule["alternatives"]}
        self.assertEqual(set(alternatives), {"down", "right"})
        self.assertEqual({item["distance"]
                          for item in alternatives.values()}, {3})
        self.assertTrue(all(item["distance"] == rule["distance"]
                            for item in alternatives.values()))
        self.assertEqual(alternatives["right"]["visits"], 0)
        self.assertIn(action, alternatives)

    def test_alternatives_carry_visit_counts(self):
        memories = ([{"x": 0, "y": 1}] * 3
                    + [{"x": 1, "y": 0}] * 1)
        planner = Planner()
        action = planner.plan(_state(0, 0, [2, 2]), memories)
        probe = planner.last_probe
        alternatives = {item["action"]: item
                        for item in probe["rule"]["alternatives"]}
        self.assertEqual(alternatives["down"]["visits"], 3)
        self.assertEqual(alternatives["right"]["visits"], 1)
        self.assertIn(action, alternatives)

    def test_unique_move_has_one_alternative(self):
        action, probe = _plan(Planner(), _state(0, 0, [2, 0]))
        alternatives = probe["rule"]["alternatives"]
        self.assertEqual([item["action"] for item in alternatives],
                         ["right"])
        self.assertEqual(alternatives[0]["distance"], 1)
        self.assertIn(action, [item["action"] for item in alternatives])

    def test_collect_has_empty_alternatives(self):
        _, probe = _plan(Planner(), _state(2, 2, [2, 2]))
        self.assertEqual(probe["rule"]["alternatives"], [])

    def test_alternatives_are_json_safe(self):
        _, probe = _plan(Planner(), _state(0, 0, [2, 2]))
        json.dumps(probe["rule"]["alternatives"])

    def test_collect_at_goal_has_full_confidence(self):
        action, probe = _plan(Planner(), _state(2, 2, [2, 2]))
        rule = probe["rule"]
        self.assertEqual(action, "collect")
        self.assertEqual(rule["distance"], 0)
        self.assertEqual(rule["rule_distance"], 0)
        self.assertEqual(rule["ties"], 1)
        self.assertAlmostEqual(rule["confidence"], 1.0)
        self.assertTrue(rule["optimal"])

    def test_item_tour_uses_the_rule_goal(self):
        action, probe = _plan(
            Planner(), _state(0, 0, task="T1_forage", items=[[2, 0]]))
        rule = probe["rule"]
        self.assertEqual(action, "right")
        self.assertEqual(rule["goal"], [2, 0])
        self.assertEqual(rule["ties"], 1)
        self.assertAlmostEqual(rule["confidence"], 1.0)
        self.assertTrue(rule["optimal"])

    def test_tour_audit_single_item(self):
        action, probe = _plan(
            Planner(), _state(0, 0, task="T1_forage", items=[[2, 0]]))
        tour = probe["tour"]
        self.assertEqual(action, "right")
        self.assertEqual(tour["items"], [[2, 0]])
        self.assertEqual(tour["chosen"], [2, 0])
        self.assertEqual(tour["best_length"], 2)
        self.assertEqual(tour["chosen_length"], 2)
        self.assertEqual(tour["tied_firsts"], [[2, 0]])
        self.assertEqual(tour["tie_count"], 1)
        self.assertTrue(tour["optimal"])

    def test_tour_audit_two_way_tie(self):
        action, probe = _plan(
            Planner(), _state(0, 0, task="T1_forage",
                              items=[[1, 0], [0, 1]]))
        tour = probe["tour"]
        self.assertEqual(action, "down")
        self.assertEqual(tour["chosen"], [0, 1])
        self.assertEqual(tour["best_length"], 3)
        self.assertEqual(tour["chosen_length"], 3)
        self.assertEqual(tour["tied_firsts"], [[0, 1], [1, 0]])
        self.assertEqual(tour["tie_count"], 2)
        self.assertTrue(tour["optimal"])

    def test_tour_audit_no_tie(self):
        action, probe = _plan(
            Planner(), _state(0, 0, task="T1_forage",
                              items=[[2, 0], [0, 1]]))
        tour = probe["tour"]
        self.assertEqual(action, "down")
        self.assertEqual(tour["chosen"], [0, 1])
        self.assertEqual(tour["best_length"], 4)
        self.assertEqual(tour["tie_count"], 1)
        self.assertEqual(tour["tied_firsts"], [[0, 1]])
        self.assertTrue(tour["optimal"])

    def test_tour_audit_three_items(self):
        action, probe = _plan(
            Planner(), _state(0, 0, task="T1_forage",
                              items=[[1, 0], [0, 1], [1, 1]]))
        tour = probe["tour"]
        self.assertEqual(tour["best_length"], 3)
        self.assertEqual(tour["chosen_length"], 3)
        self.assertEqual(tour["tie_count"], 2)
        self.assertIn(tour["chosen"], tour["tied_firsts"])
        self.assertTrue(tour["optimal"])
        self.assertIn(action, ("down", "right"))

    def test_tour_audit_only_for_item_moves(self):
        _, t3 = _plan(Planner(), _state(0, 0, [2, 2]))
        action, collect = _plan(
            Planner(), _state(2, 2, task="T1_forage",
                              items=[[2, 2], [1, 1]]))
        self.assertNotIn("tour", t3)
        self.assertEqual(action, "collect")
        self.assertNotIn("tour", collect)

    def test_tour_audit_off_with_readout(self):
        state = _state(0, 0, task="T1_forage", items=[[1, 0], [0, 1]])
        on_action, on_probe = _plan(Planner(rule_readout=True), state)
        off_action, off_probe = _plan(Planner(rule_readout=False), state)
        self.assertEqual(on_action, off_action)
        self.assertIn("tour", on_probe)
        self.assertNotIn("tour", off_probe)

    def test_tour_audit_is_json_safe(self):
        _, probe = _plan(
            Planner(), _state(0, 0, task="T1_forage",
                              items=[[1, 0], [0, 1]]))
        json.dumps(probe["tour"])

    def test_tour_actions_unchanged_on_logged_run(self):
        on_trace = Agent(planner=Planner(rule_readout=True)).run_task(
            "T1_forage", 71)
        off_trace = Agent(planner=Planner(rule_readout=False)).run_task(
            "T1_forage", 71)
        self.assertEqual([record["action"] for record in on_trace],
                         [record["action"] for record in off_trace])
        self.assertEqual(len(on_trace), 16)
        self.assertEqual(sum(record["reward"] for record in on_trace), 3.0)

    def test_readout_off_removes_the_field(self):
        state = _state(0, 0, [2, 2])
        on_action, on_probe = _plan(Planner(rule_readout=True), state)
        off_action, off_probe = _plan(Planner(rule_readout=False), state)
        self.assertEqual(on_action, off_action)
        self.assertIn("rule", on_probe)
        self.assertNotIn("rule", off_probe)

    def test_actions_identical_with_and_without_readout(self):
        states = (
            _state(0, 0, [2, 0]),
            _state(0, 0, [2, 2]),
            _state(2, 2, [2, 2]),
            _state(0, 0, task="T1_forage", items=[[2, 0], [0, 2]]),
            _state(1, 2, [3, 2], obstacles=[[2, 1]]),
        )
        for state in states:
            on_action, _ = _plan(Planner(rule_readout=True), dict(state))
            off_action, _ = _plan(Planner(rule_readout=False), dict(state))
            self.assertEqual(on_action, off_action)

    def test_multiple_items_readout_is_deterministic(self):
        state = _state(0, 0, task="T1_forage", items=[[2, 0], [0, 2]])
        first = _plan(Planner(), dict(state))[1]["rule"]
        second = _plan(Planner(), dict(state))[1]["rule"]
        self.assertEqual(first, second)
        self.assertIn(first["goal"], ([2, 0], [0, 2]))

    def test_no_goal_has_no_readout(self):
        action, probe = _plan(Planner(), _state(0, 0))
        self.assertEqual(action, "wait")
        self.assertNotIn("rule", probe)

    def test_readout_is_json_safe(self):
        _, probe = _plan(Planner(), _state(0, 0, [2, 2]))
        json.dumps(probe["rule"])

    def test_logged_run_actions_identical(self):
        on_trace = Agent(planner=Planner(rule_readout=True)).run_task(
            "T3_navigate", 15)
        off_trace = Agent(planner=Planner(rule_readout=False)).run_task(
            "T3_navigate", 15)
        self.assertEqual([record["action"] for record in on_trace],
                         [record["action"] for record in off_trace])
        self.assertEqual(len(on_trace), 13)
        self.assertEqual(sum(record["reward"] for record in on_trace), 1.0)

    def test_invalid_rule_readout_rejected(self):
        with self.assertRaises(ValueError):
            Planner(rule_readout="yes")
        with self.assertRaises(ValueError):
            Planner(rule_readout=1)

    def test_policy_declares_rule_readout(self):
        self.assertEqual(PLANNER_POLICY.get("rule_readout"),
                         "bfs-move-ties")
        legacy = dict(PLANNER_POLICY)
        legacy.pop("rule_readout", None)
        self.assertNotEqual(policy_digest(), policy_digest(legacy))


if __name__ == "__main__":
    unittest.main()
