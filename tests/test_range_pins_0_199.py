"""Backfill range pins 0-199: ledger-verified totals without test pins.

Lattice snapshot-diffing transfer, part 2 (cycle 25 did exhaustive T3;
cycle 23 froze holdout 500-599). These four totals were verified in
cycles 3/5/6 and carried in CYCLES.md prose, but no test asserted
them: T3 0-99 683, T3 100-199 732, T2 0-99 800 (structural 8/seed),
T1 100-199 1646 (sums differ per range; optimality is per-seed
tour+3, pinned in test_tour_order for 0-99 and audited 100/100 for
100-199).
"""

import unittest

from agent import Agent


def _total(task, seeds):
    total = 0
    for seed in seeds:
        trace = Agent().run_task(task, seed)
        assert trace[-1]["done"], "%s:%d" % (task, seed)
        total += len(trace)
    return total


class TestRangePins0199(unittest.TestCase):
    def test_range_totals_0_199(self):
        self.assertEqual(_total("T3_navigate", range(0, 100)), 683)
        self.assertEqual(_total("T3_navigate", range(100, 200)), 732)
        self.assertEqual(_total("T2_delayed_match", range(0, 100)), 800)
        self.assertEqual(_total("T1_forage", range(100, 200)), 1646)


if __name__ == "__main__":
    unittest.main()
