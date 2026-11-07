"""Pool-corridor gate accuracy: declared config matches shipped pooling.

Cycle 37 gated corridor weighting in the pool on two-or-more blockers
(single blockers stay visits-only), but PLANNER_POLICY still cites
only detour_pooling visits with no gate. A stale citation misbinds
evidence.
"""

import unittest

from agent import PLANNER_POLICY, policy_digest


class TestPoolCorridorPolicy(unittest.TestCase):
    def test_declares_pool_corridor_gate(self):
        self.assertEqual(PLANNER_POLICY.get("pool_corridor"), ">=2")

    def test_digest_differs_from_pre_gate_legacy(self):
        legacy = dict(PLANNER_POLICY)
        legacy.pop("pool_corridor", None)
        self.assertNotEqual(policy_digest(), policy_digest(legacy))

    def test_gate_value_sensitive(self):
        altered = dict(PLANNER_POLICY)
        altered["pool_corridor"] = "never"
        self.assertNotEqual(policy_digest(altered), policy_digest())


if __name__ == "__main__":
    unittest.main()
