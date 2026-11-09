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
import time
from pathlib import Path

VOLATILE_FIELDS = frozenset({
    "created_at", "updated_at", "ts", "timestamp", "duration_ms",
    "elapsed_ms", "run_id", "session_id", "captured_at",
})


def run_record(task, seed, trace, stats=None):
    """Build one snapshot record from a task/seed trace and trace stats.

    Besides the behavior quadruple (steps/reward/success/action hash) and
    the two estimators, the record carries the integrity evidence a diff
    must be able to see: the synergy column scope, whether the actions
    replayed through the named world, and the verdict's parsed claim.
    Each is ``None`` when the caller supplied no such evidence.
    """
    stats = stats or {}
    reward = sum(float(record.get("reward", 0.0)) for record in trace)
    actions = [record.get("action") for record in trace]
    body = json.dumps(actions, separators=(",", ":"), ensure_ascii=True)
    replay = stats.get("replay")
    return {
        "record_type": "run",
        "id": "%s:%d" % (task, int(seed)),
        "task": task,
        "seed": int(seed),
        "steps": len(trace),
        "reward": reward,
        "success": bool(trace) and bool(trace[-1].get("done")) and reward > 0.0,
        "action_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        "syn": float(stats.get("syn", 0.0)),
        "syn_sign": stats.get("syn_sign"),
        "phi": float(stats.get("phi", 0.0)),
        "syn_scope": stats.get("syn_scope"),
        "replay_ok": None if replay is None else bool(replay.get("ok")),
        "verdict_claimed": None if replay is None else replay.get("claimed"),
        "captured_at": time.time(),
    }


def capture_snapshot(cases, directory=None, max_steps=200):
    """Run each ``(task, seed)`` and return sorted run records.

    Each record carries the integrity evidence the diff gate must see:
    the recomputed synergy scope and the replayed trajectory's verdict
    check, both taken from the log this capture just wrote.
    """
    from agent import Agent
    from episode_replay import verify_action_replay
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
        stats = recompute(str(log_path))
        stats["replay"] = verify_action_replay(str(log_path),
                                               check_verdict=True)
        records.append(run_record(task, seed, trace, stats))
    return sorted(records, key=lambda record: (record["record_type"],
                                               record["id"]))


def export_snapshot(records, path, meta_path=None):
    """Write records as sorted JSONL through an atomic replace."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(records, key=lambda record: (record["record_type"],
                                                  record["id"]))
    body = "".join(json.dumps(record, sort_keys=True) + "\n"
                   for record in ordered)
    _write_atomic(target, body)
    if meta_path is not None:
        write_snapshot_meta(records, meta_path)
    return str(target)


def _write_atomic(target, body):
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(body)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, target)
    _fsync_dir(target.parent)


def read_snapshot(path):
    """Read a JSONL snapshot into a list of records."""
    records = []
    with open(str(path), "r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line))
    return records


def _clean(value):
    if isinstance(value, dict):
        return {
            key: _clean(item)
            for key, item in value.items()
            if str(key).lower() not in VOLATILE_FIELDS
        }
    if isinstance(value, (list, tuple)):
        return [_clean(item) for item in value]
    return value


def _ordered(records):
    return sorted(
        records,
        key=lambda record: (
            str(record.get("record_type") or record.get("type") or ""),
            str(record.get("id") or ""),
            json.dumps(record, sort_keys=True, separators=(",", ":")),
        ),
    )


def _digest(records):
    body = "\n".join(json.dumps(record, sort_keys=True, separators=(",", ":"))
                     for record in _ordered(records))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def graph_sha256(records):
    """Exact digest of every record, including volatile capture fields."""
    return _digest(records)


def content_sha256(records):
    """Semantic digest with volatile capture fields removed recursively."""
    return _digest([_clean(record) for record in records])


def snapshot_digests(records):
    """Return record count, exact graph digest and semantic content digest."""
    records = list(records)
    return {
        "records": len(records),
        "graph_sha256": graph_sha256(records),
        "content_sha256": content_sha256(records),
    }


def write_snapshot_meta(records, meta_path):
    """Write the digest metadata as atomic JSON and return it."""
    meta = snapshot_digests(records)
    meta["schema"] = 1
    body = json.dumps(meta, sort_keys=True) + "\n"
    _write_atomic(Path(meta_path), body)
    return meta


def verify_snapshot(path, meta_path=None):
    """Verify a snapshot against its meta record count and digests."""
    target = Path(meta_path) if meta_path is not None else Path(str(path) + ".meta")
    if not target.exists():
        return {"ok": False, "findings": ["missing-meta"]}
    try:
        meta = json.loads(target.read_text(encoding="utf-8"))
        records = read_snapshot(path)
    except (OSError, ValueError) as exc:
        return {"ok": False, "findings": ["invalid-meta: %s" % exc]}
    current = snapshot_digests(records)
    findings = []
    if meta.get("records") != current["records"]:
        findings.append("record-count:%s!=%s"
                        % (meta.get("records"), current["records"]))
    if meta.get("graph_sha256") != current["graph_sha256"]:
        findings.append("graph-mismatch")
    if meta.get("content_sha256") != current["content_sha256"]:
        findings.append("content-mismatch")
    return {
        "ok": not findings,
        "findings": findings,
        "records": current["records"],
        "graph_sha256": current["graph_sha256"],
        "content_sha256": current["content_sha256"],
    }


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
