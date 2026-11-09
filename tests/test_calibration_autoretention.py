"""Automatic calibration retention at the logged-run bridge.

Failing-first: the bridge appends every run's forecasts and leaves
retention to a separate manual call. `calibration_keep_recent` must
rotate immediately after the append: T3:15 leaves 10 live/3 archived/
13 total with the same Brier, a second run reaches 10/9/19, and the
no-threshold path keeps 13 live. Invalid or no-path requests fail before
the run; a corrupt archive fails after the verdict with all forecasts
still live.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

from agent import Agent
from calibration import summary
from calibration_store import (load_all_forecasts, load_forecasts,
                               verify_forecast_file)
from self_model.model import SelfModel
from telemetry.log import Telemetry


def _run(tmp, agent, task, seed, name, calibration_path, keep=None):
    log_path = os.path.join(tmp, name + ".jsonl")
    trace = agent.run_task_logged(
        task, seed, max_steps=200, log_path=log_path,
        calibration_path=calibration_path,
        calibration_keep_recent=keep)
    return trace, log_path


class TestCalibrationAutoRetention(unittest.TestCase):
    def test_single_run_retains_ten(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            model = SelfModel()
            trace, _ = _run(tmp, Agent(self_model=model), "T3_navigate", 15,
                            "run", path, keep=10)
            live = load_forecasts(path)
            archive = load_forecasts(path + ".archive")
            combined = load_all_forecasts(path)
            stats = summary(combined, min_resolved=2)
            backup = load_forecasts(path + ".bak")
            verified = verify_forecast_file(path)
            meta = json.loads(Path(path + ".rotation").read_text(
                encoding="utf-8"))
            rule_actions = [record["action"] for record in
                            Agent().run_task("T3_navigate", 15)]
        self.assertEqual(len(trace), 13)
        self.assertEqual(sum(record["reward"] for record in trace), 1.0)
        self.assertEqual([record["action"] for record in trace],
                         rule_actions)
        self.assertEqual(len(live), 10)
        self.assertEqual(len(archive), 3)
        self.assertEqual(len(combined), 13)
        self.assertEqual(len({r["id"] for r in combined}), 13)
        self.assertEqual(stats["counts"]["resolved"], 13)
        self.assertAlmostEqual(stats["brier"], 0.005385, places=6)
        self.assertEqual(len(backup), 13)
        self.assertTrue(verified["ok"], verified["findings"])
        self.assertEqual(meta["source_records"], 13)
        self.assertEqual(meta["archived"], 3)
        self.assertEqual(meta["kept"], 10)

    def test_second_run_extends_the_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            model = SelfModel()
            agent = Agent(self_model=model)
            _run(tmp, agent, "T3_navigate", 15, "first", path, keep=10)
            _run(tmp, agent, "T3_navigate", 65, "second", path, keep=10)
            live = load_forecasts(path)
            archive = load_forecasts(path + ".archive")
            combined = load_all_forecasts(path)
            stats = summary(combined, min_resolved=2)
            backup = load_forecasts(path + ".bak")
        self.assertEqual(len(live), 10)
        self.assertEqual(len(archive), 9)
        self.assertEqual(len(combined), 19)
        self.assertEqual(len({r["id"] for r in combined}), 19)
        self.assertEqual(stats["counts"]["resolved"], 19)
        self.assertAlmostEqual(stats["brier"], 0.006447, places=6)
        self.assertEqual(len(backup), 16)

    def test_no_threshold_keeps_all_live(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            model = SelfModel()
            _run(tmp, Agent(self_model=model), "T3_navigate", 15,
                 "run", path, keep=None)
            live = load_forecasts(path)
            archive_exists = Path(path + ".archive").exists()
            backup_exists = Path(path + ".bak").exists()
            meta_exists = Path(path + ".rotation").exists()
        self.assertEqual(len(live), 13)
        self.assertFalse(archive_exists)
        self.assertFalse(backup_exists)
        self.assertFalse(meta_exists)

    def test_keep_recent_without_path_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "run.jsonl")
            with self.assertRaises(ValueError):
                Agent(self_model=SelfModel()).run_task_logged(
                    "T3_navigate", 15, max_steps=200, log_path=log_path,
                    calibration_keep_recent=10)
            log_exists = Path(log_path).exists()
        self.assertFalse(log_exists)

    def test_invalid_keep_recent_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            for value in (0, -1, True, 1.5, "10"):
                log_path = os.path.join(tmp, "run-%s.jsonl" % str(value))
                with self.assertRaises(ValueError):
                    Agent(self_model=SelfModel()).run_task_logged(
                        "T3_navigate", 15, max_steps=200,
                        log_path=log_path, calibration_path=path,
                        calibration_keep_recent=value)
                self.assertFalse(Path(log_path).exists())
        self.assertFalse(Path(path).exists())

    def test_corrupt_archive_fails_after_verdict(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            Path(path + ".archive").write_text("{bad json\n",
                                               encoding="utf-8")
            log_path = os.path.join(tmp, "run.jsonl")
            with self.assertRaises(ValueError):
                Agent(self_model=SelfModel()).run_task_logged(
                    "T3_navigate", 15, max_steps=200, log_path=log_path,
                    calibration_path=path, calibration_keep_recent=10)
            live = load_forecasts(path)
            verdicts = [record for record in Telemetry(log_path).read_all()
                        if record["type"] == "verdict"]
        self.assertEqual(len(live), 13)
        self.assertEqual(len(verdicts), 1)
        self.assertEqual(verdicts[0]["verdict"], "done")
        self.assertIn("steps=13", verdicts[0]["reason"])

    def test_keep_one_is_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            _run(tmp, Agent(self_model=SelfModel()), "T3_navigate", 15,
                 "run", path, keep=1)
            live = load_forecasts(path)
            archive = load_forecasts(path + ".archive")
            combined = load_all_forecasts(path)
        self.assertEqual(len(live), 1)
        self.assertEqual(len(archive), 12)
        self.assertEqual(len(combined), 13)
        self.assertAlmostEqual(summary(combined, min_resolved=2)["brier"],
                               0.005385, places=6)

    def test_retained_actions_match_unretained(self):
        with tempfile.TemporaryDirectory() as tmp:
            retained, _ = _run(
                tmp, Agent(self_model=SelfModel()), "T3_navigate", 15,
                "retained", os.path.join(tmp, "retained-forecasts.jsonl"),
                keep=10)
            unretained, _ = _run(
                tmp, Agent(self_model=SelfModel()), "T3_navigate", 15,
                "unretained",
                os.path.join(tmp, "unretained-forecasts.jsonl"), keep=None)
        self.assertEqual([record["action"] for record in retained],
                         [record["action"] for record in unretained])
        self.assertEqual(len(retained), len(unretained))
        self.assertEqual(sum(record["reward"] for record in retained),
                         sum(record["reward"] for record in unretained))


if __name__ == "__main__":
    unittest.main()
