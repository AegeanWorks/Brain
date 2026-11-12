"""A scan candidate must survive a held-out pool.

The family-wise scan corrects for testing many pairs on one pool; it does
not correct for selecting the pool where a noise pair cleared the tail. This
module keeps the family scan on the train rows and tests every selected
candidate on held-out rows with the same pair gate and null. It handles
both signs: a positive gap is an interaction, a negative gap is an
anti-interaction (the joint carries less than its marginals), and both are
cross-module dependencies worth replicating. A candidate is selected only
when the higher-trial tail and the holdout tail agree.
``require_replication=False`` and ``require_stability=False`` are the
executable ablations.
"""

from evals.pair_scan import (ALPHA, column_classes, pair_report,
                            scan_pairs)

DIRECTIONS = ("positive", "negative", "both")


def _direction_of(report, alpha, requested):
    """Return the candidate direction, or None when it does not clear."""
    if not report["ok"]:
        return None
    if (report["syn"] > 0.0
            and requested in ("positive", "both")
            and report["family"]["p_upper"] <= alpha):
        return "positive"
    if (report["syn"] < 0.0
            and requested in ("negative", "both")
            and report["family"]["p_lower"] <= alpha):
        return "negative"
    return None


def _tail_ok(report, direction, alpha):
    """True when a family-scan report clears the requested tail."""
    if not report or not report["ok"]:
        return False
    if direction == "positive":
        return (report["syn"] > 0.0
                and report["family"]["p_upper"] <= alpha)
    return (report["syn"] < 0.0
            and report["family"]["p_lower"] <= alpha)


def _holdout_ok(report, direction, alpha):
    """True when a single-pair holdout report clears the requested tail."""
    if not report or not report["ok"]:
        return False
    null = report.get("null") or {}
    if direction == "positive":
        return (report["syn"] > 0.0
                and null.get("p_upper") is not None
                and null["p_upper"] <= alpha)
    return (report["syn"] < 0.0
            and null.get("p_lower") is not None
            and null["p_lower"] <= alpha)


def _unique_items(items, classes):
    """Keep the first candidate for each pair of dependent-column classes."""
    seen = set()
    unique = []
    for item in items:
        first, second = item["candidate"]["columns"]
        key = tuple(sorted(
            classes[column] if 0 <= column < len(classes) else column
            for column in (first, second)))
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def scan_with_holdout(train_rows, train_target, holdout_rows, holdout_target,
                      trials=200, stability_trials=None, alpha=ALPHA,
                      direction="both", require_replication=True,
                      require_stability=True, unique=True, dedupe=True):
    """Return signed train candidates with stability and holdout verdicts.

    ``stability_trials`` re-runs the train family scan at a higher trial
    count; a candidate that clears ``alpha`` at ``trials`` but not there is
    underpowered. The default is ``max(trials, 200)``. ``direction`` is
    ``positive``, ``negative`` or ``both``. Each candidate carries
    ``direction``, ``stable``, ``replicated`` and both pair reports;
    ``selected`` honours the requested gates, and ``rejected`` is the rest.
    """
    if direction not in DIRECTIONS:
        raise ValueError(
            "Why: direction must be positive, negative or both. "
            "Fix: pass direction='both'.")
    if len(train_rows) != len(train_target):
        raise ValueError(
            "Why: train rows and target must align. "
            "Fix: pass one target per train row.")
    if len(holdout_rows) != len(holdout_target):
        raise ValueError(
            "Why: holdout rows and target must align. "
            "Fix: pass one target per holdout row.")
    if isinstance(trials, bool) or not isinstance(trials, int) or trials < 1:
        raise ValueError(
            "Why: trials must be a positive int. "
            "Fix: pass trials=200.")
    if stability_trials is None:
        stability_trials = max(trials, 200)
    if (isinstance(stability_trials, bool)
            or not isinstance(stability_trials, int)
            or stability_trials < trials):
        raise ValueError(
            "Why: stability_trials must be an int >= trials. "
            "Fix: pass stability_trials=200.")
    reports = scan_pairs(train_rows, train_target, trials=trials,
                         family_wise=True, dedupe=dedupe)
    stable_map = None
    if require_stability and stability_trials > trials:
        stable_reports = scan_pairs(train_rows, train_target,
                                    trials=stability_trials,
                                    family_wise=True, dedupe=dedupe)
        stable_map = {tuple(report["columns"]): report
                      for report in stable_reports if report["ok"]}
    candidates = []
    for report in reports:
        candidate_direction = _direction_of(report, alpha, direction)
        if candidate_direction is None:
            continue
        first, second = report["columns"]
        stable = True
        stability_report = None
        if require_stability and stable_map is not None:
            stability_report = stable_map.get((first, second))
            stable = _tail_ok(stability_report, candidate_direction, alpha)
        holdout = pair_report(holdout_rows, holdout_target, first, second,
                              trials=trials)
        replicated = _holdout_ok(holdout, candidate_direction, alpha)
        candidates.append({
            "candidate": report,
            "direction": candidate_direction,
            "stability": stability_report,
            "holdout": holdout,
            "stable": stable,
            "replicated": replicated,
        })
    selected = [
        item for item in candidates
        if (not require_stability or item["stable"])
        and (not require_replication or item["replicated"])
    ]
    rejected = [item for item in candidates if item not in selected]
    if unique:
        classes = column_classes(train_rows)
        selected = _unique_items(selected, classes)
        rejected = _unique_items(rejected, classes)
    return {
        "candidates": candidates,
        "selected": selected,
        "rejected": rejected,
        "alpha": alpha,
        "trials": trials,
        "stability_trials": stability_trials,
        "direction": direction,
        "unique": unique,
        "dedupe": dedupe,
    }
