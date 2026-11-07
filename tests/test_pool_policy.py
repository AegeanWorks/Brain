"""Detour-pooling policy accuracy: declared config matches shipped planner.

Cycle 35 pooled viable goal steps with backup detours by least-visited
for obstacle navigation, but PLANNER_POLICY still cites the pre-pool
configuration. A stale citation misbinds evidence.
"""

import unittest

from agent import PLANNER_POLICY, policy_digest


class TestPoolPolicy(unittest.TestCase):
    def test_declares_detour_pooling(self):
        self.assertEqual(PLANNER_POLICY.get("detour_pooling"), "visits")

    def test_digest_differs_from_pre_pool_legacy(self):
        legacy = dict(PLANNER_POLICY)
        legacy.pop("detour_pooling", None)
        self.assertNotEqual(policy_digest(), policy_digest(legacy))

    def test_pooling_value_sensitive(self):
        altered = dict(PLANNER_POLICY)
        altered["detour_pooling"] = "none"
        self.assertNotEqual(policy_digest(altered), policy_digest())


if __name__ == "__main__":
    unittest.main()
