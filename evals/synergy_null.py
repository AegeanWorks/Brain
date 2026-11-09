"""A synergy gap plus the null it has to be read against.

``synergy`` returns a bare number. On the pinned traces that number ranges
from -0.4506 to +0.0373 and, measured against a permutation null, most of it
means nothing: at 600 shuffles only 2 of the 6 traces are distinguishable
from the null at all.

  trace                syn        null median  p_lower  p_upper  verdict
  T1_forage:71        +0.037283   -0.006886    0.662    0.338    inside
  T2_delayed_match:3  -0.376770   -0.203483    0.057    0.955    inside
  T3_navigate:15      -0.057913   -0.031775    0.478    0.547    inside
  T3_navigate:65      -0.450561   -0.219512    0.015    1.000    negative
  T3_navigate:74      -0.040767   -0.194799    1.000    0.017    negative
  T3_navigate:479     -0.047824   -0.100149    0.895    0.118    inside

Note the sign trap: a significantly *negative* gap has a small ``p_lower``
(T3:65 0.015) — not a small ``p_upper``. ``T3_navigate:74`` is significant in
the opposite tail (``p_upper`` 0.017) because it sits *above* its null while
still negative.

``permutation_null`` keeps the trace fixed and shuffles the target, which is
the "no relationship" hypothesis for the pair being scored. The shuffle is
seeded so a verdict is reproducible.
"""

import random

from evals.estimators import synergy

#: Share of the null excluded at each tail for ``distinguishable``.
TAIL = 0.05


def permutation_null(trace, target, trials=200, seed=0):
    """Return ``trials`` synergy gaps for shuffled copies of ``target``."""
    if isinstance(trials, bool) or not isinstance(trials, int) or trials < 1:
        raise ValueError(
            "Why: trials must be a positive int. "
            "Fix: pass trials=200 or another positive int.")
    if not trace or len(trace) != len(target):
        return []
    rng = random.Random(seed)
    pool = list(target)
    draws = []
    for _ in range(trials):
        rng.shuffle(pool)
        draws.append(synergy(trace, list(pool))[0])
    return draws


def synergy_verdict(trace, target, trials=200, seed=0):
    """Report a synergy gap against its permutation null.

    ``p_upper`` is the share of the null at or above the observed value and
    ``p_lower`` the share at or below it, so a significant *negative* gap is a
    small ``p_lower``. ``distinguishable`` is true when the observed value
    falls outside the middle ``1 - 2*TAIL`` of the null.
    """
    observed = synergy(trace, target)[0] if trace else 0.0
    draws = permutation_null(trace, target, trials=trials, seed=seed)
    if not draws:
        return {
            "observed": observed,
            "trials": 0,
            "null_median": None,
            "null_min": None,
            "null_max": None,
            "p_upper": None,
            "p_lower": None,
            "direction": "zero" if observed == 0.0 else
                         ("positive" if observed > 0.0 else "negative"),
            "distinguishable": False,
        }
    ordered = sorted(draws)
    n = len(ordered)
    p_upper = sum(1 for v in ordered if v >= observed) / n
    p_lower = sum(1 for v in ordered if v <= observed) / n
    low = ordered[int(TAIL * n)]
    high = ordered[min(n - 1, int((1.0 - TAIL) * n))]
    return {
        "observed": observed,
        "trials": n,
        "null_median": ordered[n // 2],
        "null_min": ordered[0],
        "null_max": ordered[-1],
        "p_upper": p_upper,
        "p_lower": p_lower,
        "direction": "zero" if observed == 0.0 else
                     ("positive" if observed > 0.0 else "negative"),
        "distinguishable": observed < low or observed > high,
    }
