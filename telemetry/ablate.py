"""Deterministic trace transforms for ablation.

Trace model: a trace is a list of step mappings (or a single step
mapping). Each step mapping may carry keys ``M``, ``P``, ``S`` and
``hub``. Vector values are sequences of numbers; scalar values are
single numbers; absent or ``None`` values pass through unchanged.

All functions are pure: inputs are not mutated, outputs are new
containers, results depend only on arguments.
"""

import random

_MODULE_KEYS = ("M", "P", "S")


def _zero_value(value):
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return 0
    if isinstance(value, float):
        return 0.0
    return 0


def _zero_vector(vec):
    if isinstance(vec, tuple):
        return tuple(_zero_value(v) for v in vec)
    return [_zero_value(v) for v in vec]


def _copy_step(step):
    out = dict(step)
    for key in ("M", "P", "S", "hub"):
        if key in out and isinstance(out[key], (list, tuple)):
            out[key] = list(out[key]) if isinstance(out[key], list) else tuple(out[key])
    return out


def _map_trace(trace, func):
    if isinstance(trace, dict):
        return func(_copy_step(trace))
    if isinstance(trace, (list, tuple)):
        result = [func(_copy_step(step)) for step in trace]
        return tuple(result) if isinstance(trace, tuple) else result
    raise TypeError("trace must be a mapping or a list/tuple of mappings")


def hub_zero(trace):
    """Return trace copy with every ``hub`` vector replaced by zeros.

    Vector length and container kind are preserved; ``M``/``P``/``S``
    and all other keys are copied unchanged. ``None`` or missing
    ``hub`` values pass through unchanged.
    """

    def _one(step):
        hub = step.get("hub")
        if hub is None or "hub" not in step:
            return step
        if isinstance(hub, (int, float)) and not isinstance(hub, bool):
            step["hub"] = _zero_value(hub)
            return step
        if isinstance(hub, bool):
            step["hub"] = 0
            return step
        if isinstance(hub, (list, tuple)):
            step["hub"] = _zero_vector(hub)
            return step
        return step

    return _map_trace(trace, _one)


def module_lesion(trace, mod):
    """Return trace copy with module ``mod`` column zeroed.

    ``mod`` must be one of ``"M"``, ``"P"``, ``"S"``. The selected key
    is replaced by zeros (same length for sequences, zero scalar for
    numbers); all other keys pass through unchanged.
    """
    if mod not in _MODULE_KEYS:
        raise ValueError("mod must be one of 'M', 'P', 'S'")

    def _one(step):
        if mod not in step or step[mod] is None:
            return step
        value = step[mod]
        if isinstance(value, (list, tuple)):
            step[mod] = _zero_vector(value)
            return step
        if isinstance(value, (int, float, bool)):
            step[mod] = _zero_value(value)
            return step
        return step

    return _map_trace(trace, _one)


def shuffle_hub(trace, seed):
    """Return trace copy with each ``hub`` vector permuted deterministically.

    Each record ``i`` uses ``random.Random(str(seed) + ":" + str(i))``
    to permute its own ``hub`` entries, so repeated calls with the same
    ``seed`` yield identical output and distinct indices use distinct
    permutations. Element multisets per record are preserved; order
    across ``M``/``P``/``S`` is untouched.
    """

    is_single = isinstance(trace, dict)
    steps = [trace] if is_single else list(trace)
    if not is_single and not isinstance(trace, (list, tuple)):
        raise TypeError("trace must be a mapping or a list/tuple of mappings")

    out = []
    for i, step in enumerate(steps):
        rec = _copy_step(step) if isinstance(step, dict) else dict(step)
        hub = rec.get("hub")
        if isinstance(hub, (list, tuple)) and len(hub) > 1:
            rng = random.Random("%s:%d" % (seed, i))
            perm = list(range(len(hub)))
            rng.shuffle(perm)
            shuffled = [hub[j] for j in perm]
            rec["hub"] = tuple(shuffled) if isinstance(hub, tuple) else shuffled
        out.append(rec)

    if is_single:
        return out[0]
    return tuple(out) if isinstance(trace, tuple) else out
