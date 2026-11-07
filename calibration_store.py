"""Append-only calibration forecast journal with per-record checksums.

Forecasts are immutable observations; ``calibration.summary`` scores
whatever list it is given, but forecasts from earlier processes are
lost. This store appends one checksummed JSONL record per forecast under
an advisory lock, refuses duplicate ids, and names corrupt lines on
verification. Scoring stays in ``calibration.summary``. The checksum
detects accidental edits, not a keyed signature.
"""

import hashlib
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
_INPUT_FIELDS = frozenset({"id", "probability", "outcome", "at"})


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True)


def _valid_digest(value):
    return (isinstance(value, str) and len(value) == 64
            and all(ch in "0123456789abcdef" for ch in value))


def _record_digest(record):
    body = {key: value for key, value in record.items() if key != "sha256"}
    return hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()


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
    unknown = set(record) - _RECORD_FIELDS
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
    if digest != _record_digest(record):
        raise ValueError("checksum does not match the record")
    return dict(record)


def _seal(forecast, at):
    record = {
        "schema": RECORD_SCHEMA,
        "id": forecast["id"],
        "probability": float(forecast["probability"]),
        "outcome": forecast.get("outcome"),
        "at": forecast.get("at") or at,
    }
    record["sha256"] = _record_digest(record)
    return record


def _read_records(path):
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
    while True:
        try:
            descriptor = os.open(str(lock_path),
                                 os.O_CREAT | os.O_EXCL | os.O_RDWR)
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write("%d:%d\n" % (os.getpid(), int(time.time())))
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
            lock_path.unlink(missing_ok=True)
        except OSError:  # hygiene: allow best-effort lock release; the OS closes it
            pass


def append_forecasts(forecasts, path, at=None, lock_timeout=3.0):
    """Append validated, checksummed forecasts under the writer lock."""
    if not isinstance(forecasts, (list, tuple)):
        raise ValueError(
            "Why: forecasts must be a list or tuple. Fix: pass a list of "
            "{id, probability, outcome} mappings.")
    if at is not None:
        _validate_at(at)
    if (isinstance(lock_timeout, bool)
            or not isinstance(lock_timeout, (int, float))
            or lock_timeout < 0):
        raise ValueError(
            "Why: lock_timeout must be a non-negative number. "
            "Fix: pass lock_timeout=3.0.")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    _check_free_space(target.parent)
    stamp = at or _now()
    sealed = [_seal(_validate_forecast(forecast), stamp)
              for forecast in forecasts]
    identifiers = [record["id"] for record in sealed]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("duplicate forecast id in the batch")
    with _locked(target, lock_timeout):
        existing, findings = _read_records(target)
        if findings:
            raise ValueError("calibration store is invalid: %s"
                             % findings[0])
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
    combined = existing + sealed
    return {
        "path": str(target),
        "appended": len(sealed),
        "records": len(combined),
        "resolved": sum(1 for record in combined
                        if record["outcome"] is not None),
    }


def load_forecasts(path):
    """Load all valid forecast records, raising on any store defect."""
    records, findings = _read_records(path)
    if findings:
        raise ValueError("calibration store is invalid: %s" % findings[0])
    return records


def verify_forecast_file(path):
    """Verify every record's schema, checksum, id and outcome."""
    records, findings = _read_records(path)
    return {
        "ok": not findings,
        "findings": findings,
        "records": len(records),
        "resolved": sum(1 for record in records
                        if record["outcome"] is not None),
        "ignored": sum(1 for record in records
                       if record["outcome"] is None),
    }
