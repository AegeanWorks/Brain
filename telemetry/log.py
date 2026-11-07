"""Append-only JSONL record store, schema 2.

Record model: every line is one JSON object with keys
``seq``, ``type``, ``ts``, ``M``, ``P``, ``S``, ``hub`` plus ``schema`` (=2)
and type-specific payload keys.

Tamper evidence (Assay transfer): every record carries ``prev`` (the
previous record's digest, ``"GENESIS"`` for the first record of a new
log) and ``digest`` (SHA-256 over the canonical JSON of the record
without ``digest``). ``verify_chain`` recomputes the chain and names
the defect (edited / deleted / reordered / unchained / corrupt), so a
hand-edited log fails loudly instead of reading back silently. A
terminal anchor sidecar (``write_anchor``) records the final head and
record count; ``verify_chain(path, anchor_path=...)`` also reports a
truncated tail, a mismatched witness, or a missing anchor.

Durability: each append writes one line, calls ``flush`` + ``os.fsync``
on the file descriptor, then fsyncs the containing directory when the
platform permits. Callers record an action with ``append_action`` before
executing the corresponding operation, so a crash leaves the intended
operation in the log.

Multi-writer safety: each append holds an advisory lock file from the
head read through the durable write, so concurrent writers form one
chain instead of linking to the same stale head. A lock older than
``LOCK_STALE_SECONDS`` is treated as a crashed writer and broken via an
atomic rename. This mirrors AIKit's ``file_lock`` discipline.
"""

import contextlib
import hashlib
import json
import os
import time
from pathlib import Path

SCHEMA_VERSION = 2
GENESIS = "GENESIS"
LOCK_STALE_SECONDS = 30.0
LOCK_POLL_SECONDS = 0.02


@contextlib.contextmanager
def _append_lock(path, timeout_seconds=3.0):
    """Hold an exclusive advisory lock for one telemetry append.

    Adapted from AIKit's task-ledger/registry ``file_lock``: an
    ``O_CREAT|O_EXCL`` lock file with the PID and timestamp serialises
    writers across processes and threads. A lock older than
    ``LOCK_STALE_SECONDS`` is stolen by an atomic rename, so exactly one
    racer can break it. A bounded timeout raises instead of hanging or
    writing unprotected.
    """
    lock_path = Path(str(path) + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + max(0.0, float(timeout_seconds))
    acquired = False
    while True:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write("%d:%d\n" % (os.getpid(), int(time.time())))
                handle.flush()
            acquired = True
            break
        except PermissionError:
            # Windows raises EACCES while another process removes its
            # lock; treat it as contention and retry.
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    "Why: another writer holds the telemetry lock on %s. "
                    "Fix: retry after it finishes, or remove %s if no "
                    "writer is active." % (Path(path).name, lock_path.name))
            time.sleep(LOCK_POLL_SECONDS)
        except FileExistsError:
            try:
                age = time.time() - lock_path.stat().st_mtime
                if age > LOCK_STALE_SECONDS:
                    claim = Path(str(lock_path) + ".steal_%d" % os.getpid())
                    try:
                        os.replace(lock_path, claim)
                    except OSError:  # hygiene: allow another stale-lock breaker won the rename
                        pass
                    else:
                        try:
                            claim.unlink(missing_ok=True)
                        except OSError:  # hygiene: allow best-effort claim cleanup; the retry loop continues
                            pass
                        continue
            except OSError:  # hygiene: allow lock stat race; the retry loop handles it
                pass
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    "Why: another writer holds the telemetry lock on %s. "
                    "Fix: retry after it finishes, or remove %s if no "
                    "writer is active." % (Path(path).name, lock_path.name))
            time.sleep(LOCK_POLL_SECONDS)
    try:
        yield
    finally:
        if acquired:
            try:
                lock_path.unlink(missing_ok=True)
            except OSError:  # hygiene: allow best-effort lock release; a stale lock is broken by age
                pass


def _canonical(record):
    return json.dumps(record, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True).encode("utf-8")


def _digest_of(record):
    body = {k: v for k, v in record.items() if k != "digest"}
    return hashlib.sha256(_canonical(body)).hexdigest()


def sha256_file(path):
    """Return hex sha256 of file bytes at ``path``."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _dir_fsync(dir_path):
    """Fsync directory entry for ``dir_path``; no-op where unsupported."""
    try:
        fd = os.open(str(dir_path), os.O_RDONLY)
    except OSError:
        return
    try:
        try:
            os.fsync(fd)
        except OSError:  # hygiene: allow best-effort dir fsync; data already flushed
            pass
    finally:
        os.close(fd)


class Telemetry:
    """JSONL append-only store at ``path``.

    ``lock_timeout`` bounds how long one append waits for another
    writer's advisory lock before raising ``TimeoutError``. A lock older
    than ``LOCK_STALE_SECONDS`` is treated as a crashed writer.
    """

    def __init__(self, path, lock_timeout=3.0):
        if (isinstance(lock_timeout, bool)
                or not isinstance(lock_timeout, (int, float))
                or lock_timeout < 0):
            raise ValueError(
                "Why: lock_timeout must be a non-negative number. "
                "Fix: pass lock_timeout=3.0.")
        self.path = Path(path)
        parent = self.path.parent
        if str(parent) and str(parent) not in ("", "."):
            parent.mkdir(parents=True, exist_ok=True)
        self.lock_timeout = float(lock_timeout)
        self._head = None
        self._head_size = None

    def _head_digest(self):
        """Return the digest new records must link to.

        In-memory head when this instance has written; otherwise the
        last chained digest already on disk; ``GENESIS`` for a new log.
        A legacy tail without a digest still anchors the next record:
        the raw line's sha256, so the break is attributable.
        """
        if self._head is not None:
            return self._head
        if not self.path.exists():
            return GENESIS
        last_raw = None
        last_digest = None
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        last_raw = line
                        try:
                            last_digest = json.loads(line).get("digest")
                        except ValueError:
                            last_digest = None
        except OSError:
            return GENESIS
        if last_digest is not None:
            return last_digest
        if last_raw is not None:
            return "LEGACY:" + hashlib.sha256(last_raw.encode("utf-8")).hexdigest()
        return GENESIS

    def _write_record(self, record):
        record = dict(record)
        record.setdefault("schema", SCHEMA_VERSION)
        for key in ("seq", "type", "ts", "M", "P", "S", "hub"):
            record.setdefault(key, None)
        with _append_lock(self.path, timeout_seconds=self.lock_timeout):
            try:
                size = self.path.stat().st_size
            except OSError:
                size = 0
            if self._head_size != size:
                self._head = None
            record["prev"] = self._head_digest()
            record["digest"] = _digest_of(record)
            line = json.dumps(record, sort_keys=True) + "\n"
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(line)
                f.flush()
                os.fsync(f.fileno())
            try:
                _dir_fsync(self.path.parent)
            except OSError:  # hygiene: allow best-effort dir fsync; record already flushed
                pass
            self._head = record["digest"]
            try:
                self._head_size = self.path.stat().st_size
            except OSError:
                self._head_size = None
        return record

    def write_header(self, task, budget, manifest_sha256=None, manifest_path=None,
                     policy=None, policy_sha256=None, model=None):
        """Write header record (seq 0) describing task and budget.

        ``manifest_sha256`` is stored verbatim when given. When
        ``manifest_path`` is given and ``manifest_sha256`` is None, the
        sha256 of that file is computed and stored. ``policy``,
        ``policy_sha256`` and ``model`` cite the producing configuration
        (Assay-style per-record policy binding); all are stored
        verbatim when given.
        """
        if manifest_sha256 is None and manifest_path is not None:
            manifest_sha256 = sha256_file(manifest_path)
        return self._write_record(
            {
                "schema": SCHEMA_VERSION,
                "seq": 0,
                "type": "header",
                "ts": time.time(),
                "task": task,
                "budget": budget,
                "manifest_sha256": manifest_sha256,
                "policy": policy,
                "policy_sha256": policy_sha256,
                "model": model,
                "M": None,
                "P": None,
                "S": None,
                "hub": None,
            }
        )

    def append_action(self, seq, kind, args, M=None, P=None, S=None, hub=None):
        """Record an action before it executes.

        Call this method first, then execute the operation. The flush +
        os.fsync + directory fsync sequence completes before return, so
        the record is durable prior to execution.
        """
        return self._write_record(
            {
                "schema": SCHEMA_VERSION,
                "seq": seq,
                "type": "action",
                "ts": time.time(),
                "kind": kind,
                "args": args,
                "M": M,
                "P": P,
                "S": S,
                "hub": hub,
            }
        )

    def append_result(self, seq, ok, output, cost, M=None, P=None, S=None, hub=None):
        """Record the result for a prior action ``seq``."""
        return self._write_record(
            {
                "schema": SCHEMA_VERSION,
                "seq": seq,
                "type": "result",
                "ts": time.time(),
                "ok": bool(ok),
                "output": output,
                "cost": cost,
                "M": M,
                "P": P,
                "S": S,
                "hub": hub,
            }
        )

    def write_verdict(self, verdict, reason, seq=-1):
        """Write terminal verdict record."""
        return self._write_record(
            {
                "schema": SCHEMA_VERSION,
                "seq": seq,
                "type": "verdict",
                "ts": time.time(),
                "verdict": verdict,
                "reason": reason,
                "M": None,
                "P": None,
                "S": None,
                "hub": None,
            }
        )

    def write_anchor(self, anchor_path=None):
        """Write a head/count witness for the current log.

        The sidecar is written atomically and is not part of the chain;
        ``verify_chain(path, anchor_path=...)`` compares against it.
        """
        records = self.read_all()
        head = GENESIS
        for record in reversed(records):
            value = record.get("digest") if isinstance(record, dict) else None
            if isinstance(value, str):
                head = value
                break
        return write_anchor(self.path, head, len(records),
                            anchor_path=anchor_path)

    def read_all(self):
        """Return list of decoded JSON objects in file order."""
        if not self.path.exists():
            return []
        out = []
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    out.append(json.loads(line))
        return out

    def bins(self, step_ms=50):
        """Group records into fixed time bins from first timestamp.

        Returns a list of mappings with keys ``bin``, ``count``,
        ``start`` and ``end``, ordered by ``bin``. ``step_ms`` is the
        bin width in milliseconds and must be positive.
        """
        step = float(step_ms)
        if step <= 0:
            raise ValueError("step_ms must be positive")
        records = self.read_all()
        if not records:
            return []
        width = step / 1000.0
        t0 = records[0].get("ts", 0.0)
        groups = {}
        for rec in records:
            ts = rec.get("ts", t0)
            index = int((ts - t0) // width)
            if index < 0:
                index = 0
            groups[index] = groups.get(index, 0) + 1
        result = []
        for index in sorted(groups):
            start = t0 + index * width
            result.append(
                {"bin": index, "count": groups[index], "start": start, "end": start + width}
            )
        return result


def _anchor_path(path):
    return Path(str(path) + ".anchor")


def write_anchor(path, head, records, anchor_path=None):
    """Write a terminal head/count witness beside the log.

    The anchor is a separate JSON sidecar; it is written atomically with
    its own fsync and directory fsync. It is not part of the hash chain,
    so callers must keep it outside the tampered log's control (the
    anchored verifier reports a missing or mismatched witness).
    """
    target = Path(anchor_path) if anchor_path is not None else _anchor_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps({"head": str(head), "records": int(records)},
                      sort_keys=True) + "\n"
    tmp = target.with_name(target.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write(body)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, target)
    _dir_fsync(target.parent)
    return str(target)


def read_anchor(anchor_path):
    """Return the decoded anchor mapping, or None when missing/malformed."""
    try:
        with open(str(anchor_path), "r", encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, ValueError):
        return None
    if not isinstance(value, dict):
        return None
    head = value.get("head")
    records = value.get("records")
    if not isinstance(head, str):
        return None
    if isinstance(records, bool) or not isinstance(records, int):
        return None
    return {"head": head, "records": records}


def verify_chain(path, anchor_path=None):
    """Verify the hash chain of the JSONL log at ``path``.

    Returns ``{"ok": bool, "findings": [...], "records": n, "head": hex|None}``.
    Findings name the first defect class found per line:
    ``corrupt-line`` (not JSON), ``unchained-record`` (no digest/prev),
    ``edited-record`` (digest mismatch), ``reordered-record`` (prev links
    a non-adjacent digest), else ``broken-link`` (prev matches nothing:
    deletion or edited prefix). Sequence numbers are intentionally not
    checked: actions/results legitimately share a seq and the verdict
    uses -1; order is carried by the chain, not by seq.

    When ``anchor_path`` is given, the verified head and record count
    must match the separate ``write_anchor`` witness. A shorter log is
    ``truncated-tail:<count><<anchor_count>``; a different head/count is
    ``anchor-mismatch``; a missing or malformed witness is
    ``missing-anchor``. Without an anchor, a truncated prefix remains
    internally valid by design.
    """
    findings = []
    digests = []
    head = None
    count = 0
    try:
        with open(str(path), "r", encoding="utf-8") as f:
            lines = [ln for ln in f if ln.strip()]
    except OSError as exc:
        return {"ok": False, "findings": ["unreadable-log: %s" % exc],
                "records": 0, "head": None}
    for index, line in enumerate(lines):
        try:
            record = json.loads(line)
        except ValueError:
            findings.append("corrupt-line:%d" % index)
            continue
        if not isinstance(record, dict) or "digest" not in record or "prev" not in record:
            findings.append("unchained-record:%d" % index)
            continue
        if record["digest"] != _digest_of(record):
            findings.append("edited-record:%d" % index)
            continue
        want = digests[-1] if digests else GENESIS
        if record["prev"] != want and not (
                not digests and isinstance(record["prev"], str)
                and record["prev"].startswith("LEGACY:")):
            if record["prev"] in digests:
                findings.append("reordered-record:%d" % index)
            else:
                later = False
                for future in lines[index + 1:]:
                    try:
                        future_digest = json.loads(future).get("digest")
                    except ValueError:
                        future_digest = None
                    if future_digest is not None and record["prev"] == future_digest:
                        later = True
                        break
                if later:
                    findings.append("reordered-record:%d" % index)
                else:
                    findings.append("broken-link:%d" % index)
            continue
        digests.append(record["digest"])
        head = record["digest"]
        count += 1
    if anchor_path is not None:
        anchor = read_anchor(anchor_path)
        if anchor is None:
            findings.append("missing-anchor")
        elif count < anchor["records"]:
            findings.append("truncated-tail:%d<%d" % (count, anchor["records"]))
        elif count != anchor["records"] or head != anchor["head"]:
            findings.append("anchor-mismatch")
    return {"ok": not findings, "findings": findings,
            "records": count, "head": head}
