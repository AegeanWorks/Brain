"""SelfModel forecast bridge: logged runs persist their own forecasts.

Failing-first: `SelfModel` records confidence/outcome pairs and
`calibration_store` can persist forecasts, but nothing connects them. A
logged run with `calibration_path` must append only the forecasts from
that run, under a header-derived unique id prefix, after the verdict.
The bridge is opt-in and must not change actions or rewards.
"""

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from agent import Agent
from calibration import summary
from calibration_store import load_forecasts, verify_forecast_file
from self_model.model import SelfModel
from telemetry.log import Telemetry


def _run(tmp, task="T3_navigate", seed=15, calibration_path=None,
         agent=None, log_name=None):
    log_path = os.path.join(tmp, log_name or ("%s-%d.jsonl" % (task, seed)))
    agent = agent if agent is not None else Agent(self_model=SelfModel())
    trace = agent.run_task_logged(task, seed, max_steps=200,
                                  log_path=log_path,
                                  calibration_path=calibration_path)
    return agent, trace, log_path


class TestCalibrationBridge(unittest.TestCase):
    def test_selfmodel_forecasts_prefix_and_slice(self):
        model = SelfModel()
        model.record(1.0, True, 1.0)
        model.record(1.0, False, 0.5)
        self.assertEqual(model.forecast_count(), 2)
        forecasts = model.forecasts("run")
        self.assertEqual([item["id"] for item in forecasts],
                         ["run:0", "run:1"])
        self.assertEqual([item["probability"] for item in forecasts],
                         [1.0, 0.5])
        self.assertEqual([item["outcome"] for item in forecasts], [1, 0])
        sliced = model.forecasts("run", start=1)
        self.assertEqual([item["id"] for item in sliced], ["run:1"])

    def test_logged_run_persists_only_this_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            model = SelfModel()
            agent = Agent(self_model=model)
            _, first, log1 = _run(tmp, "T3_navigate", 15, path, agent,
                                  "first.jsonl")
            _, second, log2 = _run(tmp, "T3_navigate", 65, path, agent,
                                   "second.jsonl")
            records = load_forecasts(path)
            verified = verify_forecast_file(path)
            header1 = Telemetry(log1).read_all()[0]
            header2 = Telemetry(log2).read_all()[0]
            ids = [record["id"] for record in records]
            prefixes = {identifier.rsplit(":", 1)[0] for identifier in ids}
        self.assertEqual(len(first), 13)
        self.assertEqual(len(second), 6)
        self.assertEqual(len(records), 19)
        self.assertEqual(verified["records"], 19)
        self.assertEqual(verified["resolved"], 19)
        self.assertEqual(len(set(ids)), 19)
        self.assertEqual(len(prefixes), 2)
        self.assertNotEqual(header1["digest"][:12], header2["digest"][:12])
        self.assertTrue(all(identifier.startswith(
            header1["digest"][:12] + ":") for identifier in ids[:13]))
        self.assertTrue(all(identifier.startswith(
            header2["digest"][:12] + ":") for identifier in ids[13:]))

    def test_logged_summary_matches_in_memory(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            model = SelfModel()
            _, trace, _ = _run(tmp, "T3_navigate", 15, path,
                               Agent(self_model=model))
            records = load_forecasts(path)
            persisted = summary(records, min_resolved=2)
            memory = model.calibration(min_resolved=2)
        self.assertEqual(len(trace), 13)
        self.assertEqual(sum(record["reward"] for record in trace), 1.0)
        self.assertEqual(persisted["counts"]["resolved"], 13)
        self.assertEqual(persisted["counts"]["resolved"],
                         memory["counts"]["resolved"])
        self.assertAlmostEqual(persisted["brier"], 0.230769, places=6)
        self.assertAlmostEqual(persisted["brier"], memory["brier"], places=6)

    def test_keyed_bridge_roundtrip_and_wrong_key(self):
        key = hashlib.sha256(b"bridge-key").digest()
        wrong = hashlib.sha256(b"bridge-wrong").digest()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            log_path = os.path.join(tmp, "run.jsonl")
            trace = Agent(self_model=SelfModel()).run_task_logged(
                "T3_navigate", 15, max_steps=200, log_path=log_path,
                calibration_path=path, calibration_hmac_key=key)
            records = load_forecasts(path, hmac_key=key)
            verified = verify_forecast_file(path, hmac_key=key)
            with self.assertRaises(ValueError):
                load_forecasts(path, hmac_key=wrong)
        self.assertEqual(len(trace), 13)
        self.assertEqual(len(records), 13)
        self.assertTrue(verified["ok"], verified["findings"])
        self.assertTrue(verified["hmac"])

    def test_keyed_bridge_requires_a_path(self):
        key = hashlib.sha256(b"bridge-key").digest()
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "run.jsonl")
            with self.assertRaises(ValueError):
                Agent(self_model=SelfModel()).run_task_logged(
                    "T3_navigate", 15, max_steps=200, log_path=log_path,
                    calibration_hmac_key=key)
            log_exists = Path(log_path).exists()
        self.assertFalse(log_exists)

    def test_invalid_bridge_key_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            for value in ("text", b"", 3):
                log_path = os.path.join(tmp, "run-%s.jsonl" % str(value))
                with self.assertRaises(ValueError):
                    Agent(self_model=SelfModel()).run_task_logged(
                        "T3_navigate", 15, max_steps=200,
                        log_path=log_path, calibration_path=path,
                        calibration_hmac_key=value)
                self.assertFalse(Path(log_path).exists())
        self.assertFalse(Path(path).exists())

    def test_default_none_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            model = SelfModel()
            _, trace, _ = _run(tmp, "T3_navigate", 15, None,
                               Agent(self_model=model))
            exists = Path(path).exists()
            loaded = load_forecasts(path)
        self.assertEqual(len(trace), 13)
        self.assertEqual(model.forecast_count(), 13)
        self.assertFalse(exists)
        self.assertEqual(loaded, [])

    def test_bridge_requires_a_self_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            log_path = os.path.join(tmp, "run.jsonl")
            with self.assertRaises(ValueError):
                Agent().run_task_logged("T3_navigate", 15, max_steps=200,
                                        log_path=log_path,
                                        calibration_path=path)
            log_exists = Path(log_path).exists()
            store_exists = Path(path).exists()
        self.assertFalse(log_exists)
        self.assertFalse(store_exists)

    def test_bridge_requires_forecast_api(self):
        class MinimalModel:
            def snapshot(self):
                return {}

            def record(self, cost, ok, conf):
                return {}

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            log_path = os.path.join(tmp, "run.jsonl")
            with self.assertRaises(ValueError):
                Agent(self_model=MinimalModel()).run_task_logged(
                    "T3_navigate", 15, max_steps=200, log_path=log_path,
                    calibration_path=path)
            log_exists = Path(log_path).exists()
        self.assertFalse(log_exists)

    def test_append_failure_surfaces_after_verdict(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            Path(path).write_text("{bad json\n", encoding="utf-8")
            log_path = os.path.join(tmp, "run.jsonl")
            with self.assertRaises(ValueError):
                Agent(self_model=SelfModel()).run_task_logged(
                    "T3_navigate", 15, max_steps=200, log_path=log_path,
                    calibration_path=path)
            records = Telemetry(log_path).read_all()
            verdicts = [record for record in records
                        if record["type"] == "verdict"]
        self.assertEqual(len(verdicts), 1)
        self.assertEqual(verdicts[0]["verdict"], "done")
        self.assertIn("steps=13", verdicts[0]["reason"])

    def test_bridge_does_not_change_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, plain, _ = _run(tmp, "T3_navigate", 15, None, log_name="plain")
            _, logged, _ = _run(tmp, "T3_navigate", 15,
                                os.path.join(tmp, "forecasts.jsonl"),
                                log_name="logged")
        self.assertEqual([record["action"] for record in plain],
                         [record["action"] for record in logged])
        self.assertEqual(len(plain), len(logged))
        self.assertEqual(sum(record["reward"] for record in plain),
                         sum(record["reward"] for record in logged))


if __name__ == "__main__":
    unittest.main()
