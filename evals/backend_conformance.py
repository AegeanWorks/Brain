"""Backend conformance battery: the seam is checkable without reading code.

A pluggable provider seam is only worth having if a *new* provider can be
validated. This battery runs the contract over the shipped providers and
over three deliberately broken controls, so the check itself is shown to
discriminate rather than rubber-stamp.

The controls are the point:

    conforming        identity declared, deterministic, legal token  -> ok
    alternating       same input, different output                  -> non-deterministic
    class-identity    never declared an identity                    -> identity-from-class-name
    returns-none      no proposal at all                            -> no-proposal

Nothing here needs a network or a model file. `llamacpp` is registered but
is only checked for its *identity*, since constructing it would need a
server binary; a provider backed by a live model should be checked through a
replay transport, because temperature and batching make byte-identical
output across processes false in practice.
"""

import argparse
import json

from models.backend import ModelBackend, StubBackend
from models.conformance import check_backend, format_findings
from models.registry import names

OBS = {"task": "T3_navigate", "x": 0, "y": 0, "steps": 0,
       "legal": ["up", "down", "left", "right", "wait"]}

#: Exact conformance outcome for each control, pinned so a change to the
#: contract fails the battery instead of silently widening the seam.
EXPECTED = {
    "conforming": True,
    "alternating": False,
    "class-identity": False,
    "returns-none": False,
}


class Conforming(ModelBackend):
    def identity(self):
        return "control:conforming"

    def generate(self, observation):
        return (observation.get("legal") or ["wait"])[-1]


class Alternating(ModelBackend):
    def __init__(self):
        self._n = 0

    def identity(self):
        return "control:alternating"

    def generate(self, observation):
        self._n += 1
        legal = observation.get("legal") or ["wait"]
        return legal[self._n % len(legal)]


class ClassIdentity(ModelBackend):
    def generate(self, observation):
        return "wait"


class ReturnsNone(ModelBackend):
    def identity(self):
        return "control:returns-none"

    def generate(self, observation):
        return None


CONTROLS = {
    "conforming": Conforming,
    "alternating": Alternating,
    "class-identity": ClassIdentity,
    "returns-none": ReturnsNone,
}


def measure():
    """Run the contract over every control and the shipped registry."""
    cases = []
    for name, provider in CONTROLS.items():
        report = check_backend(provider, OBS)
        cases.append({
            "subject": name,
            "ok": report["ok"],
            "identity": report["identity"],
            "deterministic": report["deterministic"],
            "findings": report["findings"],
            "line": format_findings(report),
        })

    stub = check_backend(StubBackend(["wait", "wait", "wait"]), OBS)
    cases.append({
        "subject": "stub",
        "ok": stub["ok"],
        "identity": stub["identity"],
        "deterministic": stub["deterministic"],
        "findings": stub["findings"],
        "line": format_findings(stub),
    })
    return {"cases": cases, "registered": names()}


def checks(report):
    """Return the claims this battery's own output contradicts."""
    findings = []
    by_subject = {case["subject"]: case for case in report["cases"]}
    for subject, expected_ok in EXPECTED.items():
        if subject not in by_subject:
            findings.append("missing:%s" % subject)
            continue
        if by_subject[subject]["ok"] is not expected_ok:
            findings.append("ok:%s:%s!=%s"
                            % (subject, by_subject[subject]["ok"],
                               expected_ok))
    for required in ("stub", "llamacpp"):
        if required not in report["registered"]:
            findings.append("unregistered:%s" % required)
    if not by_subject.get("conforming", {}).get("deterministic"):
        findings.append("conforming-not-deterministic")
    if by_subject.get("alternating", {}).get("deterministic") is not False:
        findings.append("alternating-not-flagged")
    return findings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", default=True)
    parser.parse_args()
    report = measure()
    problems = checks(report)
    payload = dict(report, findings=problems, ok=not problems)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
