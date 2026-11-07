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
