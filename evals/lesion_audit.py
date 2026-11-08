"""Lesion detectability: can a readout tell a lesion from arbitrary noise?

A lesion test ("zero module X and show the score changes") is only evidence
when the readout can change for that module at all. If the readout is blind
to X's columns, zeroing X and swapping in random values produce the same
result, so "the score did not move" cannot support "X is not integrated"
(EVID-009: a control that never fails is not a control).

This module makes that surface explicit and measurable. It substitutes one
module's block with deterministic pseudo-random values of the same shape and
reports which modules each shipped readout can distinguish from noise. It
runs no agent and touches no telemetry; it answers one question per
readout/module pair so a lesion claim can cite a detectable surface or be
recorded as vacuous.
"""

import random

from evals.estimators import SYNERGY_COLUMNS, phi_ar, synergy

#: Module name -> half-open column span in the M/P/S/hub block row that
#: ``agent.Agent._step_vectors`` emits: M=[0,2], P=[2,4], S=[4,6], hub=[6,...].
MODULE_SPANS = {"M": (0, 2), "P": (2, 4), "S": (4, 6), "hub": (6, None)}

#: Modules the ablation helpers can lesion, in block order.
LESION_MODULES = ("M", "P", "S", "hub")


def module_columns(module, width=None):
    """Column indices belonging to ``module`` within a row of ``width``."""
    if module not in MODULE_SPANS:
        raise ValueError(
            "Why: %r is not a module. Fix: pass one of %s."
            % (module, list(LESION_MODULES)))
    low, high = MODULE_SPANS[module]
    if high is None:
        high = width if width is not None else low + 3
    return list(range(low, high))


def substitute_module(rows, module, seed=0):
    """Copy ``rows`` with ``module``'s block replaced by seeded random floats.

    Shape and every other column are preserved. Substitution, rather than
    zeroing, is the right probe for detectability: zeros can coincide with a
    real invariant (a counter at zero), while pseudo-random values of the
    same scale as the block cannot.
    """
    if not rows:
        return []
    width = max(len(row) for row in rows)
    columns = set(module_columns(module, width))
    rng = random.Random("%s:%s" % (seed, module))
    out = []
    for row in rows:
        copy = [float(value) for value in row]
        for column in columns:
            if column < len(copy):
                copy[column] = rng.random() * 16.0
        out.append(copy)
    return out


def _synergy_of(rows):
    if not rows:
        return (0.0, 0.0)
    width = max(len(row) for row in rows)
    padded = [list(row) + [0.0] * (width - len(row)) for row in rows]
    trace = [row[:-1] for row in padded]
    target = [row[-1] for row in padded]
    return synergy(trace, target)


def _phi_of(rows):
    if len(rows) < 3:
        return 0.0
    width = max(len(row) for row in rows)
    padded = [list(row) + [0.0] * (width - len(row)) for row in rows]
    return phi_ar(padded)


def detectability(rows, seed=0):
    """Report, per readout, which modules it can distinguish from noise.

    ``rows`` are full block rows (target in the last column, as
    ``evals.recompute`` builds them). A module is ``detectable`` when
    substituting its block changes the readout at all; ``invisible`` lists
    the rest, whose lesion tests cannot be evidence for that readout.
    """
    baseline_syn = _synergy_of(rows)
    baseline_phi = _phi_of(rows)
    detectable_syn, invisible_syn = [], []
    detectable_phi, invisible_phi = [], []
    for module in LESION_MODULES:
        swapped = substitute_module(rows, module, seed=seed)
        if _synergy_of(swapped) != baseline_syn:
            detectable_syn.append(module)
        else:
            invisible_syn.append(module)
        if _phi_of(swapped) != baseline_phi:
            detectable_phi.append(module)
        else:
            invisible_phi.append(module)
    width = max((len(row) for row in rows), default=0)
    return {
        "synergy": {
            "columns": list(SYNERGY_COLUMNS),
            "detectable": detectable_syn,
            "invisible": invisible_syn,
            "all_detectable": not invisible_syn,
            "baseline": baseline_syn[0],
        },
        "phi": {
            "columns": list(range(max(0, width - 1))),
            "detectable": detectable_phi,
            "invisible": invisible_phi,
            "all_detectable": not invisible_phi,
            "baseline": baseline_phi,
        },
        "n_rows": len(rows),
        "n_columns": width,
    }
