"""Immutable claims, kill tests and verdict history (research-engine transfer).

Adapted from ``research-engine/engine/claims.py`` and its verdict
records. A claim carries an id, text, kill test, declared confidence and
status. ``record_verdict`` appends a supports/refutes/inconclusive
verdict and returns a new claim; the previous record is never mutated.
The ledger is in-memory and JSON-roundtrippable; persistence is left to
the caller. A verdict may carry an optional ``ref`` (for example the
episode digest of the logged run that produced the evidence).
"""

import time
from dataclasses import asdict, dataclass, field, replace

CLAIM_STATUSES = ("proposed", "supported", "refuted", "inconclusive")
VERDICT_STATUSES = ("supports", "refutes", "inconclusive")
_VERDICT_TO_CLAIM = {
    "supports": "supported",
    "refutes": "refuted",
    "inconclusive": "inconclusive",
}


def _stamp():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


@dataclass(frozen=True)
class Verdict:
    status: str
    evidence: str
    at: str
    ref: str = None

    def __post_init__(self):
        if self.status not in VERDICT_STATUSES:
            raise ValueError("Why: unknown verdict status %r. Fix: use %s."
                             % (self.status, VERDICT_STATUSES))
        _validate_text(self.evidence, "verdict evidence")
        _validate_text(self.at, "verdict at")
        _validate_ref(self.ref)


def _validate_ref(value):
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            "Why: verdict ref must be a non-empty string or None. "
            "Fix: pass the episode/run digest or omit ref.")
    return value


@dataclass(frozen=True)
class Claim:
    id: str
    text: str
    kill_test: str
    status: str = "proposed"
    confidence: float = 0.5
    verdicts: tuple = field(default_factory=tuple)

    def __post_init__(self):
        _validate_claim(self)


def _validate_text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Why: claim %s must be a non-empty string. "
                         "Fix: pass the claim text/kill test." % name)
    return value


def _validate_confidence(value):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not 0.0 <= float(value) <= 1.0):
        raise ValueError("Why: confidence must be in [0, 1]. "
                         "Fix: pass confidence=0.5.")
    return float(value)


def _validate_claim(claim):
    _validate_text(claim.id, "id")
    _validate_text(claim.text, "text")
    _validate_text(claim.kill_test, "kill_test")
    if claim.status not in CLAIM_STATUSES:
        raise ValueError("Why: unknown claim status %r. Fix: use one of %s."
                         % (claim.status, CLAIM_STATUSES))
    _validate_confidence(claim.confidence)
    for verdict in claim.verdicts:
        if not isinstance(verdict, Verdict):
            raise ValueError("verdicts must be Verdict records")
        if verdict.status not in VERDICT_STATUSES:
            raise ValueError("unknown verdict status %r" % verdict.status)
        _validate_text(verdict.evidence, "verdict evidence")
        _validate_text(verdict.at, "verdict at")
        _validate_ref(verdict.ref)
    expected = ("proposed" if not claim.verdicts
                else _VERDICT_TO_CLAIM[claim.verdicts[-1].status])
    if claim.status != expected:
        raise ValueError(
            "Why: claim status %r does not match its verdict history (%r). "
            "Fix: load a consistent snapshot or rebuild the claim."
            % (claim.status, expected))
    return claim


def record_verdict(claim, status, evidence, at=None, ref=None):
    """Return a new Claim with the verdict appended and status updated."""
    if status not in VERDICT_STATUSES:
        raise ValueError("Why: unknown verdict status %r. Fix: use %s."
                         % (status, VERDICT_STATUSES))
    evidence = _validate_text(evidence, "evidence")
    ref = _validate_ref(ref)
    stamp = at if isinstance(at, str) and at else _stamp()
    verdict = Verdict(status=status, evidence=evidence, at=stamp, ref=ref)
    return replace(claim, status=_VERDICT_TO_CLAIM[status],
                   verdicts=tuple(claim.verdicts) + (verdict,))


#: Claim status -> the forecast outcome it resolves to. ``None`` means the
#: claim was judged but its truth value is undecided, so a scorer must
#: ignore it rather than guess.
_STATUS_OUTCOME = {
    "proposed": None,
    "supported": 1,
    "refuted": 0,
    "inconclusive": None,
}


def claim_forecasts(ledger):
    """Return one forecast record per judged claim, for calibration scoring.

    A claim's ``confidence`` is a declared probability that the claim holds,
    the same kind of forecast ``calibration.summary`` scores. A ``proposed``
    claim has no verdict, so it is excluded; a ``supported`` verdict maps to
    outcome 1 and ``refuted`` to 0; an ``inconclusive`` verdict is kept with
    ``outcome=None`` so the scorer ignores it and reports it as uncovered.

    The ledger is read, never mutated.
    """
    forecasts = []
    for claim in ledger.claims():
        if claim.status == "proposed":
            continue
        forecasts.append({
            "id": claim.id,
            "probability": claim.confidence,
            "outcome": _STATUS_OUTCOME[claim.status],
        })
    return forecasts


class ClaimLedger:
    """Ordered in-memory claims with append-only verdict history."""

    def __init__(self, claims=None):
        self._claims = []
        for claim in claims or []:
            self._insert(claim)

    def _insert(self, claim):
        _validate_claim(claim)
        if any(existing.id == claim.id for existing in self._claims):
            raise ValueError("duplicate claim id %r" % claim.id)
        self._claims.append(claim)
        return claim

    def add(self, text, kill_test, confidence=0.5, claim_id=None):
        """Create a proposed claim and return it."""
        text = _validate_text(text, "text")
        kill_test = _validate_text(kill_test, "kill_test")
        confidence = _validate_confidence(confidence)
        if claim_id is None:
            used = {claim.id for claim in self._claims}
            index = 1
            while "C%d" % index in used:
                index += 1
            claim_id = "C%d" % index
        claim = Claim(id=str(claim_id), text=text, kill_test=kill_test,
                      confidence=confidence)
        return self._insert(claim)

    def get(self, claim_id):
        for claim in self._claims:
            if claim.id == claim_id:
                return claim
        raise ValueError("unknown claim id %r" % claim_id)

    def record(self, claim_id, status, evidence, at=None, ref=None):
        """Append a verdict to one claim and return the updated claim."""
        claim = self.get(claim_id)
        updated = record_verdict(claim, status, evidence, at=at, ref=ref)
        for index, existing in enumerate(self._claims):
            if existing.id == claim_id:
                self._claims[index] = updated
                break
        return updated

    def claims(self):
        return tuple(self._claims)

    def summary(self):
        statuses = {status: 0 for status in CLAIM_STATUSES}
        verdicts = 0
        with_verdicts = 0
        for claim in self._claims:
            statuses[claim.status] += 1
            verdicts += len(claim.verdicts)
            if claim.verdicts:
                with_verdicts += 1
        return {
            "claims": len(self._claims),
            "statuses": statuses,
            "verdicts": verdicts,
            "with_verdicts": with_verdicts,
            "without_verdicts": len(self._claims) - with_verdicts,
        }

    def to_dict(self):
        claims = []
        for claim in self._claims:
            value = asdict(claim)
            value["verdicts"] = [dict(item) for item in value["verdicts"]]
            claims.append(value)
        return {"claims": claims}

    @classmethod
    def from_dict(cls, payload):
        if not isinstance(payload, dict) or not isinstance(payload.get("claims"), list):
            raise ValueError("payload must contain a claims list")
        ledger = cls()
        for raw in payload["claims"]:
            if not isinstance(raw, dict):
                raise ValueError("each claim must be an object")
            raw_verdicts = raw.get("verdicts") or []
            if not isinstance(raw_verdicts, (list, tuple)):
                raise ValueError("verdicts must be a list")
            verdicts = tuple(
                Verdict(status=item.get("status"), evidence=item.get("evidence"),
                        at=item.get("at"), ref=item.get("ref"))
                for item in raw_verdicts
                if isinstance(item, dict)
            )
            if len(verdicts) != len(raw_verdicts):
                raise ValueError("each verdict must be an object")
            claim = Claim(
                id=str(raw.get("id", "")),
                text=raw.get("text", ""),
                kill_test=raw.get("kill_test", ""),
                status=raw.get("status", "proposed"),
                confidence=raw.get("confidence", 0.5),
                verdicts=verdicts,
            )
            ledger._insert(claim)
        return ledger
