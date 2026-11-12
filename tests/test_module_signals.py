"""The module-state channel must add testable state without changing actions.

``Agent(module_signals=True)`` writes six pre-action values per step:
M=[distinct positions, turns], P=[BFS distance, ties],
S=[online probability, distinct feature keys seen]. They use the same M/P/S layout as
the legacy vector, so ``evals.module_state`` can pool them into seven-column
rows (six signals plus reward) and feed ``evals.pair_scan`` directly.

Measured ten default-wired ``T3_navigate`` episodes (seeds 0-9):
70 signal rows, 5 gate-passing cross-module M/P/S pairs, and no
family-significant module interaction at 200 trials. The two S values are
independent (the earlier ``seen`` counter was a function of the probability). The legacy vector on
the same episodes has 70 rows and **0** gate-passing module pairs; its
selected pairs are all ``hub`` pairs. ``module_signals=False`` is the
ablation: no signal rows, no testable module pairs.
"""

import json
import os
import random
import tempfile
import unittest

from agent import Agent
from evals.module_state import (pool_signals, read_signals,
                                scan_module_state_blocks,
                                scan_module_states, scan_traces,
                                signals_from_trace)
from evals.coldstart import cold_run, warm_run
from evals.replication import scan_with_holdout
from memory.store import MemoryStore
from evals.pair_scan import (_dependent, _target_leak, module_interactions,
                             scan_pairs)
from evals.recompute import _vec_row, dedupe_rows


def _logs(directory, module_signals, seeds=range(10), task="T3_navigate",
          module_s_mode="keys", module_m_mode="turns",
          module_p_mode="alternatives"):
    paths = []
    for seed in seeds:
        path = os.path.join(directory, "run-%s-%d.jsonl" % (task, seed))
        Agent(module_signals=module_signals,
              module_s_mode=module_s_mode,
              module_m_mode=module_m_mode,
              module_p_mode=module_p_mode).run_task_logged(
            task, seed, max_steps=200, log_path=path)
        paths.append(path)
    return paths


def _cross_module_count(reports):
    return sum(
        1 for report in reports
        if report["ok"]
        and report["blocks"][0] in ("M", "P", "S")
        and report["blocks"][1] in ("M", "P", "S")
        and report["blocks"][0] != report["blocks"][1])


def _planted_log(directory, name, seed, n=64):
    """Write action records whose reward is an M/P XOR of the signals."""
    rng = random.Random(seed)
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8") as handle:
        for _ in range(n):
            first = rng.randint(0, 1)
            second = rng.randint(0, 1)
            outcome = first ^ second
            handle.write(json.dumps({
                "type": "action",
                "args": {
                    "signals": {"M": [first, 0], "P": [second, 0],
                                "S": [0, 0]},
                    "reward": outcome,
                },
            }) + "\n")
    return path


class TestModuleSignals(unittest.TestCase):
    def test_signals_are_emitted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = _logs(directory, True, seeds=[15])[0]
            rows = read_signals(path)
        self.assertEqual(len(rows), 13)
        self.assertTrue(all(len(row) == 7 for row in rows))
        self.assertTrue(all(row[4] >= 0.0 for row in rows))

    def test_trace_carries_signals(self):
        trace = Agent(module_signals=True).run_task("T3_navigate", 15)
        self.assertEqual(len(trace), 13)
        self.assertTrue(all("signals" in step for step in trace))
        rows = signals_from_trace(trace)
        self.assertEqual(len(rows), 13)
        self.assertTrue(all(len(row) == 7 for row in rows))

    def test_disabled_trace_has_no_signals(self):
        trace = Agent(module_signals=False).run_task("T3_navigate", 15)
        self.assertTrue(all("signals" not in step for step in trace))
        self.assertEqual(signals_from_trace(trace), [])

    def test_trace_and_log_signals_agree(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "trace.jsonl")
            trace = Agent(module_signals=True).run_task_logged(
                "T3_navigate", 15, max_steps=200, log_path=path)
            self.assertEqual(signals_from_trace(trace), read_signals(path))

    def test_in_memory_scan_matches_the_log_path(self):
        traces = [Agent(module_signals=True).run_task("T3_navigate", seed)
                  for seed in range(10)]
        reports = scan_traces(traces, trials=200)
        self.assertEqual(sum(1 for report in reports if report["ok"]), 14)
        self.assertEqual(module_interactions(
            [row for trace in traces for row in signals_from_trace(trace)],
            [step["reward"] for trace in traces for step in trace],
            trials=200), [])

    def test_coldstart_trace_carries_signals(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(os.path.join(directory, "m.db"))
            try:
                warm_run(store, "T3_navigate", 15)
                _, trace, _ = cold_run(
                    store, "T3_navigate", 15,
                    log_path=os.path.join(directory, "cold.jsonl"))
            finally:
                store.close()
            rows = signals_from_trace(trace)
            log_rows = read_signals(os.path.join(directory, "cold.jsonl"))
        self.assertEqual(len(rows), len(trace))
        self.assertEqual(rows, log_rows)
        self.assertTrue(scan_traces([trace], trials=100))

    def test_module_signals_can_be_disabled(self):
        with tempfile.TemporaryDirectory() as directory:
            path = _logs(directory, False, seeds=[15])[0]
            rows = read_signals(path)
        self.assertEqual(rows, [])

    def test_signal_scan_has_more_testable_module_pairs_than_legacy(self):
        with tempfile.TemporaryDirectory() as signal_dir:
            signal_paths = _logs(signal_dir, True)
            signal_reports = scan_module_states(signal_paths, trials=200)
        with tempfile.TemporaryDirectory() as legacy_dir:
            legacy_paths = _logs(legacy_dir, False)
            legacy_rows = []
            for path in legacy_paths:
                with open(path, encoding="utf-8") as handle:
                    legacy_rows.extend(
                        dedupe_rows([row for row in
                                     (_vec_row(json.loads(line))
                                      for line in handle) if row]))
            target = [row[-1] for row in legacy_rows]
            legacy_reports = scan_pairs(legacy_rows, target, trials=200)
        self.assertEqual(_cross_module_count(signal_reports), 12)
        self.assertEqual(_cross_module_count(legacy_reports), 0)

    def test_the_s_block_is_independent(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = _logs(directory, True)
            rows = pool_signals(paths)
        self.assertFalse(_dependent([row[4] for row in rows],
                                    [row[5] for row in rows]))

    def test_turns_mode_varies_on_t3(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = _logs(directory, True)
            rows = pool_signals(paths)
        self.assertGreater(len({row[1] for row in rows}), 1)

    def test_revisits_mode_is_constant_on_t3(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = _logs(directory, True, module_m_mode="revisits")
            rows = pool_signals(paths)
        self.assertEqual(len({row[1] for row in rows}), 1)

    def test_turns_mode_adds_testable_pairs(self):
        with tempfile.TemporaryDirectory() as directory:
            turns = scan_module_states(_logs(directory, True,
                                             module_m_mode="turns"), trials=50)
        with tempfile.TemporaryDirectory() as directory:
            revisits = scan_module_states(_logs(directory, True,
                                                module_m_mode="revisits"),
                                          trials=50)
        self.assertEqual(sum(1 for report in turns if report["ok"]), 14)
        self.assertEqual(sum(1 for report in revisits if report["ok"]), 9)

    def test_alternatives_mode_removes_the_distance_leak(self):
        with tempfile.TemporaryDirectory() as directory:
            rows = pool_signals(_logs(directory, True))
        self.assertFalse(_target_leak([row[2] for row in rows],
                                      [row[-1] for row in rows]))

    def test_distance_mode_is_target_leaky(self):
        with tempfile.TemporaryDirectory() as directory:
            rows = pool_signals(_logs(directory, True,
                                      module_p_mode="distance"))
        self.assertTrue(_target_leak([row[2] for row in rows],
                                     [row[-1] for row in rows]))

    def test_alternatives_mode_adds_cross_module_pairs(self):
        with tempfile.TemporaryDirectory() as directory:
            alternatives = scan_module_states(
                _logs(directory, True, module_p_mode="alternatives"),
                trials=50)
        with tempfile.TemporaryDirectory() as directory:
            distance = scan_module_states(
                _logs(directory, True, module_p_mode="distance"), trials=50)
        self.assertEqual(_cross_module_count(alternatives), 12)
        self.assertEqual(_cross_module_count(distance), 8)

    def test_the_seen_mode_is_dependent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = _logs(directory, True, seeds=[15],
                         module_s_mode="seen")[0]
            rows = read_signals(path)
        self.assertTrue(_dependent([row[4] for row in rows],
                                   [row[5] for row in rows]))

    def test_keys_mode_adds_one_testable_pair(self):
        with tempfile.TemporaryDirectory() as directory:
            keys = scan_module_states(_logs(directory, True,
                                            module_s_mode="keys"), trials=50)
        with tempfile.TemporaryDirectory() as directory:
            seen = scan_module_states(_logs(directory, True,
                                            module_s_mode="seen"), trials=50)
        self.assertEqual(sum(1 for report in keys if report["ok"]), 14)
        self.assertEqual(sum(1 for report in seen if report["ok"]), 13)

    def test_module_interactions_are_empty_at_200_trials(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = _logs(directory, True)
            rows = pool_signals(paths)
            target = [row[-1] for row in rows]
            self.assertEqual(len(rows), 70)
            self.assertEqual(module_interactions(rows, target, trials=200), [])

    def test_signals_do_not_change_actions(self):
        plain = Agent(module_signals=False).run_task("T3_navigate", 15)
        signal = Agent(module_signals=True).run_task("T3_navigate", 15)
        self.assertEqual(
            [(step["action"], step["reward"], step["done"]) for step in plain],
            [(step["action"], step["reward"], step["done"]) for step in signal])

    def test_block_split_reaches_module_and_world(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = _logs(directory, True)
            blocks = scan_module_state_blocks(paths, trials=200)
        self.assertEqual(blocks["module"], [])
        self.assertEqual(blocks["world"], [])

    def test_a_planted_signal_interaction_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = _planted_log(directory, "planted.jsonl", 1)
            blocks = scan_module_state_blocks([path], trials=100)
        self.assertEqual([report["columns"]
                          for report in blocks["module"]], [[0, 2]])
        self.assertEqual(blocks["world"], [])

    def test_a_planted_signal_interaction_replicates(self):
        with tempfile.TemporaryDirectory() as directory:
            train = _planted_log(directory, "train.jsonl", 1)
            holdout = _planted_log(directory, "holdout.jsonl", 2)
            train_rows = pool_signals([train])
            holdout_rows = pool_signals([holdout])
            result = scan_with_holdout(
                train_rows, [row[-1] for row in train_rows],
                holdout_rows, [row[-1] for row in holdout_rows], trials=100)
        self.assertEqual([item["candidate"]["columns"]
                          for item in result["selected"]], [[0, 2]])
        self.assertTrue(all(item["stable"] and item["replicated"]
                            for item in result["candidates"]))

    def test_the_positive_control_needs_the_signal_block(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "plain.jsonl")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(json.dumps({"type": "action",
                                         "args": {"reward": 1.0}}) + "\n")
            rows = read_signals(path)
            blocks = scan_module_state_blocks([path], trials=50)
        self.assertEqual(rows, [])
        self.assertEqual(blocks["module"], [])
        self.assertEqual(blocks["world"], [])

    def test_malformed_signal_rows_are_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "bad.jsonl")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(json.dumps({"type": "action",
                                         "args": {"signals": {"M": [1]}}}) + "\n")
                handle.write(json.dumps({"type": "action",
                                         "args": {"signals": {"M": [1, 2],
                                                              "P": [3]}}}) + "\n")
            self.assertEqual(read_signals(path), [])


if __name__ == "__main__":
    unittest.main()
