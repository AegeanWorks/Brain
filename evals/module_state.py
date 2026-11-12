"""Read the optional six-value module-state channel from telemetry.

``Agent(module_signals=True)`` (the default) writes a pre-action ``signals``
block into each action record:

    M = [distinct positions, turns] (revisits in the ablation)
    P = [alternatives count, ties] (distance in the ablation)
    S = [online probability, distinct feature keys seen]

The six values use the same M/P/S block layout as the legacy vector, so a
seven-column row (six signals plus the reward target) can go straight into
``evals.pair_scan``. ``module_signals=False`` is the executable ablation:
the action records carry no ``signals`` block and this reader returns no
rows.
"""

import json

from evals.pair_scan import (anti_interactions, column_classes,
                            interactions, module_pair, scan_pairs,
                            unique_pairs, world_pair)


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


def read_signal_metadata(log_path):
    """Return the first action record's signals metadata, or None."""
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
            if not isinstance(args, dict) or not isinstance(
                    args.get("signals"), dict):
                continue
            meta = args.get("signals_meta")
            if isinstance(meta, dict):
                return dict(meta)
    return None


def signals_meta_from_trace(trace):
    """Return the first trace step's signals metadata, or None."""
    for step in trace:
        if not isinstance(step, dict):
            continue
        meta = step.get("signals_meta")
        if isinstance(meta, dict):
            return dict(meta)
    return None


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


def scan_traces(traces, trials=200, dedupe=True):
    """Scan pooled in-memory traces with the shared pair gate and family null.

    ``dedupe=True`` removes dependent-column aliases before the family null;
    ``dedupe=False`` restores the raw family and is the executable ablation.
    """
    rows = []
    for trace in traces:
        rows.extend(signals_from_trace(trace))
    target = [row[-1] for row in rows]
    return scan_pairs(rows, target, trials=trials, family_wise=True,
                      dedupe=dedupe)


def scan_module_states(log_paths, trials=200, dedupe=True):
    """Scan pooled signal rows with the shared pair gate and family null.

    ``dedupe=True`` removes dependent-column aliases before the family null;
    ``dedupe=False`` restores the raw family and is the executable ablation.
    """
    rows = pool_signals(log_paths)
    target = [row[-1] for row in rows]
    return scan_pairs(rows, target, trials=trials, family_wise=True,
                      dedupe=dedupe)


def _split_blocks(rows, target, trials=200, unique=True, dedupe=True):
    positive = interactions(rows, target, trials=trials, dedupe=dedupe)
    anti = anti_interactions(rows, target, trials=trials, dedupe=dedupe)
    if unique:
        classes = column_classes(rows)
        positive = unique_pairs(positive, classes)
        anti = unique_pairs(anti, classes)
    return {
        "module": [report for report in positive if module_pair(report)],
        "world": [report for report in positive if world_pair(report)],
        "anti_module": [report for report in anti if module_pair(report)],
        "anti_world": [report for report in anti if world_pair(report)],
    }


def scan_module_state_blocks(log_paths, trials=200, unique=True, dedupe=True):
    """Return the pooled log signal scan split into positive and anti pairs.

    ``unique=True`` collapses dependent-column aliases before the block
    split, matching the signed replication path; ``unique=False`` restores
    the raw entries.
    """
    log_paths = list(log_paths)
    rows = pool_signals(log_paths)
    result = _split_blocks(rows, [row[-1] for row in rows],
                           trials=trials, unique=unique, dedupe=dedupe)
    result["metadata"] = (read_signal_metadata(log_paths[0])
                          if log_paths else None)
    return result


def scan_trace_blocks(traces, trials=200, unique=True, dedupe=True):
    """Return the in-memory trace signal scan split into positive/anti pairs."""
    traces = list(traces)
    rows = []
    for trace in traces:
        rows.extend(signals_from_trace(trace))
    result = _split_blocks(rows, [row[-1] for row in rows],
                           trials=trials, unique=unique, dedupe=dedupe)
    result["metadata"] = (signals_meta_from_trace(traces[0])
                          if traces else None)
    return result
