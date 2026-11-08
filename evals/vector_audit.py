"""Audit a telemetry vector matrix for degenerate (non-independent) columns.

``Agent._step_vectors`` emits one 9-component vector per step:
M=[memory count, recall hits], P=[planner idx, pending],
S=[errors, budget], hub=[x, y, reward]. The integration readouts
(``evals.recompute``, ``evals.lesion_audit``) treat those blocks as the
memory, planner, self-model and world signals, but several components are
mechanically the step index: the loop saves one memory row, records one
self-model transition and marks one planner step per iteration. Those
counters therefore agree by construction, not by measurement.

This module reports that degeneracy as data instead of leaving it to be
inferred: which columns are constant, which pairs are byte-identical, and
how many distinct non-constant columns actually remain. A block with
fewer than three distinct columns is not three independent measurements,
so a cross-module number computed from it must not be read as coupling.

Pure functions over rows; no agent, no telemetry, no randomness.
"""

#: Column labels in the order ``_step_vectors`` concatenates the blocks.
BLOCK_LABELS = ["M0", "M1", "P0", "P1", "S0", "S1", "hub0", "hub1", "hub2"]

#: Minimum distinct non-constant columns a full block matrix is expected to
#: carry before it can represent three modules plus the world hub.
MIN_DISTINCT = 3


def _width(rows):
    return max((len(row) for row in rows), default=0)


def _label(index):
    return BLOCK_LABELS[index] if index < len(BLOCK_LABELS) else "c%d" % index


def column_report(rows):
    """Return the constant columns, row/column counts, and their labels."""
    width = _width(rows)
    constant = []
    for index in range(width):
        if len({row[index] for row in rows}) <= 1:
            constant.append(_label(index))
    return {
        "n_rows": len(rows),
        "n_columns": width,
        "constant": constant,
    }


def duplicate_pairs(rows):
    """Return sorted label pairs whose columns are byte-identical."""
    width = _width(rows)
    pairs = []
    for a in range(width):
        for b in range(a + 1, width):
            if all(row[a] == row[b] for row in rows):
                pairs.append((_label(a), _label(b)))
    return sorted(pairs)


def distinct_columns(rows):
    """Return the number of distinct non-constant column value sequences."""
    width = _width(rows)
    seen = set()
    for index in range(width):
        values = tuple(row[index] for row in rows)
        if len(set(values)) <= 1:
            continue
        seen.add(values)
    return len(seen)


def degenerate_columns(rows):
    """Return labels of columns that repeat another column's values.

    A column is degenerate when some earlier column carries the same value
    sequence. Constants are excluded here: :func:`column_report` already
    names them, and every constant trivially repeats every other constant.
    """
    width = _width(rows)
    seen = {}
    degenerate = []
    for index in range(width):
        values = tuple(row[index] for row in rows)
        if len(set(values)) <= 1:
            continue
        if values in seen:
            degenerate.append(_label(index))
        else:
            seen[values] = index
    return degenerate


def audit_rows(rows):
    """Report the independence of one vector matrix in a single mapping."""
    report = column_report(rows)
    report["duplicates"] = duplicate_pairs(rows)
    report["degenerate"] = degenerate_columns(rows)
    report["distinct"] = distinct_columns(rows)
    report["sufficient"] = report["distinct"] >= MIN_DISTINCT
    return report


def audit_vectors(vectors):
    """Audit ``(M, P, S, hub)`` tuples directly, flattening them first."""
    rows = []
    for m, p, s, hub in vectors:
        rows.append(list(m) + list(p) + list(s) + list(hub))
    return audit_rows(rows)
