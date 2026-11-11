"""A module interaction needs two module blocks, not the world hub.

The pair scan treats every feature column as a module. Pooling ten
``T3_navigate`` episodes (seeds 0-9, fully wired) gives 70 deduped rows and
one reward per episode. The uncorrected family-wise scan returns five
"interactions":

    (0,6) (1,6) (2,6) (5,6)  syn +0.2142  family p_upper 0.0198
    (3,6)                    syn +0.1895  family p_upper 0.0297

Column 6 is ``hub0`` (x), and columns 0/1/2/5 are the step counters. Those
are time-and-position pairs, not M/P/S module pairs. ``lesion_audit``
already labels the blocks; the scan did not use them.

``module_interactions`` restricts the same corrected scan to pairs whose
two columns belong to different M/P/S blocks and returns nothing on this
pooled trace. A synthetic XOR across the M and P blocks is still detected,
so the filter does not erase real cross-module candidates.
"""

import json
import os
import random
import tempfile
import unittest

from agent import Agent
from evals.pair_scan import (block_for, interactions, module_interactions,
                             module_pair, scan_pairs, world_interactions)
from evals.recompute import _vec_row, dedupe_rows
from memory.store import MemoryStore
from planner.plan import Planner as TrackerPlanner
from self_model.model import SelfModel as PersistentSelfModel


def _episode(seed):
    with tempfile.TemporaryDirectory() as directory:
        log = os.path.join(directory, "run.jsonl")
        store = MemoryStore(os.path.join(directory, "m.db"))
        try:
            Agent(
                memory_store=store,
                planner_tracker=TrackerPlanner(
                    [("s%d" % i, "op%d" % i) for i in range(30)]),
                self_model=PersistentSelfModel(),
            ).run_task_logged("T3_navigate", seed, max_steps=200, log_path=log)
        finally:
            store.close()
        with open(log, encoding="utf-8") as handle:
            rows = dedupe_rows(
                [row for row in (_vec_row(json.loads(line))
                                 for line in handle) if row])
    width = max(len(row) for row in rows)
    return [row + [0.0] * (width - len(row)) for row in rows]


def _pooled(seeds=range(10)):
    rows = []
    for seed in seeds:
        rows.extend(_episode(seed))
    return rows, [row[-1] for row in rows]


def _cross_module(n=64, seed=28):
    """A planted XOR between column 0 (M) and column 2 (P)."""
    rng = random.Random(seed)
    rows, target = [], []
    for _ in range(n):
        first = rng.randint(0, 1)
        second = rng.randint(0, 1)
        outcome = first ^ second
        rows.append([first, rng.randint(0, 1),
                     second, rng.randint(0, 1),
                     rng.randint(0, 1), rng.randint(0, 1),
                     rng.randint(0, 1), rng.randint(0, 1),
                     outcome])
        target.append(outcome)
    return rows, target


class TestModulePairScan(unittest.TestCase):
    def test_blocks_label_the_legacy_vector(self):
        width = 9
        self.assertEqual([block_for(index, width) for index in range(width)],
                         ["M", "M", "P", "P", "S", "S", "hub", "hub", "target"])

    def test_pooled_scan_reports_world_pairs(self):
        rows, target = _pooled()
        reports = interactions(rows, target, trials=200)
        self.assertTrue(reports)
        for report in reports:
            self.assertIn("hub", report["blocks"])

    def test_module_pair_accepts_only_cross_module_blocks(self):
        self.assertTrue(module_pair({"blocks": ["M", "P"]}))
        self.assertFalse(module_pair({"blocks": ["S", "S"]}))
        self.assertFalse(module_pair({"blocks": ["M", "hub"]}))

    def test_world_interactions_match_the_hub_subset(self):
        rows, target = _pooled()
        selected = interactions(rows, target, trials=200)
        world = world_interactions(rows, target, trials=200)
        self.assertTrue(world)
        self.assertEqual(world, [report for report in selected
                                 if "hub" in report["blocks"]])

    def test_world_interactions_exclude_module_pairs(self):
        rows, target = _cross_module()
        self.assertEqual([report["columns"]
                          for report in interactions(rows, target, trials=200)],
                         [[0, 2]])
        self.assertEqual(world_interactions(rows, target, trials=200), [])

    def test_pooled_module_interactions_are_empty(self):
        rows, target = _pooled()
        self.assertEqual(module_interactions(rows, target, trials=200), [])

    def test_module_interactions_require_two_different_blocks(self):
        rows, target = _cross_module()
        reports = module_interactions(rows, target, trials=200)
        self.assertEqual([report["columns"] for report in reports], [[0, 2]])
        self.assertEqual(reports[0]["blocks"], ["M", "P"])

    def test_a_cross_module_planted_pair_is_detected(self):
        rows, target = _cross_module()
        reports = scan_pairs(rows, target, trials=200, family_wise=True)
        by_columns = {tuple(report["columns"]): report
                      for report in reports if report["ok"]}
        self.assertIn((0, 2), by_columns)
        self.assertLessEqual(by_columns[(0, 2)]["family"]["p_upper"], 0.05)

    def test_the_ablation_keeps_the_world_pairs(self):
        rows, target = _pooled()
        all_pairs = interactions(rows, target, trials=200)
        module_pairs = module_interactions(rows, target, trials=200)
        self.assertTrue(all_pairs)
        self.assertEqual(module_pairs, [])
        self.assertTrue(any("hub" in report["blocks"] for report in all_pairs))


if __name__ == "__main__":
    unittest.main()
