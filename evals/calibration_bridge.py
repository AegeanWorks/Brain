"""Calibration bridge battery: logged runs persist their own forecasts.

A default run keeps 13 forecasts in memory and writes no journal. A
logged run with ``calibration_path`` persists exactly those 13 under the
header-digest prefix; a second run on the same self-model appends only
its 6 new forecasts (19 total, two prefixes). Missing self-models and a
corrupt journal fail loudly; actions and rewards stay identical.
"""

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

from agent import Agent
from calibration import summary
from calibration_store import load_forecasts, verify_forecast_file
from self_model.model import SelfModel
from telemetry.log import Telemetry

MODES = ("default", "logged", "two-runs", "keyed", "missing-self-model",
         "corrupt-store", "actions")


def _run(agent, task, seed, tmp, name, calibration_path=None,
         hmac_key=None):
    log_path = os.path.join(tmp, name + ".jsonl")
    trace = agent.run_task_logged(task, seed, max_steps=200,
                                  log_path=log_path,
                                  calibration_path=calibration_path,
                                  calibration_hmac_key=hmac_key)
    return trace, log_path


def _stats(records, min_resolved=2):
    stats = summary(records, min_resolved=min_resolved)
    return {
        "records": len(records),
        "resolved": stats["counts"]["resolved"],
        "brier": stats["brier"],
        "skill": stats["skill"],
    }


def measure_case(mode="logged", directory=None):
    if directory is None:
        raise ValueError("directory is required")
    path = os.path.join(directory, "forecasts-%s.jsonl" % mode)
    result = {"mode": mode, "steps": 0, "reward": 0.0, "records": 0,
              "resolved": 0, "brier": None, "skill": None,
              "in_memory_resolved": None, "in_memory_brier": None,
              "file_before": False, "file_after": False,
              "prefixes": 0, "unique_ids": None, "log_verdict": None,
              "actions_match": None, "hmac": None, "error": None}
    if mode == "keyed":
        key = hashlib.sha256(b"bridge-eval-key").digest()
        wrong = hashlib.sha256(b"bridge-eval-wrong").digest()
        model = SelfModel()
        trace, _log = _run(Agent(self_model=model), "T3_navigate", 15,
                           directory, "keyed", path, key)
        records = load_forecasts(path, hmac_key=key)
        verified = verify_forecast_file(path, hmac_key=key)
        try:
            load_forecasts(path, hmac_key=wrong)
        except ValueError as exc:
            result["error"] = str(exc)
        result.update(_stats(records))
        result.update({"steps": len(trace),
                       "reward": sum(r["reward"] for r in trace),
                       "in_memory_resolved": model.calibration(
                           min_resolved=2)["counts"]["resolved"],
                       "in_memory_brier": model.calibration(
                           min_resolved=2)["brier"],
                       "hmac": verified["hmac"],
                       "file_after": Path(path).exists()})
        return result
    if mode == "missing-self-model":
        log_path = os.path.join(directory, "missing.jsonl")
        try:
            Agent().run_task_logged("T3_navigate", 15, max_steps=200,
                                    log_path=log_path,
                                    calibration_path=path)
        except ValueError as exc:
            result["error"] = str(exc)
        result["file_after"] = Path(path).exists()
        result["log_verdict"] = Path(log_path).exists()
        return result
    if mode == "corrupt-store":
        Path(path).write_text("{bad json\n", encoding="utf-8")
        log_path = os.path.join(directory, "corrupt.jsonl")
        try:
            Agent(self_model=SelfModel()).run_task_logged(
                "T3_navigate", 15, max_steps=200, log_path=log_path,
                calibration_path=path)
        except ValueError as exc:
            result["error"] = str(exc)
        verdicts = [record for record in Telemetry(log_path).read_all()
                    if record["type"] == "verdict"]
        if verdicts:
            result["log_verdict"] = verdicts[-1]["verdict"]
        result["file_after"] = Path(path).exists()
        return result
    if mode == "actions":
        model = SelfModel()
        plain, _ = _run(Agent(self_model=model), "T3_navigate", 15,
                        directory, "actions-plain")
        model = SelfModel()
        logged, _ = _run(Agent(self_model=model), "T3_navigate", 15,
                         directory, "actions-logged", path)
        result.update({"steps": len(plain),
                       "reward": sum(r["reward"] for r in plain),
                       "actions_match": [r["action"] for r in plain]
                       == [r["action"] for r in logged]})
        return result
    model = SelfModel()
    agent = Agent(self_model=model)
    calibration_path = None if mode == "default" else path
    result["file_before"] = Path(path).exists()
    first, log1 = _run(agent, "T3_navigate", 15, directory,
                       "run1-" + mode, calibration_path)
    result.update({"steps": len(first),
                   "reward": sum(r["reward"] for r in first),
                   "in_memory_resolved": model.calibration(
                       min_resolved=2)["counts"]["resolved"],
                   "in_memory_brier": model.calibration(
                       min_resolved=2)["brier"]})
    if mode == "two-runs":
        second, log2 = _run(agent, "T3_navigate", 65, directory,
                            "run2-" + mode, calibration_path)
        result["second_steps"] = len(second)
        result["second_reward"] = sum(r["reward"] for r in second)
        result["log2_prefix"] = Telemetry(log2).read_all()[0]["digest"][:12]
    records = load_forecasts(path) if calibration_path is not None else []
    verified = (verify_forecast_file(path)
                if calibration_path is not None else {"ok": True})
    result.update(_stats(records))
    result.update({
        "file_after": Path(path).exists() if calibration_path else False,
        "prefixes": len({record["id"].rsplit(":", 1)[0]
                         for record in records}),
        "unique_ids": len({record["id"] for record in records}
                          ) == len(records),
    })
    if mode in ("logged", "two-runs"):
        header = Telemetry(log1).read_all()[0]
        result["log_prefix"] = header["digest"][:12]
        result["prefix_matches"] = all(
            record["id"].startswith(header["digest"][:12] + ":")
            for record in records[:result["steps"]])
        result["verified"] = verified["ok"]
    if mode == "two-runs":
        result["second_prefix_matches"] = all(
            record["id"].startswith(result["log2_prefix"] + ":")
            for record in records[result["steps"]:])
    return result


def run_battery(modes=MODES):
    with tempfile.TemporaryDirectory() as directory:
        return {"model": "rule", "modes": list(modes),
                "cases": [measure_case(mode, directory)
                          for mode in modes]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", action="append", choices=MODES, default=[],
                        help="repeatable (default: all modes)")
    args = parser.parse_args()
    modes = tuple(args.mode) if args.mode else MODES
    print(json.dumps(run_battery(modes), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
