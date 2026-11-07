"""Automatic calibration-retention battery at the logged-run bridge.

A T3:15 run with calibration_keep_recent=10 appends 13 forecasts and
rotates to 10 live/3 archived/13 total with Brier 0.230769. A second
T3:65 run extends the archive to 9 and the total to 19 (Brier 0.223684).
Without the threshold all 13 stay live. Missing/invalid requests fail
before the run; a corrupt archive fails after a done verdict with the
13 forecasts still live.
"""

import argparse
import json
import os
import tempfile
from pathlib import Path

from agent import Agent
from calibration import summary
from calibration_store import load_all_forecasts, load_forecasts
from self_model.model import SelfModel
from telemetry.log import Telemetry

MODES = ("retained", "retained-two-runs", "unretained", "missing-path",
         "invalid", "corrupt-archive", "actions")


def _run(tmp, agent, task, seed, name, calibration_path, keep=None):
    log_path = os.path.join(tmp, name + ".jsonl")
    trace = agent.run_task_logged(
        task, seed, max_steps=200, log_path=log_path,
        calibration_path=calibration_path,
        calibration_keep_recent=keep)
    return trace, log_path


def _stats(records):
    stats = summary(records, min_resolved=2)
    return {"brier": stats["brier"], "skill": stats["skill"],
            "resolved": stats["counts"]["resolved"]}


def _combined(path):
    live = load_forecasts(path)
    archive_path = path + ".archive"
    archive = (load_forecasts(archive_path)
               if Path(archive_path).exists() else [])
    combined = load_all_forecasts(path)
    return live, archive, combined


def measure_case(mode="retained", directory=None):
    if directory is None:
        raise ValueError("directory is required")
    path = os.path.join(directory, "forecasts-%s.jsonl" % mode)
    result = {"mode": mode, "steps": 0, "reward": 0.0, "live": 0,
              "archive": 0, "total": 0, "brier": None, "skill": None,
              "resolved": 0, "backup": None, "metadata": False,
              "prefixes": 0, "unique": None, "verdict": None,
              "actions_match": None, "error": None}
    if mode == "missing-path":
        log_path = os.path.join(directory, "missing-path.jsonl")
        try:
            Agent(self_model=SelfModel()).run_task_logged(
                "T3_navigate", 15, max_steps=200, log_path=log_path,
                calibration_keep_recent=10)
        except ValueError as exc:
            result["error"] = str(exc)
        result["verdict"] = Path(log_path).exists()
        return result
    if mode == "invalid":
        log_path = os.path.join(directory, "invalid.jsonl")
        try:
            Agent(self_model=SelfModel()).run_task_logged(
                "T3_navigate", 15, max_steps=200, log_path=log_path,
                calibration_path=path, calibration_keep_recent=0)
        except ValueError as exc:
            result["error"] = str(exc)
        result["verdict"] = Path(log_path).exists()
        return result
    if mode == "corrupt-archive":
        Path(path + ".archive").write_text("{bad json\n", encoding="utf-8")
        log_path = os.path.join(directory, "corrupt.jsonl")
        try:
            Agent(self_model=SelfModel()).run_task_logged(
                "T3_navigate", 15, max_steps=200, log_path=log_path,
                calibration_path=path, calibration_keep_recent=10)
        except ValueError as exc:
            result["error"] = str(exc)
        verdicts = [record for record in Telemetry(log_path).read_all()
                    if record["type"] == "verdict"]
        if verdicts:
            result["verdict"] = verdicts[-1]["verdict"]
        result["live"] = len(load_forecasts(path))
        return result
    if mode == "actions":
        retained, _ = _run(
            directory, Agent(self_model=SelfModel()), "T3_navigate", 15,
            "actions-retained",
            os.path.join(directory, "actions-retained-forecasts.jsonl"),
            keep=10)
        unretained, _ = _run(
            directory, Agent(self_model=SelfModel()), "T3_navigate", 15,
            "actions-unretained",
            os.path.join(directory, "actions-unretained-forecasts.jsonl"),
            keep=None)
        result.update({"steps": len(retained),
                       "reward": sum(r["reward"] for r in retained),
                       "actions_match": [r["action"] for r in retained]
                       == [r["action"] for r in unretained]})
        return result
    agent = Agent(self_model=SelfModel())
    keep = None if mode == "unretained" else 10
    trace, _ = _run(directory, agent, "T3_navigate", 15, "run1-" + mode,
                    path, keep)
    result.update({"steps": len(trace),
                   "reward": sum(r["reward"] for r in trace)})
    if mode == "retained-two-runs":
        second, _ = _run(directory, agent, "T3_navigate", 65,
                         "run2-" + mode, path, keep)
        result["second_steps"] = len(second)
        result["second_reward"] = sum(r["reward"] for r in second)
    live, archive, combined = _combined(path)
    stats = _stats(combined)
    result.update({"live": len(live), "archive": len(archive),
                   "total": len(combined), "brier": stats["brier"],
                   "skill": stats["skill"], "resolved": stats["resolved"],
                   "backup": (len(load_forecasts(path + ".bak"))
                              if Path(path + ".bak").exists() else None),
                   "metadata": Path(path + ".rotation").exists(),
                   "prefixes": len({r["id"].rsplit(":", 1)[0]
                                    for r in combined}),
                   "unique": len({r["id"] for r in combined}
                                 ) == len(combined)})
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
