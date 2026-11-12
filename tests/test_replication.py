"""A scan candidate must replicate on held-out episodes.

The family-wise scan corrects for testing many pairs on one pool. It does
not protect against selecting the one pool where a noise pair happened to
clear the tail. The module-state channel makes that failure visible: on
``T3_navigate`` seeds 0-9 its ``(0,4)`` M-S pair reads ``syn +0.13`` at
per-pair ``p_upper 0.045``; on the held-out seeds 10-19 the same pair reads
``syn +0.0076`` at ``p_upper 0.97``. A train-only report calls the first a
candidate.

``scan_with_holdout`` keeps the family scan on the train rows, re-runs it
at ``max(trials, 200)`` to reject a trial-count artifact, and tests every
candidate on the held-out rows with the same pair gate. A candidate is
selected only when the higher-trial tail survives and the holdout pair is
valid, positive and outside its null. ``require_stability=False`` and
``require_replication=False`` are the executable ablations.
"""

import json
import os
import random
import tempfile
import unittest

from agent import Agent
from evals.module_state import pool_signals
from evals.replication import scan_with_holdout


def _signal_rows(seeds, task="T3_navigate"):
    rows = []
    with tempfile.TemporaryDirectory() as directory:
        paths = []
        for seed in seeds:
            path = os.path.join(directory, "run-%d.jsonl" % seed)
            Agent(module_signals=True).run_task_logged(
                task, seed, max_steps=200, log_path=path)
            paths.append(path)
        rows = pool_signals(paths)
    return rows, [row[-1] for row in rows]


def _planted(seed, n=64):
    """A non-leaky XOR between column 0 (M) and column 2 (P)."""
    rng = random.Random(seed)
    rows, target = [], []
    for _ in range(n):
        first = rng.randint(0, 1)
        second = rng.randint(0, 1)
        outcome = first ^ second
        rows.append([first, rng.randint(0, 1), second, rng.randint(0, 1),
                     rng.randint(0, 1), rng.randint(0, 1),
                     rng.randint(0, 1), rng.randint(0, 1), outcome])
        target.append(outcome)
    return rows, target


class TestHoldoutReplication(unittest.TestCase):
    def test_a_train_only_signal_candidate_fails_holdout(self):
        train_rows, train_target = _signal_rows(range(10))
        holdout_rows, holdout_target = _signal_rows(range(10, 20))
        result = scan_with_holdout(train_rows, train_target,
                                   holdout_rows, holdout_target, trials=100,
                                   direction="positive")
        candidates = [item["candidate"]["columns"]
                      for item in result["candidates"]]
        self.assertIn([0, 4], candidates)
        self.assertEqual([item["candidate"]["columns"]
                          for item in result["selected"]], [])
        rejected = [item["candidate"]["columns"]
                    for item in result["rejected"]]
        self.assertIn([0, 4], rejected)
        candidate = [item for item in result["candidates"]
                     if item["candidate"]["columns"] == [0, 4]][0]
        self.assertFalse(candidate["stable"])
        self.assertEqual(result["stability_trials"], 200)

    def test_the_ablation_returns_the_train_candidates(self):
        train_rows, train_target = _signal_rows(range(10))
        holdout_rows, holdout_target = _signal_rows(range(10, 20))
        result = scan_with_holdout(train_rows, train_target,
                                   holdout_rows, holdout_target, trials=100,
                                   direction="positive",
                                   require_replication=False,
                                   require_stability=False)
        self.assertTrue(result["candidates"])
        self.assertEqual(result["selected"], result["candidates"])
        self.assertEqual(result["rejected"], [])

    def test_a_planted_cross_module_pair_replicates(self):
        train_rows, train_target = _planted(1)
        holdout_rows, holdout_target = _planted(2)
        result = scan_with_holdout(train_rows, train_target,
                                   holdout_rows, holdout_target, trials=100,
                                   direction="positive")
        replicated = [item["candidate"]["columns"]
                      for item in result["selected"]]
        self.assertEqual(replicated, [[0, 2]])
        self.assertTrue(all(item["replicated"]
                            for item in result["candidates"]))
        self.assertTrue(all(item["stable"]
                            for item in result["candidates"]))

    def test_no_candidate_degrades_to_empty(self):
        rows = [[0.0] * 9 for _ in range(10)]
        target = [0.0] * 10
        result = scan_with_holdout(rows, target, rows, target, trials=50,
                                   stability_trials=50)
        self.assertEqual(result["candidates"], [])
        self.assertEqual(result["selected"], [])
        self.assertEqual(result["rejected"], [])

    def test_a_100_trial_candidate_is_unstable_at_200(self):
        train_rows, train_target = _signal_rows(range(10))
        holdout_rows, holdout_target = _signal_rows(range(10, 20))
        result = scan_with_holdout(train_rows, train_target,
                                   holdout_rows, holdout_target,
                                   trials=100, stability_trials=200,
                                   direction="positive",
                                   require_replication=False)
        self.assertEqual(result["selected"], [])
        self.assertTrue(result["rejected"])
        for item in result["candidates"]:
            self.assertFalse(item["stable"])

    def test_the_stability_ablation_returns_the_candidate(self):
        train_rows, train_target = _signal_rows(range(10))
        holdout_rows, holdout_target = _signal_rows(range(10, 20))
        result = scan_with_holdout(train_rows, train_target,
                                   holdout_rows, holdout_target,
                                   trials=100, stability_trials=200,
                                   direction="positive",
                                   require_replication=False,
                                   require_stability=False)
        self.assertEqual([item["candidate"]["columns"]
                          for item in result["selected"]], [[0, 4]])

    def test_a_replicated_anti_interaction_is_selected(self):
        train_rows, train_target = _signal_rows(range(10))
        holdout_rows, holdout_target = _signal_rows(range(10, 20))
        result = scan_with_holdout(train_rows, train_target,
                                   holdout_rows, holdout_target, trials=100,
                                   direction="both")
        anti = [item for item in result["selected"]
                if item["direction"] == "negative"]
        self.assertTrue(anti)
        for item in anti:
            self.assertLess(item["candidate"]["syn"], 0.0)
            self.assertLessEqual(item["candidate"]["family"]["p_lower"], 0.05)
            self.assertLessEqual(item["holdout"]["null"]["p_lower"], 0.05)

    def test_positive_only_ignores_the_anti_interaction(self):
        train_rows, train_target = _signal_rows(range(10))
        holdout_rows, holdout_target = _signal_rows(range(10, 20))
        result = scan_with_holdout(train_rows, train_target,
                                   holdout_rows, holdout_target, trials=100,
                                   direction="positive")
        self.assertEqual([item["candidate"]["columns"]
                          for item in result["selected"]], [])

    def test_negative_only_selects_the_anti_interaction(self):
        train_rows, train_target = _signal_rows(range(10))
        holdout_rows, holdout_target = _signal_rows(range(10, 20))
        result = scan_with_holdout(train_rows, train_target,
                                   holdout_rows, holdout_target, trials=100,
                                   direction="negative")
        self.assertTrue(result["selected"])
        self.assertTrue(all(item["direction"] == "negative"
                            for item in result["selected"]))
        self.assertTrue(all(item["candidate"]["syn"] < 0.0
                            for item in result["selected"]))

    def test_block_level_holdout_replicates_p_s_on_t1(self):
        train_rows, train_target = _signal_rows(range(10))
        holdout_rows, holdout_target = _signal_rows(range(10), task="T1_forage")
        result = scan_with_holdout(train_rows, train_target,
                                   holdout_rows, holdout_target, trials=100,
                                   direction="both", level="block")
        self.assertTrue(result["selected"])
        for item in result["selected"]:
            self.assertEqual(item["direction"], "negative")
            self.assertEqual(set(item["candidate"]["blocks"]), {"P", "S"})
            self.assertTrue(item["holdout_matches"])

    def test_block_level_selection_collapses_to_one_dependency(self):
        train_rows, train_target = _signal_rows(range(10))
        holdout_rows, holdout_target = _signal_rows(range(10), task="T1_forage")
        result = scan_with_holdout(train_rows, train_target,
                                   holdout_rows, holdout_target, trials=100,
                                   direction="both", level="block")
        self.assertEqual(len(result["selected"]), 1)
        self.assertEqual(set(result["selected"][0]["candidate"]["blocks"]),
                         {"P", "S"})
        raw = scan_with_holdout(train_rows, train_target,
                                holdout_rows, holdout_target, trials=100,
                                direction="both", level="block", unique=False)
        self.assertEqual(len(raw["selected"]), 2)

    def test_block_holdout_uses_the_deduped_family(self):
        train_rows, train_target = _signal_rows(range(10))
        holdout_rows, holdout_target = _signal_rows(range(10, 20))
        deduped = scan_with_holdout(train_rows, train_target,
                                    holdout_rows, holdout_target, trials=100,
                                    direction="both", level="block")
        raw = scan_with_holdout(train_rows, train_target,
                                holdout_rows, holdout_target, trials=100,
                                direction="both", level="block",
                                dedupe=False)
        self.assertTrue(deduped["selected"])
        self.assertEqual(
            deduped["selected"][0]["holdout_matches"][0]["family"]["family_size"],
            10)
        self.assertTrue(raw["selected"])
        self.assertEqual(
            raw["selected"][0]["holdout_matches"][0]["family"]["family_size"],
            14)

    def test_column_level_holdout_does_not_replicate_across_t1(self):
        train_rows, train_target = _signal_rows(range(10))
        holdout_rows, holdout_target = _signal_rows(range(10), task="T1_forage")
        result = scan_with_holdout(train_rows, train_target,
                                   holdout_rows, holdout_target, trials=100,
                                   direction="both", level="column")
        self.assertEqual([item["candidate"]["columns"]
                          for item in result["selected"]], [])

    def test_block_level_holdout_fails_on_t2(self):
        train_rows, train_target = _signal_rows(range(10))
        holdout_rows, holdout_target = _signal_rows(
            range(10), task="T2_delayed_match")
        result = scan_with_holdout(train_rows, train_target,
                                   holdout_rows, holdout_target, trials=100,
                                   direction="both", level="block")
        self.assertEqual([item["candidate"]["columns"]
                          for item in result["selected"]], [])

    def test_level_must_be_known(self):
        rows, target = _planted(6)
        with self.assertRaises(ValueError):
            scan_with_holdout(rows, target, rows, target, level="cell")

    def test_direction_must_be_known(self):
        rows, target = _planted(5)
        with self.assertRaises(ValueError):
            scan_with_holdout(rows, target, rows, target,
                              direction="sideways")

    def test_the_holdout_result_is_deterministic(self):
        train_rows, train_target = _planted(3)
        holdout_rows, holdout_target = _planted(4)
        first = scan_with_holdout(train_rows, train_target,
                                  holdout_rows, holdout_target, trials=80)
        second = scan_with_holdout(train_rows, train_target,
                                   holdout_rows, holdout_target, trials=80)
        self.assertEqual([(item["candidate"]["columns"], item["replicated"])
                          for item in first["candidates"]],
                         [(item["candidate"]["columns"], item["replicated"])
                          for item in second["candidates"]])


if __name__ == "__main__":
    unittest.main()
