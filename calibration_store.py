"""Append-only calibration forecast journal with per-record checksums.

Forecasts are immutable observations; ``calibration.summary`` scores
whatever list it is given, but forecasts from earlier processes are
lost. This store appends one checksummed JSONL record per forecast under
an advisory lock, refuses duplicate ids, and names corrupt lines on
verification. Scoring stays in ``calibration.summary``. An optional
HMAC-SHA256 per record binds the journal to a caller-held key; the
checksum alone detects accidental edits.
"""

import hashlib
import hmac
import json
import os
import shutil
import time
from contextlib import contextmanager
from pathlib import Path

RECORD_SCHEMA = 1
LOCK_STALE_SECONDS = 30.0
LOCK_POLL_SECONDS = 0.02
MIN_FREE_BYTES = 10 * 1024 * 1024
_RECORD_FIELDS = frozenset(
    {"schema", "id", "probability", "outcome", "at", "sha256"})
_OPTIONAL_FIELDS = frozenset({"mac"})
_INPUT_FIELDS = frozenset({"id", "probability", "outcome", "at"})


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True)


def _valid_digest(value):
    return (isinstance(value, str) and len(value) == 64
            and all(ch in "0123456789abcdef" for ch in value))


def _record_digest(record):
    body = {key: value for key, value in record.items()
            if key not in ("sha256", "mac")}
    return hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()


def _record_mac(record, key):
    body = {name: value for name, value in record.items() if name != "mac"}
    return hmac.new(key, _canonical(body).encode("utf-8"),
                    hashlib.sha256).hexdigest()


def _validate_hmac_key(value):
    if value is None:
        return None
    if not isinstance(value, (bytes, bytearray)) or not value:
        raise ValueError(
            "Why: hmac_key must be non-empty bytes or None. "
            "Fix: pass the verifier-held bytes key, or omit it.")
    return bytes(value)


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _validate_probability(value):
    if (isinstance(value, bool)
            or not isinstance(value, (int, float))
            or value != value
            or value in (float("inf"), float("-inf"))
            or not 0.0 <= float(value) <= 1.0):
        raise ValueError("probability must be a finite number in [0, 1]")
    return float(value)


def _validate_outcome(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value not in (0, 1):
        raise ValueError("outcome must be 0, 1 or None")
    return value


def _validate_at(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("at must be a non-empty string")
    return value


def _validate_forecast(forecast):
    if not isinstance(forecast, dict):
        raise ValueError("a forecast must be an object")
    unknown = set(forecast) - _INPUT_FIELDS
    if unknown:
        raise ValueError("forecast has unknown fields: %s" % sorted(unknown))
    identifier = forecast.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("a forecast must have a non-empty string id")
    _validate_probability(forecast.get("probability"))
    if "outcome" not in forecast:
        raise ValueError("forecast %s needs an outcome" % identifier)
    _validate_outcome(forecast.get("outcome"))
    if forecast.get("at") is not None:
        _validate_at(forecast.get("at"))
    return forecast


def _validate_record(record):
    """Validate one stored record's schema, fields and checksum."""
    if not isinstance(record, dict):
        raise ValueError("record is not an object")
    missing = _RECORD_FIELDS - set(record)
    if missing:
        raise ValueError("record is missing fields: %s" % sorted(missing))
    unknown = set(record) - _RECORD_FIELDS - _OPTIONAL_FIELDS
    if unknown:
        raise ValueError("record has unknown fields: %s" % sorted(unknown))
    if record["schema"] != RECORD_SCHEMA:
        raise ValueError("unsupported forecast schema")
    identifier = record["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("record id must be a non-empty string")
    _validate_probability(record["probability"])
    _validate_outcome(record["outcome"])
    _validate_at(record["at"])
    digest = record["sha256"]
    if not _valid_digest(digest):
        raise ValueError("checksum must be a lowercase SHA-256 digest")
    mac = record.get("mac")
    if mac is not None and not _valid_digest(mac):
        raise ValueError("MAC must be a lowercase SHA-256 digest")
    if digest != _record_digest(record):
        raise ValueError("checksum does not match the record")
    return dict(record)


def _seal(forecast, at, hmac_key=None):
    record = {
        "schema": RECORD_SCHEMA,
        "id": forecast["id"],
        "probability": float(forecast["probability"]),
        "outcome": forecast.get("outcome"),
        "at": forecast.get("at") or at,
    }
    record["sha256"] = _record_digest(record)
    if hmac_key is not None:
        record["mac"] = _record_mac(record, hmac_key)
    return record


def _read_records(path, hmac_key=None):
    target = Path(path)
    if not target.exists():
        return [], []
    try:
        lines = target.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [], ["unreadable-store: %s" % exc]
    records = []
    findings = []
    seen = set()
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except ValueError:
            findings.append("line %d: invalid JSON" % number)
            continue
        try:
            record = _validate_record(value)
        except ValueError as exc:
            findings.append("line %d: %s" % (number, exc))
            continue
        if hmac_key is not None:
            stored = record.get("mac")
            if stored is None:
                findings.append("line %d: record is missing its MAC" % number)
                continue
            if not hmac.compare_digest(stored, _record_mac(record, hmac_key)):
                findings.append(
                    "line %d: record MAC does not match" % number)
                continue
        if record["id"] in seen:
            findings.append("line %d: duplicate id %r"
                            % (number, record["id"]))
        seen.add(record["id"])
        records.append(record)
    return records, findings


def _fsync_dir(path):
    if os.name == "nt":
        return
    try:
        descriptor = os.open(str(path), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:  # hygiene: allow best-effort dir fsync; the append already fsynced
        pass
    finally:
        os.close(descriptor)


def _check_free_space(directory):
    try:
        free = shutil.disk_usage(str(directory)).free
    except OSError:
        return
    if free < MIN_FREE_BYTES:
        raise ValueError(
            "Why: a calibration-store append needs at least 10 MiB free on "
            "the target volume. Fix: free space or choose another path.")


@contextmanager
def _locked(target, timeout_seconds=3.0):
    """Hold an exclusive advisory lock for one forecast append."""
    lock_path = Path(str(target) + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + max(0.0, float(timeout_seconds))
    token = "%d:%d:%s" % (os.getpid(), time.time_ns(),
                          os.urandom(8).hex())
    while True:
        try:
            descriptor = os.open(str(lock_path),
                                 os.O_CREAT | os.O_EXCL | os.O_RDWR)
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(token + "\n")
                handle.flush()
            break
        except PermissionError:
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    "Why: another writer holds the calibration-store lock on "
                    "%s. Fix: retry after it finishes, or remove %s if no "
                    "writer is active." % (Path(target).name,
                                           lock_path.name))
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
                        except OSError:  # hygiene: allow best-effort claim cleanup; retry continues
                            pass
                        continue
            except OSError:  # hygiene: allow lock stat race; the retry loop handles it
                pass
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    "Why: another writer holds the calibration-store lock on "
                    "%s. Fix: retry after it finishes, or remove %s if no "
                    "writer is active." % (Path(target).name,
                                           lock_path.name))
            time.sleep(LOCK_POLL_SECONDS)
    try:
        yield
    finally:
        try:
            content = lock_path.read_text(encoding="utf-8").strip()
        except OSError:
            content = None
        if content == token:
            try:
                lock_path.unlink(missing_ok=True)
            except OSError:  # hygiene: allow best-effort lock release; the OS closes it
                pass


def _write_records_atomic(target, records):
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, target)
    _fsync_dir(target.parent)


def _write_json_atomic(target, value):
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, target)
    _fsync_dir(target.parent)


def _backup_file(source, backup):
    backup_tmp = backup.with_name(backup.name + ".tmp")
    shutil.copyfile(source, backup_tmp)
    with open(backup_tmp, "r+b") as handle:
        os.fsync(handle.fileno())
    os.replace(backup_tmp, backup)
    _fsync_dir(backup.parent)


def append_forecasts(forecasts, path, at=None, lock_timeout=3.0,
                     keep_recent=None, hmac_key=None):
    """Append validated, checksummed forecasts under the writer lock.

    With ``keep_recent`` the append and the archive rotation run under
    the same lock, so no other writer interleaves between them. The
    rotation keeps the newest N live; ``None`` leaves every record live.
    An optional ``hmac_key`` adds a per-record MAC and verifies existing
    records before appending.
    """
    if not isinstance(forecasts, (list, tuple)):
        raise ValueError(
            "Why: forecasts must be a list or tuple. Fix: pass a list of "
            "{id, probability, outcome} mappings.")
    hmac_key = _validate_hmac_key(hmac_key)
    if at is not None:
        _validate_at(at)
    if (isinstance(lock_timeout, bool)
            or not isinstance(lock_timeout, (int, float))
            or lock_timeout < 0):
        raise ValueError(
            "Why: lock_timeout must be a non-negative number. "
            "Fix: pass lock_timeout=3.0.")
    if keep_recent is not None:
        if (isinstance(keep_recent, bool)
                or not isinstance(keep_recent, int)
                or keep_recent < 1):
            raise ValueError(
                "Why: keep_recent must be a positive int or None. "
                "Fix: pass keep_recent=100 or None.")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    _check_free_space(target.parent)
    stamp = at or _now()
    sealed = [_seal(_validate_forecast(forecast), stamp, hmac_key=hmac_key)
              for forecast in forecasts]
    identifiers = [record["id"] for record in sealed]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("duplicate forecast id in the batch")
    rotation = None
    with _locked(target, lock_timeout):
        existing, findings = _read_records(target, hmac_key=hmac_key)
        if findings:
            raise ValueError("calibration store is invalid: %s"
                             % findings[0])
        if hmac_key is None and any(record.get("mac") for record in existing):
            raise ValueError(
                "Why: the calibration journal is keyed; an unkeyed append "
                "would mix authenticated and unauthenticated records. "
                "Fix: pass hmac_key=... or start a new journal.")
        existing_ids = {record["id"] for record in existing}
        duplicates = [identifier for identifier in identifiers
                      if identifier in existing_ids]
        if duplicates:
            raise ValueError("duplicate forecast id(s): %s"
                             % sorted(duplicates))
        if sealed:
            body = "".join(json.dumps(record, sort_keys=True) + "\n"
                           for record in sealed)
            with open(target, "a", encoding="utf-8", newline="\n") as handle:
                handle.write(body)
                handle.flush()
                os.fsync(handle.fileno())
            _fsync_dir(target.parent)
        if keep_recent is not None:
            rotation = _rotate_locked(
                target, Path(str(target) + ".archive"), keep_recent,
                hmac_key=hmac_key)
    combined = existing + sealed
    if rotation is None:
        rotated = False
        live_count = len(combined)
        archived = 0
        backup = None
        metadata = None
    else:
        rotated = rotation["rotated"]
        live_count = rotation["kept"]
        archived = rotation["archived"]
        backup = rotation["backup"]
        metadata = rotation["metadata"]
    return {
        "path": str(target),
        "appended": len(sealed),
        "records": len(combined),
        "resolved": sum(1 for record in combined
                        if record["outcome"] is not None),
        "rotated": rotated,
        "live": live_count,
        "archived": archived,
        "backup": backup,
        "metadata": metadata,
        "hmac": hmac_key is not None,
    }


def load_forecasts(path, hmac_key=None):
    """Load all valid forecast records, raising on any store defect."""
    hmac_key = _validate_hmac_key(hmac_key)
    records, findings = _read_records(path, hmac_key=hmac_key)
    if findings:
        raise ValueError("calibration store is invalid: %s" % findings[0])
    return records


def load_all_forecasts(path, archive_path=None, hmac_key=None):
    """Load archived forecasts in order, then the live journal.

    Archive and live ids must be disjoint; the combined list preserves
    the original chronological order when the archive holds older
    records and the live journal holds the newest ones.
    """
    hmac_key = _validate_hmac_key(hmac_key)
    archive = (Path(archive_path) if archive_path is not None
               else Path(str(path) + ".archive"))
    records = []
    if archive.exists():
        records.extend(load_forecasts(archive, hmac_key=hmac_key))
    records.extend(load_forecasts(path, hmac_key=hmac_key))
    seen = set()
    for record in records:
        if record["id"] in seen:
            raise ValueError(
                "duplicate forecast id %r across archive/live"
                % record["id"])
        seen.add(record["id"])
    return records


def verify_forecast_file(path, hmac_key=None):
    """Verify every record's schema, checksum, MAC, id and outcome."""
    hmac_key = _validate_hmac_key(hmac_key)
    records, findings = _read_records(path, hmac_key=hmac_key)
    return {
        "ok": not findings,
        "findings": findings,
        "records": len(records),
        "resolved": sum(1 for record in records
                        if record["outcome"] is not None),
        "ignored": sum(1 for record in records
                       if record["outcome"] is None),
        "hmac": hmac_key is not None,
    }


def _rotate_locked(target, archive, keep_recent, hmac_key=None):
    """Rotate ``target`` into ``archive``; the caller holds the lock."""
    live, findings = _read_records(target, hmac_key=hmac_key)
    if findings:
        raise ValueError("calibration store is invalid: %s" % findings[0])
    if hmac_key is None and any(record.get("mac") for record in live):
        raise ValueError(
            "Why: the calibration journal is keyed; an unkeyed rotation "
            "would move records without authenticating them. "
            "Fix: pass hmac_key=... or leave the journal unrotated.")
    if len(live) <= keep_recent:
        return {
            "rotated": False,
            "source_records": len(live),
            "archived": 0,
            "kept": len(live),
            "live": str(target),
            "archive": str(archive),
            "archive_records": None,
            "backup": None,
            "metadata": None,
        }
    archived, archive_findings = _read_records(archive, hmac_key=hmac_key)
    if archive_findings:
        raise ValueError("calibration archive is invalid: %s"
                         % archive_findings[0])
    if hmac_key is None and any(record.get("mac") for record in archived):
        raise ValueError(
            "Why: the calibration archive is keyed; an unkeyed rotation "
            "would extend it without authentication. "
            "Fix: pass hmac_key=... or leave the journal unrotated.")
    archived_ids = {record["id"]: record for record in archived}
    older = live[:-keep_recent]
    recent = live[-keep_recent:]
    additions = []
    for record in older:
        existing = archived_ids.get(record["id"])
        if existing is not None:
            if existing != record:
                raise ValueError(
                    "archive id %r conflicts with a different record"
                    % record["id"])
            continue
        additions.append(record)
    combined = archived + additions
    _check_free_space(archive.parent)
    _write_records_atomic(archive, combined)
    backup = Path(str(target) + ".bak")
    _backup_file(target, backup)
    _write_records_atomic(target, recent)
    metadata = {
        "schema": RECORD_SCHEMA,
        "source": target.name,
        "source_records": len(live),
        "archived": len(older),
        "kept": len(recent),
        "archive": archive.name,
        "archive_records": len(combined),
        "source_last_sha256": live[-1]["sha256"],
        "archive_last_sha256": (combined[-1]["sha256"]
                                if combined else None),
        "created_at": _now(),
    }
    metadata_path = Path(str(target) + ".rotation")
    _write_json_atomic(metadata_path, metadata)
    return {
        "rotated": True,
        "source_records": len(live),
        "archived": len(older),
        "kept": len(recent),
        "live": str(target),
        "archive": str(archive),
        "archive_records": len(combined),
        "backup": str(backup),
        "metadata": str(metadata_path),
    }


def rotate_forecast_journal(path, keep_recent=100, archive_path=None,
                            lock_timeout=3.0, hmac_key=None):
    """Archive older forecasts and keep the newest ``keep_recent`` live.

    The archive accumulates older records (idempotent by id); the live
    journal keeps the newest records; the pre-rotation live journal is
    copied to ``.bak``; a ``.rotation`` sidecar records the counts and
    last checksums. The combined archive+live read is lossless and keeps
    the original Brier/skill. A short or missing journal is a no-op.
    """
    if (isinstance(keep_recent, bool) or not isinstance(keep_recent, int)
            or keep_recent < 1):
        raise ValueError(
            "Why: keep_recent must be a positive int. "
            "Fix: pass keep_recent=100.")
    if (isinstance(lock_timeout, bool)
            or not isinstance(lock_timeout, (int, float))
            or lock_timeout < 0):
        raise ValueError(
            "Why: lock_timeout must be a non-negative number. "
            "Fix: pass lock_timeout=3.0.")
    hmac_key = _validate_hmac_key(hmac_key)
    target = Path(path)
    archive = (Path(archive_path) if archive_path is not None
               else Path(str(target) + ".archive"))
    if archive == target:
        raise ValueError(
            "Why: archive_path must differ from path. "
            "Fix: pass a separate archive path.")
    target.parent.mkdir(parents=True, exist_ok=True)
    archive.parent.mkdir(parents=True, exist_ok=True)
    _check_free_space(target.parent)
    with _locked(target, lock_timeout):
        return _rotate_locked(target, archive, keep_recent,
                              hmac_key=hmac_key)
