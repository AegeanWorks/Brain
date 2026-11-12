"""Read the optional six-value module-state channel from telemetry.

``Agent(module_signals=True)`` (the default) writes a pre-action ``signals``
block into each action record:

    M = [distinct positions, turns] (revisits in the ablation)
    P = [BFS distance, ties]
    S = [online probability, distinct feature keys seen]

The six values use the same M/P/S block layout as the legacy vector, so a
seven-column row (six signals plus the reward target) can go straight into
``evals.pair_scan``. ``module_signals=False`` is the executable ablation:
the action records carry no ``signals`` block and this reader returns no
rows.
"""

import json

from evals.pair_scan import module_interactions, scan_pairs, world_interactions


def _row(args):
    """Return one six-signal row plus target, or None when malformed."""
    signals = args.get("signals")
    if not isinstance(signals, dict):
        return None
    values = []
    for block in ("M", "P", "S"):
        pair = signals.get(block)
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            return None
        try:
            values.extend(float(value) for value in pair)
        except (TypeError, ValueError):
            return None
    try:
        target = float(args.get("reward", 0.0))
    except (TypeError, ValueError):
        target = 0.0
    return values + [target]


def read_signals(log_path):
    """Return one row per action record carrying a ``signals`` block."""
    rows = []
    with open(log_path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(record, dict) or record.get("type") != "action":
                continue
            args = record.get("args")
            if not isinstance(args, dict):
                continue
            row = _row(args)
            if row is not None:
                rows.append(row)
    return rows


def pool_signals(log_paths):
    """Concatenate the signal rows from several episode logs."""
    rows = []
    for path in log_paths:
        rows.extend(read_signals(path))
    return rows


def signals_from_trace(trace):
    """Return one signal row per trace step that carries a signals block."""
    rows = []
    for step in trace:
        if not isinstance(step, dict):
            continue
        row = _row({"signals": step.get("signals"),
                    "reward": step.get("reward", 0.0)})
        if row is not None:
            rows.append(row)
    return rows


def scan_traces(traces, trials=200):
    """Scan pooled in-memory traces with the shared pair gate and family null."""
    rows = []
    for trace in traces:
        rows.extend(signals_from_trace(trace))
    target = [row[-1] for row in rows]
    return scan_pairs(rows, target, trials=trials, family_wise=True)


def scan_module_states(log_paths, trials=200):
    """Scan pooled signal rows with the shared pair gate and family null."""
    rows = pool_signals(log_paths)
    target = [row[-1] for row in rows]
    return scan_pairs(rows, target, trials=trials, family_wise=True)


def scan_module_state_blocks(log_paths, trials=200):
    """Return the pooled signal scan split into module and world pairs."""
    rows = pool_signals(log_paths)
    target = [row[-1] for row in rows]
    return {
        "module": module_interactions(rows, target, trials=trials),
        "world": world_interactions(rows, target, trials=trials),
    }
