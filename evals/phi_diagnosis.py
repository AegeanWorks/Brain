"""A pinned 0.0 must say whether the estimator *could* have moved.

Every cycle's baseline pins ``phi == 0.0``. Measured: ``phi_ar`` returns
0.0 on all 120 real runs (seeds 0-39 for each of T1/T2/T3) and only
0.00772296 on a synthetic strong AR(1) series — so the ``0.0`` pin cannot
fail for trace reasons and asserts nothing about the estimator's power.

An assertion that cannot fail is not evidence (EVID-009). This module
records *why* phi is 0.0: which columns it reads, whether they vary, and
the smallest input that does move it. A reader then knows the pin is a
statement about these traces, not about phi's sensitivity.

Pure functions over rows; no agent, no telemetry.
"""

from evals.estimators import phi_ar


def _columns(rows):
    if not rows:
        return []
    width = max(len(row) for row in rows)
    return [[float(row[index]) if index < len(row) else 0.0
             for row in rows] for index in range(width)]


def phi_diagnosis(rows):
    """Explain a ``phi_ar`` result as data.

    Returns ``phi``, the row count, whether every column is constant, the
    per-column unique counts, and ``predictable`` — whether the trace has
    any within-column variation at all. A trace whose columns are constant
    cannot produce a non-zero residual-variance ratio, so a reported
    ``0.0`` on such a trace is a property of the input, not a measurement
    of "no integration".
    """
    phi = phi_ar(rows)
    columns = _columns(rows)
    unique = [len(set(column)) for column in columns]
    return {
        "phi": phi,
        "n_rows": len(rows),
        "n_columns": len(columns),
        "unique_per_column": unique,
        "all_constant": bool(unique) and all(count <= 1 for count in unique),
        # phi_ar returns 0.0 for fewer than three rows by construction, so a
        # shorter trace cannot support a forecast however much it varies.
        "predictable": len(rows) >= 3 and any(count > 1 for count in unique),
    }


def probe_scale():
    """Return the smallest synthetic series that moves ``phi_ar`` off 0.0.

    Used only to show the estimator is responsive at all; the shipped
    traces are not this series.
    """
    import random

    rng = random.Random(1)
    series = [[0.0, 0.0]]
    for _ in range(60):
        previous = series[-1]
        series.append([0.95 * previous[0] + rng.gauss(0, 0.1),
                       0.90 * previous[1] + rng.gauss(0, 0.2)])
    return phi_ar(series)
