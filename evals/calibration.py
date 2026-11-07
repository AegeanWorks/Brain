"""Calibration battery: proper scores over fixtures and a real run.

Perfect forecasts score Brier 0 and skill 1; inverted forecasts score
Brier 1 and negative skill; a calibrated fixture sits between; small and
ignored-outcome sets warn and adjust coverage. A real T3:15 run with the
persistent SelfModel keeps 13 steps / 1.0 and exposes its confidence/
outcome calibration readout without changing actions.
"""

import argparse
import json

from agent import Agent
from calibration import summary
from self_model.model import SelfModel


def _forecast(identifier, probability, outcome):
    return {"id": str(identifier), "probability": probability,
            "outcome": outcome}


def _perfect():
    return [_forecast(index, 1.0 if index < 5 else 0.0,
                      1 if index < 5 else 0) for index in range(10)]


def _inverted():
    return [_forecast(index, 1.0 if index >= 5 else 0.0,
                      1 if index < 5 else 0) for index in range(10)]


def _calibrated():
    return [
        _forecast(0, 0.9, 1), _forecast(1, 0.8, 1),
        _forecast(2, 0.7, 0), _forecast(3, 0.6, 1),
        _forecast(4, 0.5, 0), _forecast(5, 0.4, 0),
        _forecast(6, 0.3, 1), _forecast(7, 0.2, 0),
        _forecast(8, 0.1, 0), _forecast(9, 0.1, 0),
    ]


def _compact(stats):
    return {
        "counts": stats["counts"],
        "coverage": stats["coverage"],
        "brier": stats["brier"],
        "log_loss": stats["log_loss"],
        "base_rate": stats["base_rate"],
        "skill": stats["skill"],
        "bins": stats["bins"],
        "warnings": stats["warnings"],
    }


def _fixture_case(name, forecasts, min_resolved=10):
    return {"mode": name, "stats": _compact(
        summary(forecasts, min_resolved=min_resolved))}


def measure_run():
    model = SelfModel()
    trace = Agent(self_model=model).run_task("T3_navigate", 15)
    stats = model.calibration(min_resolved=2)
    return {
        "mode": "run-T3-15",
        "steps": len(trace),
        "reward": sum(record["reward"] for record in trace),
        "success": bool(trace[-1]["done"]) and sum(
            record["reward"] for record in trace) > 0.0,
        "stats": _compact(stats),
    }


def run_battery():
    return {
        "model": "rule",
        "cases": [
            _fixture_case("perfect", _perfect()),
            _fixture_case("calibrated", _calibrated()),
            _fixture_case("inverted", _inverted()),
            _fixture_case("small", _perfect()[:3]),
            _fixture_case("ignored", [
                _forecast(0, 0.8, 1), _forecast(1, 0.2, 0),
                _forecast(2, 0.5, None)]),
            measure_run(),
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", default=True)
    parser.parse_args()
    print(json.dumps(run_battery(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
