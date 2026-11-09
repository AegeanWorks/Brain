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
from evals.battery_check import exit_code_for, format_findings
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


#: Exact ``(brier, skill)`` each fixture must produce. Five fixtures are
#: built by construction (a perfect forecaster scores 0 and skill 1, an
#: inverted one scores 1 and skill -3); the sixth is the real T3:15
#: self-model readout. Pinning them makes a scorer change fail the battery.
#:
#: ``run-T3-15`` was re-baselined in ADR-140 from ``(0.230769, -2.25)`` to
#: ``(0.005385, 0.924167)`` when the agent began recording a confidence
#: formed before the action instead of ``1.0 if reward > 0 else 0.5``.
EXPECTED = {
    "perfect": (0.0, 1.0),
    "calibrated": (0.166, 0.308333),
    "inverted": (1.0, -3.0),
    "small": (0.0, None),
    "ignored": (0.04, 0.84),
    "run-T3-15": (0.005385, 0.924167),
}


def checks(report):
    """Return the claims this battery's own output contradicts.

    The fixtures are exact by construction, so a moved score is a scorer
    regression, not noise.
    """
    findings = []
    by_mode = {case.get("mode"): case for case in report.get("cases", [])}
    for mode, (brier, skill) in EXPECTED.items():
        case = by_mode.get(mode)
        if case is None:
            findings.append("missing-mode:%s" % mode)
            continue
        stats = case.get("stats") or {}
        got_brier = stats.get("brier")
        if got_brier is None or abs(float(got_brier) - brier) > 1e-6:
            findings.append("brier:%s:%s!=%s" % (mode, got_brier, brier))
        got_skill = stats.get("skill")
        if skill is None:
            if got_skill is not None:
                findings.append("skill:%s:%s!=None" % (mode, got_skill))
        elif got_skill is None or abs(float(got_skill) - skill) > 1e-6:
            findings.append("skill:%s:%s!=%s" % (mode, got_skill, skill))
    for mode in ("small", "inverted"):
        case = by_mode.get(mode)
        if case is not None and not (case.get("stats") or {}).get("warnings"):
            findings.append("no-warning:%s" % mode)
    run = by_mode.get("run-T3-15")
    if run is not None:
        if run.get("steps") != 13:
            findings.append("run-steps:%s!=13" % run.get("steps"))
        if run.get("reward") != 1.0:
            findings.append("run-reward:%s!=1.0" % run.get("reward"))
        resolved = (run.get("stats") or {}).get("counts", {}).get("resolved")
        if resolved != 13:
            findings.append("run-resolved:%s!=13" % resolved)
    return findings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", default=True)
    parser.parse_args()
    report = run_battery()
    print(json.dumps(report, indent=2, sort_keys=True))
    findings = checks(report)
    if findings:
        print(format_findings("calibration", findings), end="")
    raise SystemExit(exit_code_for(findings))


if __name__ == "__main__":
    main()
