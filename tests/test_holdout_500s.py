"""Frozen holdout split: seeds 500-599 pinned as regression holdout.

Transferred idea: Crucible frozen splits (overlap 0 or exit 1,
train/holdout separation). Probe seeds 0-499 drove all planner fixes;
500-599 verified fully optimal by audit scan and are now frozen: any
future change that moves these totals is a regression, not tuning.
"""

import unittest

from agent import Agent


def _steps(task, seed, max_steps=200):
    return Agent().run_task(task, seed, max_steps=max_steps)


class TestHoldout500s(unittest.TestCase):
    def test_holdout_500_599_totals(self):
        totals = {}
        for task in ("T1_forage", "T2_delayed_match", "T3_navigate"):
            total = 0
            for seed in range(500, 600):
                trace = _steps(task, seed)
                self.assertTrue(trace[-1]["done"], "%s:%d" % (task, seed))
                self.assertGreater(sum(r["reward"] for r in trace), 0.0)
                total += len(trace)
            totals[task] = total
        self.assertEqual(totals["T1_forage"], 1581)
        self.assertEqual(totals["T2_delayed_match"], 800)
        self.assertEqual(totals["T3_navigate"], 738)


if __name__ == "__main__":
    unittest.main()
