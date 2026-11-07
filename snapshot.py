"""Deterministic run snapshots and record-set diffing (lattice transfer).

Adapted from ``lattice/diff.py`` (AegeanWorks/Lattice): records are
matched by ``(record_type, id)``; volatile bookkeeping fields never count
as changes; every added/removed/changed list is sorted. A snapshot is a
portable JSONL file written atomically. Capture imports the agent and
recompute lazily so this module stays a pure data utility.
"""

import hashlib
import json
import os
from pathlib import Path

VOLATILE_FIELDS = frozenset({
    "created_at", "updated_at", "ts", "timestamp", "duration_ms",
    "elapsed_ms", "run_id", "session_id",
})


def run_record(task, seed, trace, stats=None):
    """Build one snapshot record from a task/seed trace and trace stats."""
    reward = sum(float(record.get("reward", 0.0)) for record in trace)
    actions = [record.get("action") for record in trace]
    body = json.dumps(actions, separators=(",", ":"), ensure_ascii=True)
    return {
        "record_type": "run",
        "id": "%s:%d" % (task, int(seed)),
        "task": task,
        "seed": int(seed),
        "steps": len(trace),
        "reward": reward,
        "success": bool(trace) and bool(trace[-1].get("done")) and reward > 0.0,
        "action_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        "syn": float((stats or {}).get("syn", 0.0)),
        "phi": float((stats or {}).get("phi", 0.0)),
    }


def capture_snapshot(cases, directory=None, max_steps=200):
    """Run each ``(task, seed)`` and return sorted run records."""
    from agent import Agent
    from evals.recompute import recompute

    if directory is None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            return capture_snapshot(cases, tmp, max_steps=max_steps)
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    records = []
    for task, seed in cases:
        log_path = root / ("%s-%d.jsonl" % (task, int(seed)))
        if log_path.exists():
            log_path.unlink()
        trace = Agent().run_task_logged(task, seed, max_steps=max_steps,
                                        log_path=str(log_path))
        records.append(run_record(task, seed, trace,
                                  recompute(str(log_path))))
    return sorted(records, key=lambda record: (record["record_type"],
                                               record["id"]))


def export_snapshot(records, path):
    """Write records as sorted JSONL through an atomic replace."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(records, key=lambda record: (record["record_type"],
                                                  record["id"]))
    body = "".join(json.dumps(record, sort_keys=True) + "\n"
                   for record in ordered)
    tmp = target.with_name(target.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(body)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, target)
    _fsync_dir(target.parent)
    return str(target)


def read_snapshot(path):
    """Read a JSONL snapshot into a list of records."""
    records = []
    with open(str(path), "r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line))
    return records


def _index(records):
    indexed = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        record_type = str(record.get("record_type") or record.get("type") or "")
        identifier = str(record.get("id") or "")
        if record_type and identifier:
            indexed[(record_type, identifier)] = record
    return indexed


def diff_records(old_records, new_records):
    """Compare two record sets by ``(record_type, id)``.

    Volatile fields are ignored. Every list is sorted, and the summary
    counts added/removed/changed/unchanged records.
    """
    old = _index(old_records)
    new = _index(new_records)
    added = [{"record_type": key[0], "id": key[1]}
             for key in sorted(set(new) - set(old))]
    removed = [{"record_type": key[0], "id": key[1]}
               for key in sorted(set(old) - set(new))]
    changed = []
    unchanged = 0
    for key in sorted(set(old) & set(new)):
        before, after = old[key], new[key]
        fields = sorted(
            name for name in set(before) | set(after)
            if name not in VOLATILE_FIELDS
            and name not in ("record_type", "id")
            and before.get(name) != after.get(name)
        )
        if fields:
            changed.append({"record_type": key[0], "id": key[1],
                            "fields": fields})
        else:
            unchanged += 1
    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "summary": {
            "added": len(added),
            "removed": len(removed),
            "changed": len(changed),
            "unchanged": unchanged,
        },
    }


def _fsync_dir(path):
    if os.name == "nt":
        return
    try:
        descriptor = os.open(str(path), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:  # hygiene: allow best-effort dir fsync; file replace already done
        pass
    finally:
        os.close(descriptor)
