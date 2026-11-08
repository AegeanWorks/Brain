"""Durable claim-ledger snapshots with checksums, backups and quarantine.

The in-memory ClaimLedger roundtrips as JSON but is lost when the process
exits. This store writes one checksummed snapshot atomically (temp +
fsync + replace), keeps the previous snapshot as ``.bak``, serialises
writers with an ``O_CREAT|O_EXCL`` lock that steals a stale one, and
quarantines a corrupt primary before falling back to the backup. A
checksum detects accidental edits; an optional HMAC-SHA256 binds the
snapshot to a caller-held key, so an editor who recomputes the checksum
still fails verification.
"""

import hashlib
import hmac
import json
import os
import shutil
import time
from contextlib import contextmanager
from pathlib import Path

from claims import ClaimLedger

STORE_SCHEMA = 1
LOCK_STALE_SECONDS = 30.0
LOCK_POLL_SECONDS = 0.02
MIN_FREE_BYTES = 10 * 1024 * 1024
REPLACE_TRIES = 5
_REQUIRED_FIELDS = frozenset({"schema", "saved_at", "claims", "sha256"})
_OPTIONAL_FIELDS = frozenset({"mac"})


class ClaimStoreMacError(ValueError):
    """The caller's key cannot authenticate the snapshot; do not quarantine."""


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True)


def _valid_digest(value):
    return (isinstance(value, str) and len(value) == 64
            and all(ch in "0123456789abcdef" for ch in value))


def _digest(payload):
    body = {key: value for key, value in payload.items()
            if key not in ("sha256", "mac")}
    return hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()


def _mac(payload, key):
    body = {name: value for name, value in payload.items() if name != "mac"}
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


def _sealed(ledger, saved_at):
    payload = {
        "schema": STORE_SCHEMA,
        "saved_at": float(saved_at if saved_at is not None else time.time()),
        "claims": list(ledger.to_dict()["claims"]),
    }
    payload["sha256"] = _digest(payload)
    return payload


def _validate_payload(value):
    if not isinstance(value, dict):
        raise ValueError("claim store payload must be an object")
    missing = _REQUIRED_FIELDS - set(value)
    if missing:
        raise ValueError("claim store is missing %s" % sorted(missing))
    unknown = set(value) - _REQUIRED_FIELDS - _OPTIONAL_FIELDS
    if unknown:
        raise ValueError("claim store has unknown fields: %s" % sorted(unknown))
    if value["schema"] != STORE_SCHEMA:
        raise ValueError("unsupported claim store schema")
    saved_at = value["saved_at"]
    if (isinstance(saved_at, bool)
            or not isinstance(saved_at, (int, float))
            or saved_at < 0):
        raise ValueError("claim store saved_at must be a non-negative number")
    digest = value["sha256"]
    if not _valid_digest(digest):
        raise ValueError("claim store checksum must be a lowercase SHA-256 digest")
    mac = value.get("mac")
    if mac is not None and not _valid_digest(mac):
        raise ValueError("claim store MAC must be a lowercase SHA-256 digest")
    if digest != _digest(value):
        raise ValueError("claim store checksum does not match its payload")
    try:
        ledger = ClaimLedger.from_dict({"claims": value["claims"]})
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError("claim store claims are invalid: %s" % exc)
    return ledger, value


def _read_payload(path, hmac_key=None):
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError("claim store is unreadable: %s" % exc)
    try:
        value = json.loads(text)
    except ValueError as exc:
        raise ValueError("claim store is not valid JSON") from exc
    ledger, value = _validate_payload(value)
    if hmac_key is not None:
        stored = value.get("mac")
        if stored is None:
            raise ClaimStoreMacError("claim store is missing its MAC")
        if not hmac.compare_digest(stored, _mac(value, hmac_key)):
            raise ClaimStoreMacError(
                "claim store MAC does not match its payload")
    return ledger, value


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


def _check_free_space(directory):
    try:
        free = shutil.disk_usage(str(directory)).free
    except OSError:
        return
    if free < MIN_FREE_BYTES:
        raise ValueError(
            "Why: a claim-store write needs at least 10 MiB free on the "
            "target volume. Fix: free space or choose another path.")


def _replace_with_retries(source, target):
    for attempt in range(REPLACE_TRIES):
        try:
            os.replace(source, target)
            return
        except OSError:
            if attempt == REPLACE_TRIES - 1:
                raise
            time.sleep(0.01)


def _write_atomic(target, text):
    tmp = target.with_name(target.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    if target.exists():
        backup = target.with_name(target.name + ".bak")
        backup_tmp = backup.with_name(backup.name + ".tmp")
        try:
            shutil.copyfile(target, backup_tmp)
            with open(backup_tmp, "r+b") as handle:
                os.fsync(handle.fileno())
            _replace_with_retries(backup_tmp, backup)
        except OSError:
            try:
                backup_tmp.unlink(missing_ok=True)
            except OSError:  # hygiene: allow best-effort cleanup; the primary is untouched
                pass
            try:
                tmp.unlink(missing_ok=True)
            except OSError:  # hygiene: allow best-effort cleanup; the write is refused
                pass
            raise
    _replace_with_retries(tmp, target)
    _fsync_dir(target.parent)


@contextmanager
def _locked(target, timeout_seconds=3.0):
    """Hold an exclusive advisory lock for one claim-store write.

    Adapted from the telemetry append lock: an ``O_CREAT|O_EXCL`` lock
    file with the PID and timestamp serialises writers; a lock older than
    ``LOCK_STALE_SECONDS`` is stolen by an atomic rename; a bounded
    timeout raises instead of hanging.
    """
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
                    "Why: another writer holds the claim-store lock on %s. "
                    "Fix: retry after it finishes, or remove %s if no "
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
                    "Why: another writer holds the claim-store lock on %s. "
                    "Fix: retry after it finishes, or remove %s if no "
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


def save_ledger(ledger, path, saved_at=None, lock_timeout=3.0,
                hmac_key=None):
    """Write one checksummed claim-ledger snapshot atomically."""
    if not isinstance(ledger, ClaimLedger):
        raise ValueError(
            "Why: ledger must be a ClaimLedger. Fix: build one with "
            "ClaimLedger().")
    hmac_key = _validate_hmac_key(hmac_key)
    if saved_at is not None and (
            isinstance(saved_at, bool)
            or not isinstance(saved_at, (int, float))
            or saved_at < 0):
        raise ValueError(
            "Why: saved_at must be a non-negative number or None. "
            "Fix: pass saved_at=time.time() or omit it.")
    if (isinstance(lock_timeout, bool)
            or not isinstance(lock_timeout, (int, float))
            or lock_timeout < 0):
        raise ValueError(
            "Why: lock_timeout must be a non-negative number. "
            "Fix: pass lock_timeout=3.0.")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    _check_free_space(target.parent)
    payload = _sealed(ledger, saved_at)
    if hmac_key is not None:
        payload["mac"] = _mac(payload, hmac_key)
    body = json.dumps(payload, sort_keys=True) + "\n"
    with _locked(target, lock_timeout):
        _write_atomic(target, body)
    return {
        "path": str(target),
        "claims": len(ledger.claims()),
        "verdicts": sum(len(claim.verdicts) for claim in ledger.claims()),
        "sha256": payload["sha256"],
        "hmac": hmac_key is not None,
    }


def _quarantine(target):
    destination = Path(str(target) + ".corrupt")
    try:
        os.replace(target, destination)
    except OSError:  # hygiene: allow best-effort quarantine; backup fallback still applies
        return None
    return destination


def load_ledger(path, hmac_key=None):
    """Load a claim ledger, recovering from a backup after a corrupt primary."""
    hmac_key = _validate_hmac_key(hmac_key)
    target = Path(path)
    backup = Path(str(target) + ".bak")
    if not target.exists():
        if backup.exists():
            ledger, _value = _read_payload(backup, hmac_key=hmac_key)
            return ledger
        return ClaimLedger()
    try:
        ledger, _value = _read_payload(target, hmac_key=hmac_key)
        return ledger
    except ClaimStoreMacError:
        raise
    except ValueError:
        _quarantine(target)
        if backup.exists():
            try:
                ledger, _value = _read_payload(backup, hmac_key=hmac_key)
                return ledger
            except ValueError as exc:
                raise ValueError(
                    "Why: the claim store primary was quarantined and the "
                    "backup is also invalid: %s. Fix: restore a valid "
                    "snapshot or start a new ledger." % exc)
        raise


def verify_ledger_file(path, hmac_key=None):
    """Verify the primary snapshot's schema, checksum, MAC and claims."""
    hmac_key = _validate_hmac_key(hmac_key)
    target = Path(path)
    if not target.exists():
        return {"ok": False, "findings": ["missing-primary"],
                "claims": None, "verdicts": None, "sha256": None,
                "hmac": hmac_key is not None}
    try:
        ledger, value = _read_payload(target, hmac_key=hmac_key)
    except ValueError as exc:
        return {"ok": False, "findings": ["invalid-primary: %s" % exc],
                "claims": None, "verdicts": None, "sha256": None,
                "hmac": hmac_key is not None}
    return {
        "ok": True,
        "findings": [],
        "claims": len(ledger.claims()),
        "verdicts": sum(len(claim.verdicts) for claim in ledger.claims()),
        "sha256": value["sha256"],
        "hmac": hmac_key is not None,
    }
