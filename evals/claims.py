"""Claim/verdict battery: kill tests over real T3 run outcomes.

Six claims are judged against T3:15 and T3:65: three should be supported,
two refuted and one inconclusive. The claim's declared confidence does
not decide the verdict; evidence does. Claims are immutable, verdict
history is ordered and the ledger roundtrips as JSON. The runs remain
13/6 steps with 1.0 reward.

The declared confidences are also scored as forecasts: ``calibration``
reports Brier and skill over the judged claims (``supported`` -> 1,
``refuted`` -> 0, ``inconclusive`` -> unresolved and excluded), so a
ledger cannot declare confidence and never hear whether it was right.
"""

import argparse
import json

from agent import Agent
from calibration import summary as cal_summary
from claims import ClaimLedger, claim_forecasts

STAMP = "2026-11-07T00:00:00Z"


def measure():
    trace15 = Agent().run_task("T3_navigate", 15)
    trace65 = Agent().run_task("T3_navigate", 65)
    actual = {
        "T3:15": {"steps": len(trace15),
                  "reward": sum(r["reward"] for r in trace15)},
        "T3:65": {"steps": len(trace65),
                  "reward": sum(r["reward"] for r in trace65)},
    }
    ledger = ClaimLedger()
    ledger.add("T3:15 completes in 13 steps", "steps != 13", 0.9)
    ledger.add("T3:65 completes in 13 steps", "steps != 13", 0.8)
    ledger.add("T3:15 reward is 1.0", "reward != 1.0", 0.95)
    ledger.add("T3:65 reward is 0.0", "reward != 0.0", 0.7)
    ledger.add("T3:65 completes in 6 steps", "steps != 6", 0.6)
    ledger.add("T3:15 energy is zero", "energy != 0", 0.5)

    checks = (
        ("C1", "T3:15", "steps", 13, "supports"),
        ("C2", "T3:65", "steps", 13, "refutes"),
        ("C3", "T3:15", "reward", 1.0, "supports"),
        ("C4", "T3:65", "reward", 0.0, "refutes"),
        ("C5", "T3:65", "steps", 6, "supports"),
    )
    for claim_id, run, field, expected, status in checks:
        observed = actual[run][field]
        verdict = "supports" if observed == expected else "refutes"
        if verdict != status:
            raise AssertionError("%s expected %s, got %s"
                                 % (claim_id, status, verdict))
        ledger.record(claim_id, status,
                      "%s %s=%r expected %r"
                      % (run, field, observed, expected), at=STAMP)
    ledger.record("C6", "inconclusive",
                  "no energy observation was recorded", at=STAMP)

    summary = ledger.summary()
    restored = ClaimLedger.from_dict(ledger.to_dict())
    return {
        "steps": [actual["T3:15"]["steps"], actual["T3:65"]["steps"]],
        "rewards": [actual["T3:15"]["reward"], actual["T3:65"]["reward"]],
        "summary": summary,
        "calibration": cal_summary(claim_forecasts(ledger), min_resolved=1),
        "claims": [
            {"id": claim.id, "confidence": claim.confidence,
             "status": claim.status,
             "verdicts": [verdict.status for verdict in claim.verdicts]}
            for claim in ledger.claims()
        ],
        "roundtrip": restored.claims() == ledger.claims(),
    }


def run_battery():
    return {"model": "rule", "cases": [measure()]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", default=True)
    parser.parse_args()
    print(json.dumps(run_battery(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
