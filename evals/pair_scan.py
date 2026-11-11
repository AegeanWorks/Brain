"""Searching for an interacting column pair needs a per-pair validity gate.

Rung 3 asks which module pairs carry joint information. Scanning all pairs
with ``synergy`` alone finds confident positives that are artifacts:

  T1_forage:71  cols(1,2) syn +0.2599  p_upper 0.000  "distinguishable"
                cols(1,3) syn +0.2599  p_upper 0.000
                cols(1,4) syn +0.2599  p_upper 0.000

but column 2 is **constant** (values ``[0.0]``, distinct=1), so ``i2 == 0``
and the joint code is a relabelling of column 1: `ij` rises from 0.222647 to
0.482578 only because ``mutual_info_discrete(tj, ..., bins=64)`` re-bins a
16-code joint. Any pair with a constant partner scores identically, which is
exactly what those three rows show.

A permutation null does not catch this — the artifact survives it. The gate
has to be structural: both columns must vary, they must not be the same
column, and **neither may be a deterministic function of the other**. That
last condition is the one that matters most, because the shipped block is
almost entirely collinear: on `T3_navigate:15` every column in the 9-column
M/P/S/hub block is a deterministic function of every other (the only
exceptions are col6 vs col7/col8). A pair drawn from that block is one
variable counted twice, so no pair of it can demonstrate an interaction.

``synergy_scope`` computes the constant/duplicate checks per pair;
``_dependent`` adds the functional-dependence check. Measured on the shipped
traces, the only pairs that pass every gate have a gap that does not beat
the null, so ``interactions`` returns nothing — which is the honest answer
for a substrate whose trace carries one variable in nine columns.
"""

import random

from evals.estimators import synergy, synergy_scope
from evals.synergy_null import synergy_verdict

#: Family-wise tail for a scan that tests every valid pair at once.
ALPHA = 0.05


def _dependent(first, second):
    """True when one column is a deterministic function of the other.

    A pair of functionally dependent columns is one variable measured twice,
    so ``I(joint)`` cannot exceed the marginal and any positive gap is a
    re-binning artifact rather than interaction.
    """
    forward = {}
    for a, b in zip(first, second):
        if forward.setdefault(a, b) != b:
            forward = None
            break
    if forward is not None:
        return True
    backward = {}
    for b, a in zip(second, first):
        if backward.setdefault(a, b) != b:
            return False
    return True


def pair_report(rows, target, first, second, trials=200, with_null=True):
    """Score one column pair, refusing artifacts before scoring.

    Returns ``syn``/``syn_n``/``ok`` plus the scope verdict. ``ok`` is false
    when the pair cannot decide (constant, duplicate or functionally
    dependent columns), in which case the gap is reported but must not be
    read as interaction. ``with_null=False`` omits the single-pair null for
    callers that will apply a family-wise null across all pairs instead.
    """
    pair = [[row[first], row[second]] for row in rows]
    scope = synergy_scope(pair, target)
    syn, syn_n = synergy(pair, target)
    reason = scope["reason"]
    if scope["sufficient"] and _dependent([r[0] for r in pair],
                                          [r[1] for r in pair]):
        reason = "dependent-columns"
    report = {
        "columns": [first, second],
        "syn": syn,
        "syn_n": syn_n,
        "ok": reason is None,
        "reason": reason,
    }
    if report["ok"] and with_null:
        report["null"] = synergy_verdict(pair, target, trials=trials)
    return report


def _family_wise(rows, target, reports, trials=200, seed=0):
    """Attach a max/min-statistic null to every pair that passed the gate.

    ``synergy_verdict`` tests one pre-registered pair. A scan tests many, so
    the per-pair 5% tails accumulate: a 28-pair scan expects a false positive
    by construction. This null keeps the trace fixed and shuffles the target
    once per trial, scores every valid pair against the *same* shuffled
    target, and records the largest and smallest gap in that trial. Each
    observed gap is then compared with that family's extreme, so the scan's
    multiplicity is paid by one corrected tail rather than by a divisor.
    """
    if isinstance(trials, bool) or not isinstance(trials, int) or trials < 1:
        raise ValueError(
            "Why: trials must be a positive int. "
            "Fix: pass trials=200 or another positive int.")
    valid = [report for report in reports if report["ok"]]
    if not valid:
        return
    pairs = [(report["columns"][0], report["columns"][1])
             for report in valid]
    matrices = [[[row[first], row[second]] for row in rows]
                for first, second in pairs]
    rng = random.Random(seed)
    pool = list(target)
    maxima = []
    minima = []
    for _ in range(trials):
        rng.shuffle(pool)
        shuffled = list(pool)
        gaps = [synergy(matrix, shuffled)[0] for matrix in matrices]
        maxima.append(max(gaps))
        minima.append(min(gaps))
    for report in valid:
        observed = report["syn"]
        report["family"] = {
            "trials": trials,
            "family_size": len(valid),
            "p_upper": (1 + sum(1 for value in maxima
                                if value >= observed)) / (trials + 1),
            "p_lower": (1 + sum(1 for value in minima
                                if value <= observed)) / (trials + 1),
        }


def scan_pairs(rows, target, trials=200, family_wise=True, seed=0):
    """Return every column pair's report, sorted by gap descending.

    Pairs that fail the gate sort last regardless of their gap, so a caller
    reading the head of the list never sees an artifact first. With
    ``family_wise=True`` every valid pair carries a ``family`` block holding
    the scan-corrected tails; ``family_wise=False`` restores the per-pair
    null only and is the executable ablation.
    """
    if not rows:
        return []
    width = min(len(row) for row in rows)
    reports = []
    for first in range(width):
        for second in range(first + 1, width):
            reports.append(pair_report(rows, target, first, second, trials,
                                       with_null=not family_wise))
    reports.sort(key=lambda r: (r["ok"], r["syn"]), reverse=True)
    if family_wise:
        _family_wise(rows, target, reports, trials=trials, seed=seed)
    return reports


def interactions(rows, target, trials=200, family_wise=True, seed=0):
    """Return only the pairs that pass the gate AND beat their family upward.

    This is the honest answer to "which two modules interact": empty when no
    pair both varies independently and clears the scan-corrected positive
    tail. A pair that is distinguishable only *below* its family is
    anti-interacting (the joint carries less than its marginals), a different
    claim returned by :func:`anti_interactions`.
    """
    selected = []
    for report in scan_pairs(rows, target, trials, family_wise=family_wise,
                             seed=seed):
        if not report["ok"] or report["syn"] <= 0.0:
            continue
        if family_wise:
            if report["family"]["p_upper"] <= ALPHA:
                selected.append(report)
        elif report["null"]["distinguishable"]:
            selected.append(report)
    return selected


def anti_interactions(rows, target, trials=200, family_wise=True, seed=0):
    """Return pairs that pass the gate and sit below their family null.

    Kept separate from :func:`interactions` so a caller counting
    "interactions" is never handed a negative gap. The same family-wise
    correction applies to the lower tail.
    """
    selected = []
    for report in scan_pairs(rows, target, trials, family_wise=family_wise,
                             seed=seed):
        if not report["ok"] or report["syn"] >= 0.0:
            continue
        if family_wise:
            if report["family"]["p_lower"] <= ALPHA:
                selected.append(report)
        elif report["null"]["distinguishable"]:
            selected.append(report)
    return selected
