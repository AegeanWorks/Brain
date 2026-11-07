"""Forecast calibration: Brier, log loss, skill and reliability bins.

Adapted from ``research-engine/engine/calibration.py`` (AegeanWorks/
Research Engine). Forecasts are ``{"id", "probability", "outcome"}``
mappings; ``outcome`` may be ``None`` for unresolved items. Brier and
log loss are proper scoring rules over probabilities recorded before the
outcome. They describe this run's forecasting record; they are not a
posterior and never change a policy. Small resolved sets are reported as
descriptive rather than decisive.
"""

import math

MIN_RESOLVED = 10
BIN_EDGES = ((0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0))
_EPS = 1.0e-12


def _clip(probability):
    return min(max(float(probability), _EPS), 1.0 - _EPS)


def _bin_index(probability):
    for index, (low, high) in enumerate(BIN_EDGES):
        if low <= probability < high:
            return index
    return len(BIN_EDGES) - 1


def _validate(forecasts, min_resolved):
    if isinstance(min_resolved, bool) or not isinstance(min_resolved, int) or min_resolved < 1:
        raise ValueError("Why: min_resolved must be a positive int. "
                         "Fix: pass min_resolved=10.")
    pairs = []
    total = 0
    ignored = 0
    for forecast in forecasts:
        if not isinstance(forecast, dict):
            raise ValueError("a forecast must be a mapping")
        identifier = forecast.get("id")
        if not isinstance(identifier, str) or not identifier:
            raise ValueError("a forecast must have a non-empty string id")
        if "probability" not in forecast or "outcome" not in forecast:
            raise ValueError("forecast %s needs probability and outcome"
                             % identifier)
        probability = forecast["probability"]
        if (isinstance(probability, bool)
                or not isinstance(probability, (int, float))
                or not math.isfinite(float(probability))
                or not 0.0 <= float(probability) <= 1.0):
            raise ValueError("forecast %s probability must be in [0, 1]"
                             % identifier)
        outcome = forecast["outcome"]
        if outcome is not None and (
                isinstance(outcome, bool)
                or not isinstance(outcome, int)
                or outcome not in (0, 1)):
            raise ValueError("forecast %s outcome must be 0, 1 or None"
                             % identifier)
        total += 1
        if outcome is None:
            ignored += 1
        else:
            pairs.append((identifier, float(probability), int(outcome)))
    return pairs, total, ignored


def summary(forecasts, min_resolved=MIN_RESOLVED):
    """Compute the calibration scorecard for a sequence of forecasts."""
    pairs, total, ignored = _validate(forecasts, min_resolved)
    counts = {
        "total": total,
        "resolved": len(pairs),
        "ignored": ignored,
        "supported": sum(1 for _id, _p, outcome in pairs if outcome == 1),
        "refuted": sum(1 for _id, _p, outcome in pairs if outcome == 0),
    }
    resolved = counts["resolved"]
    coverage = round(resolved / total, 4) if total else 0.0
    brier = log_loss = base_rate = brier_baseline = skill = None
    if resolved:
        brier = sum((probability - outcome) ** 2
                    for _id, probability, outcome in pairs) / resolved
        log_loss = -sum(
            outcome * math.log(_clip(probability))
            + (1 - outcome) * math.log(_clip(1.0 - probability))
            for _id, probability, outcome in pairs
        ) / resolved
        base_rate = sum(outcome for _id, _p, outcome in pairs) / resolved
        brier_baseline = sum(
            (base_rate - outcome) ** 2 for _id, _p, outcome in pairs
        ) / resolved
        skill = 1.0 - brier / brier_baseline if brier_baseline > 0 else None

    bins = []
    for index, (low, high) in enumerate(BIN_EDGES):
        members = [(probability, outcome) for _id, probability, outcome in pairs
                   if _bin_index(probability) == index]
        if members:
            mean_confidence = sum(p for p, _o in members) / len(members)
            observed = sum(o for _p, o in members) / len(members)
            gap = observed - mean_confidence
        else:
            mean_confidence = observed = gap = None
        bins.append({
            "low": low, "high": high, "n": len(members),
            "mean_confidence": None if mean_confidence is None else round(mean_confidence, 4),
            "observed": None if observed is None else round(observed, 4),
            "gap": None if gap is None else round(gap, 4),
        })

    warnings = []
    if resolved == 0:
        warnings.append("no resolved forecast; calibration is undefined")
    elif resolved < min_resolved:
        warnings.append(
            "%d resolved forecast(s); scores are descriptive below %d"
            % (resolved, min_resolved))
    if resolved and base_rate in (0.0, 1.0):
        warnings.append(
            "every resolved outcome has the same label; discrimination cannot be measured")
    for item in bins:
        if item["n"] and item["gap"] is not None and abs(item["gap"]) >= 0.2:
            direction = "overconfident" if item["gap"] < 0 else "underconfident"
            warnings.append(
                "bin %.1f-%.1f is %s by %.2f"
                % (item["low"], item["high"], direction, abs(item["gap"])))

    return {
        "counts": counts,
        "coverage": coverage,
        "min_resolved": min_resolved,
        "brier": None if brier is None else round(brier, 6),
        "log_loss": None if log_loss is None else round(log_loss, 6),
        "base_rate": None if base_rate is None else round(base_rate, 6),
        "brier_baseline": None if brier_baseline is None else round(brier_baseline, 6),
        "skill": None if skill is None else round(skill, 6),
        "bins": bins,
        "warnings": warnings,
    }
