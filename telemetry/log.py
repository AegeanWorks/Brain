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
truncated tail, a mismatched witness, or a missing anchor. An optional
anchor journal (``append_anchor``/``verify_anchor_journal``) chains
each run's anchor to the previous anchor hash, so a deleted or rewound
middle anchor is named; ``verify_chain(path, journal_path=...)``
compares the log with the latest journal anchor. Optional HMAC-SHA256
signing (``Telemetry(path, hmac_key=bytes)`` and
``verify_chain(path, hmac_key=...)``) adds a keyed ``mac`` to every
record; missing or bad MACs are named, and unkeyed logs stay
byte-compatible. Keys come from outside the repository.

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
import hmac
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
    body = {k: v for k, v in record.items() if k not in ("digest", "mac")}
    return hashlib.sha256(_canonical(body)).hexdigest()


def _mac_of(record, key):
    """HMAC-SHA256 over the canonical record without its ``mac`` field."""
    body = {k: v for k, v in record.items() if k != "mac"}
    return hmac.new(key, _canonical(body), hashlib.sha256).hexdigest()


def _last_nonempty_line(path, chunk_size=65536):
    """Return the last non-empty line, reading backward from the file tail.

    Adapted from ``assay/storage.py`` (AegeanWorks/assay, AL-1.1). The
    bounded binary scan avoids reading a whole JSONL log just to find
    the previous digest when a fresh writer resumes it.
    """
    chunk_size = max(256, int(chunk_size))
    # hygiene: allow binary tail read; bytes are decoded as UTF-8 below
    with Path(path).open("rb") as handle:
        handle.seek(0, os.SEEK_END)
        end = handle.tell()
        buffer = b""
        while end > 0:
            start = max(0, end - chunk_size)
            handle.seek(start)
            buffer = handle.read(end - start) + buffer
            trimmed = buffer.rstrip(b"\r\n")
            lines = [line for line in trimmed.splitlines() if line.strip()]
            if lines and (start == 0 or b"\n" in trimmed):
                return lines[-1].decode("utf-8")
            end = start
    return ""


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
    ``hmac_key`` (non-empty bytes) signs every record with HMAC-SHA256;
    ``None`` keeps the unkeyed format and bytes unchanged.
    """

    def __init__(self, path, lock_timeout=3.0, hmac_key=None):
        if (isinstance(lock_timeout, bool)
                or not isinstance(lock_timeout, (int, float))
                or lock_timeout < 0):
            raise ValueError(
                "Why: lock_timeout must be a non-negative number. "
                "Fix: pass lock_timeout=3.0.")
        if hmac_key is not None:
            if (not isinstance(hmac_key, (bytes, bytearray))
                    or not hmac_key):
                raise ValueError(
                    "Why: hmac_key must be non-empty bytes or None. "
                    "Fix: pass a verifier-held bytes key, or omit it.")
            hmac_key = bytes(hmac_key)
        self.path = Path(path)
        parent = self.path.parent
        if str(parent) and str(parent) not in ("", "."):
            parent.mkdir(parents=True, exist_ok=True)
        self.lock_timeout = float(lock_timeout)
        self._hmac_key = hmac_key
        self._head = None
        self._head_size = None

    def _head_digest(self):
        """Return the digest new records must link to.

        In-memory head when this instance has written; otherwise the
        last chained digest already on disk; ``GENESIS`` for a new log.
        A legacy tail without a digest still anchors the next record:
        the raw line's sha256, so the break is attributable. Only the
        final line is read from disk, so a fresh writer does not scan
        the whole log.
        """
        if self._head is not None:
            return self._head
        if not self.path.exists():
            return GENESIS
        try:
            last_raw = _last_nonempty_line(self.path)
        except OSError:
            return GENESIS
        if not last_raw:
            return GENESIS
        last_digest = None
        try:
            last_digest = json.loads(last_raw).get("digest")
        except ValueError:
            last_digest = None
        if last_digest is not None:
            return last_digest
        try:
            with open(self.path, "rb") as handle:
                handle.seek(0, os.SEEK_END)
                terminated = handle.tell() > 0
                if terminated:
                    handle.seek(-1, os.SEEK_END)
                    terminated = handle.read(1) in (b"\n", b"\r")
        except OSError:
            terminated = False
        raw = last_raw + ("\n" if terminated else "")
        return "LEGACY:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _write_record(self, record):
        record = dict(record)
        record.pop("mac", None)
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
            if self._hmac_key is not None:
                record["mac"] = _mac_of(record, self._hmac_key)
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

    def write_anchor_journal(self, journal_path=None, created_at=None):
        """Append the current log head/count to an anchor journal.

        Each journal record commits to the previous anchor hash, so
        deleting or rewinding a middle anchor is detectable. The
        single-anchor API is unchanged.
        """
        records = self.read_all()
        head = GENESIS
        for record in reversed(records):
            value = record.get("digest") if isinstance(record, dict) else None
            if isinstance(value, str):
                head = value
                break
        return append_anchor(self.path, head, len(records),
                             journal_path=journal_path,
                             created_at=created_at)

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


ANCHOR_JOURNAL_SCHEMA = 1
_ANCHOR_FIELDS = frozenset(
    {"schema", "ledger", "seq", "head", "created_at", "prev", "hash"})


def _anchor_journal_path(path):
    return Path(str(path) + ".anchors")


def _valid_digest(value):
    return (isinstance(value, str) and len(value) == 64
            and all(ch in "0123456789abcdef" for ch in value))


def _anchor_payload(record):
    return _canonical({key: record[key] for key in
                       ("schema", "ledger", "seq", "head", "created_at",
                        "prev")})


def _anchor_hash(record):
    return hashlib.sha256(_anchor_payload(record)).hexdigest()


def _validate_anchor_record(value, line_number=0):
    """Validate one journal record; raise ValueError with a named defect."""
    if not isinstance(value, dict):
        raise ValueError("anchor %d is not an object" % line_number)
    unknown = set(value) - _ANCHOR_FIELDS
    missing = _ANCHOR_FIELDS - set(value)
    if unknown:
        raise ValueError("anchor %d has unknown fields: %s"
                         % (line_number, sorted(unknown)))
    if missing:
        raise ValueError("anchor %d is missing fields: %s"
                         % (line_number, sorted(missing)))
    if value["schema"] != ANCHOR_JOURNAL_SCHEMA:
        raise ValueError("anchor %d has unsupported schema" % line_number)
    ledger = value["ledger"]
    if (not isinstance(ledger, str) or not ledger
            or any(ord(ch) < 32 for ch in ledger)):
        raise ValueError("anchor %d has an invalid ledger label" % line_number)
    seq = value["seq"]
    if isinstance(seq, bool) or not isinstance(seq, int) or seq < 0:
        raise ValueError("anchor %d has an invalid seq" % line_number)
    head = value["head"]
    if not (head == GENESIS and seq == 0) and not _valid_digest(head):
        raise ValueError("anchor %d has an invalid head" % line_number)
    prev = value["prev"]
    if prev != GENESIS and not _valid_digest(prev):
        raise ValueError("anchor %d has an invalid prev" % line_number)
    created_at = value["created_at"]
    if not isinstance(created_at, str) or not created_at:
        raise ValueError("anchor %d has an invalid created_at" % line_number)
    stored = value["hash"]
    if stored != _anchor_hash(value):
        raise ValueError("anchor %d hash does not match its payload"
                         % line_number)
    return dict(value)


def append_anchor(path, head, records, journal_path=None, created_at=None):
    """Append one anchor to a JSONL journal and return the stored record.

    ``head`` is the log's last digest and ``records`` its record count.
    The previous anchor hash is read from the journal tail; a seq that
    moves backwards is refused. The single-line append is fsynced and
    the containing directory is fsynced where the platform allows it.
    """
    if not (head == GENESIS and records == 0) and not _valid_digest(head):
        raise ValueError("head must be a lowercase SHA-256 digest")
    if isinstance(records, bool) or not isinstance(records, int) or records < 0:
        raise ValueError("records must be a non-negative integer")
    target = (Path(journal_path) if journal_path is not None
              else _anchor_journal_path(path))
    target.parent.mkdir(parents=True, exist_ok=True)
    prev = GENESIS
    last_seq = -1
    if target.exists():
        try:
            tail = _last_nonempty_line(target)
        except OSError as exc:
            raise ValueError("anchor journal tail is unreadable: %s" % exc)
        if tail:
            try:
                value = json.loads(tail)
            except ValueError:
                raise ValueError("anchor journal tail is not valid JSON")
            anchor = _validate_anchor_record(value)
            prev = anchor["hash"]
            last_seq = anchor["seq"]
    if records < last_seq:
        raise ValueError("anchor seq %d moves backwards from %d"
                         % (records, last_seq))
    stamp = created_at or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    record = {
        "schema": ANCHOR_JOURNAL_SCHEMA,
        "ledger": Path(str(path)).name,
        "seq": records,
        "head": head,
        "created_at": stamp,
        "prev": prev,
    }
    record["hash"] = _anchor_hash(record)
    line = json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
    with open(target, "a", encoding="utf-8", newline="\n") as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())
    _dir_fsync(target.parent)
    return record


def verify_anchor_journal(journal_path):
    """Verify every anchor's hash and its link to the previous anchor."""
    target = Path(journal_path)
    if not target.exists():
        return {"ok": False, "anchors": 0, "head": None,
                "latest": None, "errors": ["missing-journal"]}
    try:
        lines = target.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return {"ok": False, "anchors": 0, "head": None,
                "latest": None, "errors": ["unreadable-journal: %s" % exc]}
    errors = []
    records = []
    expected_prev = GENESIS
    last_seq = -1
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except ValueError:
            errors.append("line %d: invalid JSON" % number)
            continue
        try:
            anchor = _validate_anchor_record(value, number)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if anchor["prev"] != expected_prev:
            errors.append("line %d: prev does not match the previous anchor"
                          % number)
        if anchor["seq"] < last_seq:
            errors.append("line %d: seq %d moves backwards from %d"
                          % (number, anchor["seq"], last_seq))
        records.append(anchor)
        expected_prev = anchor["hash"]
        last_seq = max(last_seq, anchor["seq"])
    if not records and not errors:
        errors.append("empty-journal")
    latest = records[-1] if records else None
    return {"ok": not errors, "anchors": len(records),
            "head": latest["hash"] if latest else None,
            "latest": latest, "errors": errors}


def verify_chain(path, anchor_path=None, journal_path=None, hmac_key=None):
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
    ``missing-anchor``.

    When ``journal_path`` is given, the journal itself is verified first
    (``anchor-journal:<error>`` on failure), then the log must match the
    latest anchor: a shorter log is ``truncated-tail``, and a different
    head/count is ``anchor-mismatch``. Without an anchor or journal, a
    truncated prefix remains internally valid by design.

    When ``hmac_key`` is given, every record must carry a matching
    HMAC-SHA256 ``mac``; missing or bad MACs are ``missing-mac:<index>``
    and ``bad-mac:<index>``. Without a key the MAC is not checked, so an
    unkeyed log remains byte-compatible.
    """
    if hmac_key is not None:
        if not isinstance(hmac_key, (bytes, bytearray)) or not hmac_key:
            raise ValueError(
                "Why: hmac_key must be non-empty bytes or None. "
                "Fix: pass a verifier-held bytes key, or omit it.")
        hmac_key = bytes(hmac_key)
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
        if hmac_key is not None:
            mac = record.get("mac")
            if not isinstance(mac, str):
                findings.append("missing-mac:%d" % index)
            elif not hmac.compare_digest(mac, _mac_of(record, hmac_key)):
                findings.append("bad-mac:%d" % index)
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
    if journal_path is not None:
        journal = verify_anchor_journal(journal_path)
        if not journal["ok"]:
            for error in journal["errors"]:
                findings.append("anchor-journal:%s" % error)
        else:
            latest = journal["latest"]
            empty_genesis = (count == 0 and latest["seq"] == 0
                             and latest["head"] == GENESIS)
            if not empty_genesis and count < latest["seq"]:
                findings.append("truncated-tail:%d<%d" % (count, latest["seq"]))
            elif not empty_genesis and (
                    count != latest["seq"] or head != latest["head"]):
                findings.append("anchor-mismatch")
    return {"ok": not findings, "findings": findings,
            "records": count, "head": head}
