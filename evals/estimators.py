"""Stdlib-only estimators for Brain evals.

Conventions:
- trace: sequence of rows, each row a sequence of floats, shape [T, N].
- target: sequence of scalars aligned with trace rows.
- All functions are deterministic given inputs; the only randomness is
  the seeded generator inside permutation_null.
"""
import math
import random


def _discretize(values, bins):
    xs = [float(v) for v in values]
    if not xs or bins < 1:
        return [0] * len(xs)
    lo, hi = min(xs), max(xs)
    if hi == lo:
        return [0] * len(xs)
    out = []
    for v in xs:
        b = int((v - lo) / (hi - lo) * bins)
        out.append(min(bins - 1, max(0, b)))
    return out


def mutual_info_discrete(xs, ys, bins=8):
    """Mutual information in nats between discretized xs and ys."""
    if len(xs) != len(ys) or not xs:
        return 0.0
    dx, dy = _discretize(xs, bins), _discretize(ys, bins)
    n = len(dx)
    cx = [0] * bins
    cy = [0] * bins
    jn = [[0] * bins for _ in range(bins)]
    for a, b in zip(dx, dy):
        cx[a] += 1
        cy[b] += 1
        jn[a][b] += 1
    mi = 0.0
    for a in range(bins):
        for b in range(bins):
            pxy = jn[a][b] / n
            if pxy > 0.0 and cx[a] > 0 and cy[b] > 0:
                mi += pxy * math.log(pxy / ((cx[a] / n) * (cy[b] / n)))
    return max(0.0, mi)


def _solve(A, b):
    n = len(A)
    M = [list(A[i]) + [b[i]] for i in range(n)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        if abs(M[p][c]) < 1e-12:
            return [0.0] * n
        M[c], M[p] = M[p], M[c]
        d = M[c][c]
        M[c] = [v / d for v in M[c]]
        for r in range(n):
            if r != c and M[r][c] != 0.0:
                f = M[r][c]
                M[r] = [rv - f * cv for rv, cv in zip(M[r], M[c])]
    return [row[n] for row in M]


def phi_ar(trace):
    """Residual-variance ratio: 1 - MSE(whole)/MSE(partitioned), clipped at 0."""
    T = len(trace)
    if T < 3:
        return 0.0
    X = [[float(v) for v in row] for row in trace]
    n = len(X[0])
    if n < 1 or any(len(r) != n for r in X):
        return 0.0
    XA = [[1.0] + X[t] for t in range(T - 1)]
    Y = X[1:]
    p = n + 1
    XtX = [[0.0] * p for _ in range(p)]
    for r in XA:
        for i in range(p):
            for j in range(p):
                XtX[i][j] += r[i] * r[j]
    mse_w, mse_p = 0.0, 0.0
    for j in range(n):
        col = [Y[t][j] for t in range(T - 1)]
        Xty = [sum(XA[t][i] * col[t] for t in range(T - 1)) for i in range(p)]
        w = _solve(XtX, Xty)
        resid = 0.0
        for t in range(T - 1):
            pred = sum(w[i] * XA[t][i] for i in range(p))
            resid += (col[t] - pred) ** 2
        mse_w += resid / (T - 1)
        xj = [X[t][j] for t in range(T - 1)]
        mx, my = sum(xj) / len(xj), sum(col) / len(col)
        sxx = sum((v - mx) ** 2 for v in xj)
        if sxx < 1e-12:
            rp = sum((v - my) ** 2 for v in col) / len(col)
        else:
            sxy = sum((xj[k] - mx) * (col[k] - my) for k in range(len(col)))
            a = sxy / sxx
            rp = sum((col[k] - (my + a * (xj[k] - mx))) ** 2 for k in range(len(col))) / len(col)
        mse_p += rp
    if mse_p <= 1e-12:
        return 0.0
    return max(0.0, 1.0 - (mse_w / mse_p))


#: Trace columns the ``synergy`` joint code is built from. The estimator is
#: defined over exactly this pair; every later column is never read. Callers
#: that report a 0.0 must consult :func:`synergy_scope` before reading it as
#: absent integration, because this pair can be blind to a live signal.
SYNERGY_COLUMNS = (0, 1)


def synergy_scope(trace, target):
    """Report which trace columns ``synergy`` reads, and whether they can decide.

    ``synergy`` forms its joint code from ``trace[0]`` and ``trace[1]`` only.
    When column 0 is constant the joint code is a bijection of column 1's
    bins, so the joint-minus-marginals gap is structurally ``0.0`` no matter
    what the remaining columns carry. A caller that reads that ``0.0`` as
    "no integration" is then asserting something the estimator cannot see.

    This returns the scope as data so the limit travels with the number:
    ``columns`` read, ``ignored_columns`` never read, ``constant_columns``
    inside the scope, ``duplicate_columns`` when the scope columns carry the
    same values, and ``sufficient`` with a ``reason``. It reads no
    randomness and changes no estimate.
    """
    n_rows = len(trace)
    width = max((len(row) for row in trace), default=0)
    base = {
        "columns": list(SYNERGY_COLUMNS),
        "ignored_columns": list(range(len(SYNERGY_COLUMNS), width)),
        "n_rows": n_rows,
        "n_columns": width,
        "constant_columns": [],
        "duplicate_columns": [],
        "sufficient": False,
        "reason": None,
    }
    if n_rows == 0 or width == 0:
        base["reason"] = "empty-trace"
        return base
    if n_rows != len(target):
        base["reason"] = "shape-mismatch"
        return base
    # If either scope column is constant the joint code collapses to a
    # bijection of the other, so the gap is exactly 0.0 by construction.
    constant = [j for j in SYNERGY_COLUMNS
                if j >= width or len({row[j] for row in trace}) <= 1]
    base["constant_columns"] = constant
    if constant:
        base["reason"] = "constant-scope-column"
        return base
    # If the two scope columns carry the same values there is no independent
    # second signal: the pair cannot support a claim about interaction, and
    # any positive gap it reports comes from re-binning the joint code, not
    # from two variables. Measured both ways: with c0 == c1 over 1..15 the
    # gap is +0.054115 (ij 0.50040 > i1 0.22314, because bins=64 over a
    # 8..127 range merges codes), while over a 4-value column it is exactly
    # -MI. Sufficiency is about independence, so a duplicate is insufficient
    # either way.
    low, high = SYNERGY_COLUMNS
    if [row[low] for row in trace] == [row[high] for row in trace]:
        base["duplicate_columns"] = [low, high]
        base["reason"] = "duplicate-scope-column"
        return base
    base["sufficient"] = True
    return base


def synergy(trace, target):
    """Joint-minus-marginals gap: (syn, syn_n).

    The joint code spans ``SYNERGY_COLUMNS`` only; see
    :func:`synergy_scope` for what that pair can and cannot decide.
    """
    if not trace or len(trace) != len(target):
        return (0.0, 0.0)
    c0 = [float(r[0]) for r in trace]
    c1 = [float(r[1]) for r in trace] if len(trace[0]) > 1 else [0.0] * len(trace)
    c1_bins = _discretize(c1, 8)
    tj = [float(c0[i]) * 8.0 + float(c1_bins[i]) for i in range(len(c0))]
    i1 = mutual_info_discrete(c0, list(target))
    i2 = mutual_info_discrete(c1, list(target))
    ij = mutual_info_discrete(tj, list(target), bins=64)
    syn = ij - i1 - i2
    return (syn, (syn / ij) if ij > 1e-12 else 0.0)


def synergy_sign(syn, syn_n):
    """Classify a synergy gap's direction as ``positive``, ``negative`` or ``zero``.

    ``syn`` is ``I(joint) - I(c1) - I(c2)``, so it is negative whenever the
    joint code carries less information than the sum of its marginals.
    ``syn_n`` divides by ``I(joint)``, which means a negative gap can produce
    ``syn_n == -1.0`` — the largest magnitude the ratio can reach. Read alone
    that looks like the strongest possible interaction when it is the
    opposite, so the direction travels with the number.

    The classification follows the sign of ``syn``; ``syn_n`` is accepted so
    a caller holding both does not have to re-derive which is authoritative.
    """
    if not syn:
        return "zero"
    return "positive" if float(syn) > 0.0 else "negative"


def gbi(pre_decodable, post_decodable):
    """Headroom-normalized change: (post - pre) / (1 - pre)."""
    pre, post = float(pre_decodable), float(post_decodable)
    if pre >= 1.0:
        return 0.0 if post >= pre else post - pre
    return (post - pre) / (1.0 - pre)


def logistic_k(x, y):
    """Grid search over slope k; returns (best_k, r2)."""
    xs = [float(v) for v in x]
    ys = [float(v) for v in y]
    if len(xs) != len(ys) or not xs:
        return (0.0, 0.0)
    s = sorted(xs)
    x0 = s[len(s) // 2]
    mean_y = sum(ys) / len(ys)
    sst = sum((v - mean_y) ** 2 for v in ys)
    best_k, best_r2 = 0.0, float("-inf")
    for gi in range(-40, 41):
        k = gi / 4.0
        ssr = 0.0
        for xi, yi in zip(xs, ys):
            e = math.exp(-k * (xi - x0)) if -k * (xi - x0) < 700 else float("inf")
            p = 1.0 / (1.0 + e)
            ssr += (yi - p) ** 2
        r2 = 1.0 - ssr / sst if sst > 1e-12 else (1.0 if ssr < 1e-12 else 0.0)
        if r2 > best_r2:
            best_k, best_r2 = k, r2
    return (best_k, best_r2)


def transfer_gain(naive_steps, reuse_steps):
    """Relative step reduction: (naive - reuse) / naive."""
    n, r = float(naive_steps), float(reuse_steps)
    if n <= 0:
        return 0.0
    return (n - r) / n


def recovery(time_outside, window):
    """Window fraction inside bounds: 1 - time_outside / window, clipped."""
    t, w = float(time_outside), float(window)
    if w <= 0:
        return 0.0
    return min(1.0, max(0.0, 1.0 - t / w))


def permutation_null(values_fn, shuffles=200, seed=0):
    """95th percentile of null statistics from a seeded generator."""
    rng = random.Random(seed)
    vals = []
    for _ in range(max(1, int(shuffles))):
        try:
            v = values_fn(rng)
        except TypeError:
            v = values_fn()
        vals.append(float(v))
    vals.sort()
    idx = min(len(vals) - 1, int(math.ceil(0.95 * len(vals))) - 1)
    return vals[max(0, idx)]
