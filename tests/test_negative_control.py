"""Executable negative controls for shipped planner integrations.

Transferred idea: research-engine kill-test discipline — a test must
be able to fail (EVID-008 warns on a verified test without a
control; EVID-009 errors when a control never fails). Each control
below reproduces a pre-fix planner variant from production code and
pins its reproducibly-failing signature, so a future change that
silently heals or breaks the probe fails loudly instead of passing
vacuously.

Control C1 (corridor): disable _enters_blocked_corridor (visits-only
ordering = pre-cycle-20 semantics, depth kept 4). Must detour on 479
(12 vs intact 10) and move holdout-500s T3 738 -> 742.
"""

import unittest
from unittest import mock

import agent as agent_module
from agent import Agent


def _steps(task, seed, max_steps=200):
    return Agent().run_task(task, seed, max_steps=max_steps)


class TestNegativeControl(unittest.TestCase):
    def test_corridor_control_fails_reproducibly(self):
        with mock.patch.object(agent_module, "_enters_blocked_corridor",
                               return_value=False) as cut:
            trace = _steps("T3_navigate", 479)
            self.assertEqual(len(trace), 12)
            self.assertEqual(sum(r["reward"] for r in trace), 1.0)
            total = 0
            for seed in range(500, 600):
                leg = _steps("T3_navigate", seed)
                self.assertTrue(leg[-1]["done"])
                total += len(leg)
            self.assertEqual(total, 742)
            self.assertGreater(cut.call_count, 0)

    def test_intact_side_of_control_pair(self):
        trace = _steps("T3_navigate", 479)
        self.assertEqual(len(trace), 10)
        self.assertEqual(sum(r["reward"] for r in trace), 1.0)


if __name__ == "__main__":
    unittest.main()
