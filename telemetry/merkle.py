"""Domain-separated Merkle batch anchors and inclusion proofs.

Adapted from ``merklock/hashing.py`` (AegeanWorks/Merklock). Leaves are
the 32-byte record digests already stored in the telemetry log; leaf and
node hashes are domain-separated and length-prefixed so concatenated
parts cannot be re-split ambiguously. An odd node is promoted, never
duplicated. The batch anchor is a separate, atomic JSON sidecar; it does
not change the log format or the linear chain. An append-only journal
(``append_merkle_anchor``) chains successive batch anchors with
``prev``/``hash`` links and monotonic ranges, so an earlier batch root
and its inclusion proof survive later anchors.
"""

import hashlib
import json
import os
import time
from pathlib import Path

DOMAIN = b"brain/merkle/v1"
ANCHOR_SCHEMA = 1
MAX_U32 = 0xFFFFFFFF
GENESIS = "GENESIS"


def pack(data):
    """Prefix ``data`` with its length so concatenated parts are unambiguous."""
    if len(data) > MAX_U32:
        raise ValueError("a hash part cannot exceed 4 GiB")
    return len(data).to_bytes(4, "big") + data


def digest(domain, *parts):
    """One 32-byte SHA-256 digest bound to a named protocol domain."""
    if not isinstance(domain, str) or not domain or "/" in domain or "\x00" in domain:
        raise ValueError("a domain is a non-empty name without '/'")
    for part in parts:
        if not isinstance(part, (bytes, bytearray)):
            raise ValueError("a hash part must be bytes")
    payload = (DOMAIN + b"/" + domain.encode("ascii") + b"\x00"
               + b"".join(pack(part) for part in parts))
    return hashlib.sha256(payload).digest()


def merkle_root(leaves):
    """Root of a domain-separated Merkle tree; empty and odd trees defined."""
    level = [digest("leaf", leaf) for leaf in leaves]
    if not level:
        return digest("empty-tree")
    while len(level) > 1:
        following = []
        for index in range(0, len(level) - 1, 2):
            following.append(digest("node", level[index], level[index + 1]))
        if len(level) % 2:
            following.append(level[-1])
        level = following
    return level[0]


def merkle_proof(leaves, index):
    """Sibling hashes from the leaf level upwards; promoted nodes add b''."""
    if isinstance(index, bool) or not isinstance(index, int):
        raise IndexError("merkle proof index must be an int")
    if not 0 <= index < len(leaves):
        raise IndexError("merkle proof index out of range")
    level = [digest("leaf", leaf) for leaf in leaves]
    path = []
    while len(level) > 1:
        sibling = index ^ 1
        path.append(level[sibling] if sibling < len(level) else b"")
        following = []
        for position in range(0, len(level) - 1, 2):
            following.append(digest("node", level[position], level[position + 1]))
        if len(level) % 2:
            following.append(level[-1])
        level = following
        index //= 2
    return path


def merkle_verify(leaf, index, proof, root):
    """Recompute the root from one leaf and its proof, rejecting forgery."""
    if isinstance(index, bool) or not isinstance(index, int) or index < 0:
        return False
    try:
        siblings = list(proof)
    except TypeError:
        return False
    current = digest("leaf", leaf)
    position = index
    for sibling in siblings:
        if not isinstance(sibling, (bytes, bytearray)):
            return False
        if not sibling and (position == 0 or position % 2 == 1):
            return False
        if sibling:
            if position % 2:
                current = digest("node", sibling, current)
            else:
                current = digest("node", current, sibling)
        position //= 2
    return position == 0 and current == root


def _leaf(value):
    if isinstance(value, str):
        try:
            raw = bytes.fromhex(value)
        except ValueError as exc:
            raise ValueError("a leaf digest must be hexadecimal") from exc
    elif isinstance(value, (bytes, bytearray)):
        raw = bytes(value)
    else:
        raise ValueError("a leaf digest must be bytes or hex")
    if len(raw) != 32:
        raise ValueError("a leaf digest must be 32 bytes")
    return raw


def _anchor_path(log_path):
    return Path(str(log_path) + ".merkle")


def _read_records(log_path):
    path = Path(log_path)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValueError("telemetry log is unreadable: %s" % exc)
    records = []
    for line in lines:
        if line.strip():
            records.append(json.loads(line))
    return records


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


def _write_anchor(target, anchor):
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(anchor, handle, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, target)
    _fsync_dir(target.parent)


def _validate_anchor(anchor):
    if not isinstance(anchor, dict):
        raise ValueError("merkle anchor must be an object")
    for key in ("schema", "ledger", "start", "end", "count", "root", "created_at"):
        if key not in anchor:
            raise ValueError("merkle anchor is missing %s" % key)
    if anchor["schema"] != ANCHOR_SCHEMA:
        raise ValueError("unsupported merkle anchor schema")
    start, end, count = anchor["start"], anchor["end"], anchor["count"]
    for value in (start, end, count):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("merkle anchor range values must be non-negative ints")
    if end < start or count != end - start:
        raise ValueError("merkle anchor range is inconsistent")
    root = anchor["root"]
    if (not isinstance(root, str) or len(root) != 64
            or any(ch not in "0123456789abcdef" for ch in root)):
        raise ValueError("merkle anchor root must be a lowercase SHA-256 digest")
    if not isinstance(anchor["ledger"], str) or not anchor["ledger"]:
        raise ValueError("merkle anchor ledger label is invalid")
    if not isinstance(anchor["created_at"], str) or not anchor["created_at"]:
        raise ValueError("merkle anchor created_at is invalid")
    return anchor


def _build_anchor(log_path, batch_size, created_at=None):
    """Build the batch anchor for the last ``batch_size`` record digests."""
    if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size < 1:
        raise ValueError("batch_size must be a positive int")
    records = _read_records(log_path)
    total = len(records)
    if total:
        end = total
        start = max(0, end - batch_size)
        leaves = [_leaf(record.get("digest")) for record in records[start:end]]
    else:
        start = end = 0
        leaves = []
    return {
        "schema": ANCHOR_SCHEMA,
        "ledger": Path(str(log_path)).name,
        "start": start,
        "end": end,
        "count": len(leaves),
        "root": merkle_root(leaves).hex(),
        "created_at": created_at or time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                  time.gmtime()),
    }


def write_merkle_anchor(log_path, batch_size=64, anchor_path=None,
                        created_at=None):
    """Commit the last ``batch_size`` record digests into a Merkle anchor."""
    anchor = _build_anchor(log_path, batch_size, created_at=created_at)
    target = (Path(anchor_path) if anchor_path is not None
              else _anchor_path(log_path))
    _write_anchor(target, anchor)
    return anchor


def _canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _anchor_hash(record):
    body = {key: value for key, value in record.items() if key != "hash"}
    return hashlib.sha256(_canonical_json(body).encode("utf-8")).hexdigest()


def _valid_digest(value):
    return (isinstance(value, str) and len(value) == 64
            and all(ch in "0123456789abcdef" for ch in value))


def _validate_journal_record(record, line_number=0):
    """Validate one journal record's anchor fields, prev link and hash."""
    anchor = _validate_anchor(record)
    for key in ("prev", "hash"):
        if key not in anchor:
            raise ValueError("merkle journal record is missing %s" % key)
    prev = anchor["prev"]
    if prev != GENESIS and not _valid_digest(prev):
        raise ValueError("merkle journal prev must be a digest or GENESIS")
    if not _valid_digest(anchor["hash"]):
        raise ValueError("merkle journal hash must be a lowercase SHA-256 digest")
    if anchor["hash"] != _anchor_hash(anchor):
        raise ValueError("merkle journal hash does not match its payload")
    return dict(anchor)


def _journal_path(log_path):
    return Path(str(log_path) + ".merkle.journal")


def _scan_journal(journal_path):
    """Return ``(records, errors)`` after validating links and order."""
    target = Path(journal_path)
    if not target.exists():
        return [], ["missing-journal"]
    try:
        lines = target.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [], ["unreadable-journal: %s" % exc]
    records = []
    errors = []
    expected_prev = GENESIS
    last_start = -1
    last_end = -1
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except ValueError:
            errors.append("line %d: invalid JSON" % number)
            continue
        try:
            anchor = _validate_journal_record(value, number)
        except ValueError as exc:
            errors.append("line %d: %s" % (number, exc))
            continue
        if anchor["prev"] != expected_prev:
            errors.append("line %d: prev does not match the previous anchor"
                          % number)
        if anchor["start"] < last_start or anchor["end"] < last_end:
            errors.append("line %d: batch range rolls back" % number)
        records.append(anchor)
        expected_prev = anchor["hash"]
        last_start = max(last_start, anchor["start"])
        last_end = max(last_end, anchor["end"])
    if not records and not errors:
        errors.append("empty-journal")
    return records, errors


def append_merkle_anchor(log_path, batch_size=64, journal_path=None,
                         created_at=None):
    """Append one batch anchor to a hash-chained journal.

    The previous record's ``hash`` becomes this record's ``prev``; a
    range that moves backwards is refused. The single-line append is
    fsynced and the containing directory is fsynced where possible.
    """
    anchor = _build_anchor(log_path, batch_size, created_at=created_at)
    target = (Path(journal_path) if journal_path is not None
              else _journal_path(log_path))
    target.parent.mkdir(parents=True, exist_ok=True)
    prev = GENESIS
    last_start = -1
    last_end = -1
    if target.exists():
        records, errors = _scan_journal(target)
        if errors:
            raise ValueError("merkle journal is invalid: %s" % errors[0])
        if records:
            tail = records[-1]
            prev = tail["hash"]
            last_start = tail["start"]
            last_end = tail["end"]
    if anchor["start"] < last_start or anchor["end"] < last_end:
        raise ValueError("merkle journal range rolls back from (%d, %d)"
                         % (last_start, last_end))
    record = dict(anchor)
    record["prev"] = prev
    record["hash"] = _anchor_hash(record)
    line = json.dumps(record, sort_keys=True) + "\n"
    with open(target, "a", encoding="utf-8", newline="\n") as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())
    _fsync_dir(target.parent)
    return record


def verify_merkle_journal(log_path, journal_path=None):
    """Verify journal links/order and, when given, every batch root.

    ``log_path=None`` validates only the journal itself. With a log, a
    batch extending past the current records is
    ``truncated-batch:<line>:<end>><count>``; a changed batch digest is
    ``root-mismatch:<line>``. An uncommitted log tail is allowed.
    """
    if journal_path is None:
        if log_path is None:
            raise ValueError("log_path or journal_path is required")
        journal_path = _journal_path(log_path)
    records, findings = _scan_journal(journal_path)
    tail = None
    if log_path is not None and records:
        try:
            log_records = _read_records(log_path)
        except ValueError as exc:
            findings.append("unreadable-log: %s" % exc)
            log_records = None
        if log_records is not None:
            for number, anchor in enumerate(records, start=1):
                if anchor["end"] > len(log_records):
                    findings.append("truncated-batch:%d:%d>%d"
                                    % (number, anchor["end"],
                                       len(log_records)))
                    continue
                try:
                    leaves = [_leaf(record.get("digest"))
                              for record in
                              log_records[anchor["start"]:anchor["end"]]]
                except ValueError as exc:
                    findings.append("invalid-leaf:%d: %s" % (number, exc))
                    continue
                if merkle_root(leaves).hex() != anchor["root"]:
                    findings.append("root-mismatch:%d" % number)
    if records:
        tail = records[-1]
    return {
        "ok": not findings,
        "anchors": len(records),
        "latest": tail,
        "findings": findings,
    }


def merkle_proof_for_journal_record(log_path, journal_path, record_index):
    """Prove one record in the latest journal batch that contains it."""
    records, errors = _scan_journal(journal_path)
    if errors:
        raise ValueError("merkle journal is invalid: %s" % errors[0])
    chosen = None
    for number, anchor in enumerate(records, start=1):
        if anchor["start"] <= record_index < anchor["end"]:
            chosen = (number, anchor)
    if chosen is None:
        raise ValueError("record index is outside every merkle batch")
    number, anchor = chosen
    log_records = _read_records(log_path)
    if anchor["end"] > len(log_records):
        raise ValueError("merkle batch extends past the log")
    leaves = [_leaf(record.get("digest"))
              for record in log_records[anchor["start"]:anchor["end"]]]
    local = record_index - anchor["start"]
    proof = merkle_proof(leaves, local)
    return {
        "record_index": record_index,
        "index": local,
        "leaf": leaves[local].hex(),
        "proof": [item.hex() for item in proof],
        "root": anchor["root"],
        "batch": number,
    }


def verify_merkle_anchor(log_path, anchor_path=None):
    """Verify the batch range against the log and the anchor root.

    This checks the batch commitment only; callers that need log
    authorship/order should run ``telemetry.log.verify_chain`` as well.
    """
    target = (Path(anchor_path) if anchor_path is not None
              else _anchor_path(log_path))
    if not target.exists():
        return {"ok": False, "findings": ["missing-anchor"], "root": None,
                "start": None, "end": None, "count": None}
    try:
        anchor = _validate_anchor(json.loads(target.read_text(encoding="utf-8")))
        records = _read_records(log_path)
    except (OSError, ValueError) as exc:
        return {"ok": False, "findings": ["invalid-anchor: %s" % exc],
                "root": None, "start": None, "end": None, "count": None}
    findings = []
    if anchor["end"] > len(records):
        findings.append("truncated-batch:%d>%d"
                        % (anchor["end"], len(records)))
    else:
        try:
            leaves = [_leaf(record.get("digest"))
                      for record in records[anchor["start"]:anchor["end"]]]
        except ValueError as exc:
            findings.append("invalid-leaf: %s" % exc)
        else:
            if merkle_root(leaves).hex() != anchor["root"]:
                findings.append("root-mismatch")
    return {"ok": not findings, "findings": findings,
            "root": anchor["root"], "start": anchor["start"],
            "end": anchor["end"], "count": anchor["count"]}


def merkle_proof_for_record(log_path, anchor_path, record_index):
    """Return the detached inclusion proof for one record in the batch."""
    target = (Path(anchor_path) if anchor_path is not None
              else _anchor_path(log_path))
    try:
        anchor = _validate_anchor(json.loads(target.read_text(encoding="utf-8")))
        records = _read_records(log_path)
    except (OSError, ValueError) as exc:
        raise ValueError("merkle anchor is unreadable: %s" % exc)
    if anchor["end"] > len(records):
        raise ValueError("merkle batch extends past the log")
    if not anchor["start"] <= record_index < anchor["end"]:
        raise ValueError("record index is outside the merkle batch")
    leaves = [_leaf(record.get("digest"))
              for record in records[anchor["start"]:anchor["end"]]]
    local = record_index - anchor["start"]
    proof = merkle_proof(leaves, local)
    return {
        "record_index": record_index,
        "index": local,
        "leaf": leaves[local].hex(),
        "proof": [item.hex() for item in proof],
        "root": anchor["root"],
    }


def verify_merkle_proof(bundle):
    """Verify a detached proof bundle produced by ``merkle_proof_for_record``."""
    if not isinstance(bundle, dict):
        return False
    try:
        leaf = _leaf(bundle.get("leaf"))
        root = bytes.fromhex(str(bundle.get("root", "")))
        index = bundle.get("index")
        if isinstance(index, bool) or not isinstance(index, int) or index < 0:
            return False
        proof = [_leaf(item) if item else b"" for item in bundle.get("proof", [])]
    except (TypeError, ValueError):
        return False
    return merkle_verify(leaf, index, proof, root)
