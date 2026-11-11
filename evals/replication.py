"""A scan candidate must survive a held-out pool.

The family-wise scan corrects for testing many pairs on one pool; it does
not correct for selecting the pool where a noise pair cleared the tail. This
module keeps the family scan on the train rows and tests every selected
candidate on held-out rows with the same pair gate and null. A candidate is
selected only when the holdout pair is valid, positive and outside its own
null. ``require_replication=False`` is the executable ablation and returns
the train-only candidate set.
"""

from evals.pair_scan import ALPHA, pair_report, scan_pairs


def _train_candidate(report, alpha):
    """True when a train report is a positive, family-significant pair."""
    return (report["ok"] and report["syn"] > 0.0
            and report["family"]["p_upper"] <= alpha)


def scan_with_holdout(train_rows, train_target, holdout_rows, holdout_target,
                      trials=200, stability_trials=None, alpha=ALPHA,
                      require_replication=True, require_stability=True):
    """Return train candidates with their stability and holdout verdicts.

    ``stability_trials`` re-runs the train family scan at a higher trial
    count; a candidate that clears ``alpha`` at ``trials`` but not there is
    underpowered. The default is ``max(trials, 200)``. Each candidate carries
    ``stable``, ``replicated`` and both pair reports; ``selected`` honours
    the two gates, and ``rejected`` is the rest.
    """
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
                         family_wise=True)
    stable_map = None
    if require_stability and stability_trials > trials:
        stable_reports = scan_pairs(train_rows, train_target,
                                    trials=stability_trials,
                                    family_wise=True)
        stable_map = {tuple(report["columns"]): report
                      for report in stable_reports if report["ok"]}
    candidates = []
    for report in reports:
        if not _train_candidate(report, alpha):
            continue
        first, second = report["columns"]
        stable = True
        stability_report = None
        if require_stability and stable_map is not None:
            stability_report = stable_map.get((first, second))
            stable = bool(stability_report
                          and stability_report["family"]["p_upper"] <= alpha)
        holdout = pair_report(holdout_rows, holdout_target, first, second,
                              trials=trials)
        null = holdout.get("null") or {}
        replicated = bool(holdout["ok"] and holdout["syn"] > 0.0
                          and null.get("p_upper") is not None
                          and null["p_upper"] <= alpha)
        candidates.append({
            "candidate": report,
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
    return {
        "candidates": candidates,
        "selected": selected,
        "rejected": rejected,
        "alpha": alpha,
        "trials": trials,
        "stability_trials": stability_trials,
    }
