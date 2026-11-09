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

from evals.estimators import synergy, synergy_scope
from evals.synergy_null import synergy_verdict


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


def pair_report(rows, target, first, second, trials=200):
    """Score one column pair, refusing artifacts before scoring.

    Returns ``syn``/``syn_n``/``ok`` plus the scope verdict. ``ok`` is false
    when the pair cannot decide (constant, duplicate or functionally
    dependent columns), in which case the gap is reported but must not be
    read as interaction.
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
    if report["ok"]:
        report["null"] = synergy_verdict(pair, target, trials=trials)
    return report


def scan_pairs(rows, target, trials=200):
    """Return every column pair's report, sorted by gap descending.

    Pairs that fail the gate sort last regardless of their gap, so a caller
    reading the head of the list never sees an artifact first.
    """
    if not rows:
        return []
    width = min(len(row) for row in rows)
    reports = []
    for first in range(width):
        for second in range(first + 1, width):
            reports.append(pair_report(rows, target, first, second, trials))
    reports.sort(key=lambda r: (r["ok"], r["syn"]), reverse=True)
    return reports


def interactions(rows, target, trials=200):
    """Return only the pairs that pass the gate AND beat their null upward.

    This is the honest answer to "which two modules interact": empty when no
    pair both varies independently and exceeds its permutation null on the
    positive side. A pair that is distinguishable only *below* its null is
    anti-interacting (the joint carries less than its marginals), which is a
    different claim and is returned separately by :func:`anti_interactions`.
    """
    return [report for report in scan_pairs(rows, target, trials)
            if report["ok"] and report["null"]["distinguishable"]
            and report["syn"] > 0.0]


def anti_interactions(rows, target, trials=200):
    """Return pairs that pass the gate and sit significantly *below* the null.

    Kept separate from :func:`interactions` so a caller counting
    "interactions" is never handed a negative gap.
    """
    return [report for report in scan_pairs(rows, target, trials)
            if report["ok"] and report["null"]["distinguishable"]
            and report["syn"] < 0.0]
