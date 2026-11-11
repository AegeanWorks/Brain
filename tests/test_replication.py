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


def _signal_rows(seeds):
    rows = []
    with tempfile.TemporaryDirectory() as directory:
        paths = []
        for seed in seeds:
            path = os.path.join(directory, "run-%d.jsonl" % seed)
            Agent(module_signals=True).run_task_logged(
                "T3_navigate", seed, max_steps=200, log_path=path)
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
                                   holdout_rows, holdout_target, trials=100)
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
                                   require_replication=False,
                                   require_stability=False)
        self.assertTrue(result["candidates"])
        self.assertEqual(result["selected"], result["candidates"])
        self.assertEqual(result["rejected"], [])

    def test_a_planted_cross_module_pair_replicates(self):
        train_rows, train_target = _planted(1)
        holdout_rows, holdout_target = _planted(2)
        result = scan_with_holdout(train_rows, train_target,
                                   holdout_rows, holdout_target, trials=100)
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
                                   require_replication=False,
                                   require_stability=False)
        self.assertEqual([item["candidate"]["columns"]
                          for item in result["selected"]], [[0, 4]])

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
