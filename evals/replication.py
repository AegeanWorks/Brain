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
                      trials=200, alpha=ALPHA, require_replication=True):
    """Return train candidates with their holdout verdict.

    Each candidate carries the train report, the holdout pair report, and a
    ``replicated`` flag. ``selected`` is the replicated subset when
    ``require_replication`` is true, and the full candidate set otherwise;
    ``rejected`` is always the non-replicated subset.
    """
    if len(train_rows) != len(train_target):
        raise ValueError(
            "Why: train rows and target must align. "
            "Fix: pass one target per train row.")
    if len(holdout_rows) != len(holdout_target):
        raise ValueError(
            "Why: holdout rows and target must align. "
            "Fix: pass one target per holdout row.")
    reports = scan_pairs(train_rows, train_target, trials=trials,
                         family_wise=True)
    candidates = []
    for report in reports:
        if not _train_candidate(report, alpha):
            continue
        first, second = report["columns"]
        holdout = pair_report(holdout_rows, holdout_target, first, second,
                              trials=trials)
        null = holdout.get("null") or {}
        replicated = bool(holdout["ok"] and holdout["syn"] > 0.0
                          and null.get("p_upper") is not None
                          and null["p_upper"] <= alpha)
        candidates.append({
            "candidate": report,
            "holdout": holdout,
            "replicated": replicated,
        })
    selected = ([item for item in candidates if item["replicated"]]
                if require_replication else list(candidates))
    rejected = [item for item in candidates if not item["replicated"]]
    return {
        "candidates": candidates,
        "selected": selected,
        "rejected": rejected,
        "alpha": alpha,
        "trials": trials,
    }
