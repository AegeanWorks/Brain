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


def synergy(trace, target):
    """Joint-minus-marginals gap: (syn, syn_n)."""
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
