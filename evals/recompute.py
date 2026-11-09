"""Recompute eval statistics from a JSONL log without trusting self-reports.

Parses telemetry.log schema-2 records (header/action/result/verdict
with M/P/S/hub vectors). Eval signals travel as action records whose
``args`` carry raw arrays:

- kind "eval_samples": args {"trace": [[float, ...], ...],
  "target": [float, ...]}
- kind "eval_decodability": args {"pre": float, "post": float}
- kind "eval_transfer": args {"naive_steps": float, "reuse_steps": float}
- kind "eval_recovery": args {"time_outside": float, "window": float}

Bare records {"trace": [...], "target": [...]} or {"pre","post"} pairs
are also accepted. Scalar keys such as reported_*, syn, phi, gbi, gain,
score are never read: every returned value is recomputed from raw
arrays and vectors via evals.estimators.
"""
import argparse
import json

from evals.estimators import (gbi, phi_ar, recovery, synergy, synergy_scope,
                             synergy_sign, transfer_gain)

_EVAL_KINDS = ("eval_samples", "eval_decodability", "eval_transfer", "eval_recovery")


def _mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


def _numbers(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _vec_row(rec):
    row = []
    args = rec.get("args")
    args_map = args if isinstance(args, dict) else {}
    for key in ("M", "P", "S", "hub"):
        val = rec.get(key)
        if val is None and key in args_map:
            val = args_map.get(key)
        if isinstance(val, (list, tuple)):
            row.extend(v for v in (_numbers(x) for x in val) if v is not None)
        elif isinstance(val, (int, float)) and not isinstance(val, bool):
            row.append(float(val))
    return row


def _handle_eval_payload(args, acc):
    trace = args.get("trace")
    target = args.get("target")
    if isinstance(trace, list) and trace and isinstance(trace[0], list):
        rows = [[float(v) for v in r] for r in trace]
        acc["phi_rows"].extend(rows)
        if isinstance(target, list) and len(target) == len(trace):
            acc["syn_rows"].extend(rows)
            acc["syn_targets"].extend(float(v) for v in target)
    elif isinstance(trace, list) and isinstance(target, list):
        if len(trace) == len(target) and trace and not isinstance(trace[0], list):
            two = [[float(v), 0.0] for v in trace]
            acc["syn_rows"].extend(two)
            acc["syn_targets"].extend(float(v) for v in target)
    if "pre" in args and "post" in args:
        acc["pres"].append(float(args["pre"]))
        acc["posts"].append(float(args["post"]))
    if "naive_steps" in args and "reuse_steps" in args:
        acc["naive"].append(float(args["naive_steps"]))
        acc["reuse"].append(float(args["reuse_steps"]))
    if "time_outside" in args and "window" in args:
        acc["recs"].append(recovery(args["time_outside"], args["window"]))


def recompute(log_path):
    """Read JSONL log and return dict with syn, phi, gbi, gain, recovery."""
    acc = {"phi_rows": [], "syn_rows": [], "syn_targets": [], "pres": [],
           "posts": [], "naive": [], "reuse": [], "recs": []}
    vec_rows = []
    n_records = 0
    with open(log_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(rec, dict):
                continue
            n_records += 1
            if rec.get("type") == "action" and rec.get("kind") in _EVAL_KINDS:
                args = rec.get("args")
                if isinstance(args, dict):
                    _handle_eval_payload(args, acc)
            elif rec.get("type") in ("header", "verdict"):
                pass
            elif "trace" in rec or ("pre" in rec and "post" in rec):
                _handle_eval_payload(rec, acc)
            elif "naive_steps" in rec or "time_outside" in rec:
                _handle_eval_payload(rec, acc)
            row = _vec_row(rec)
            if row:
                vec_rows.append(row)
    phi_rows = acc["phi_rows"] or vec_rows
    width = max((len(r) for r in phi_rows), default=0)
    if phi_rows and any(len(r) != width for r in phi_rows):
        phi_rows = [r + [0.0] * (width - len(r)) for r in phi_rows]
    if acc["syn_rows"]:
        syn_trace, syn_targets = acc["syn_rows"], acc["syn_targets"]
        syn, syn_n = synergy(syn_trace, syn_targets)
    elif vec_rows and len(vec_rows) >= 2:
        w2 = max(len(r) for r in vec_rows)
        if w2 >= 2:
            padded_v = [list(r) + [0.0] * (w2 - len(r)) for r in vec_rows]
            syn_trace, syn_targets = [r[:-1] for r in padded_v], [r[-1] for r in padded_v]
            syn, syn_n = synergy(syn_trace, syn_targets)
        else:
            syn_trace, syn_targets = [], []
            syn, syn_n = (0.0, 0.0)
    else:
        syn_trace, syn_targets = [], []
        syn, syn_n = (0.0, 0.0)
    return {
        "syn": syn,
        "syn_n": syn_n,
        "syn_sign": synergy_sign(syn, syn_n),
        "syn_scope": synergy_scope(syn_trace, syn_targets),
        "phi": phi_ar(phi_rows) if len(phi_rows) >= 3 else 0.0,
        "gbi": gbi(_mean(acc["pres"]), _mean(acc["posts"])) if acc["pres"] else 0.0,
        "gain": transfer_gain(_mean(acc["naive"]), _mean(acc["reuse"])) if acc["naive"] else 0.0,
        "recovery": _mean(acc["recs"]) if acc["recs"] else 0.0,
        "n_records": n_records,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    args = ap.parse_args()
    print(json.dumps(recompute(args.log), sort_keys=True))


if __name__ == "__main__":
    main()
