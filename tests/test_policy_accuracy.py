"""Policy accuracy: declared config matches the shipped planner.

Cycle-32 collapsed _has_exit to a leaf check, but PLANNER_POLICY still
advertises lookahead_depth 4. A stale citation misbinds evidence.
"""

import unittest

from agent import PLANNER_POLICY, policy_digest


class TestPolicyAccuracy(unittest.TestCase):
    def test_no_dead_depth_knob(self):
        self.assertNotIn("lookahead_depth", PLANNER_POLICY)

    def test_declares_leaf_viability(self):
        self.assertEqual(PLANNER_POLICY.get("viability"), "leaf")

    def test_digest_differs_from_legacy_depth4(self):
        legacy = dict(PLANNER_POLICY)
        legacy["lookahead_depth"] = 4
        legacy.pop("viability", None)
        self.assertNotEqual(policy_digest(), policy_digest(legacy))


if __name__ == "__main__":
    unittest.main()
