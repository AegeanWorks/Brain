"""Deterministic workspace source hash for run/evidence binding.

Adapted from ``harness/transcript.py:17 workspace_files`` and
``tools/replay.py:16 _hash_tree`` (AegeanWorks/Harness). The map hashes
each relative source file; the tree digest hashes the sorted
``path\\0digest`` lines. Caches, the git store, local reports, logs,
databases and the AIKit ledger are excluded so reruns are stable.
"""

import hashlib
from pathlib import Path

SKIP_DIRS = frozenset({
    ".git", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache",
    ".aikit", "reports",
})
SKIP_SUFFIXES = (".pyc", ".pyo", ".log", ".jsonl", ".db", ".sqlite", ".bak", ".tmp")
SKIP_NAMES = frozenset({"STOP"})


def workspace_files(root):
    """Return ``{relative_path: sha256}`` for the workspace source tree."""
    base = Path(root)
    if not base.is_dir():
        raise ValueError("workspace root is not a directory: %s" % root)
    out = {}
    for path in sorted(base.rglob("*")):
        if not path.is_file() or path.name in SKIP_NAMES:
            continue
        if path.suffix in SKIP_SUFFIXES:
            continue
        try:
            rel = path.relative_to(base).as_posix()
        except ValueError:
            continue
        if any(part in SKIP_DIRS for part in Path(rel).parts[:-1]):
            continue
        digest = hashlib.sha256()
        try:
            with open(path, "rb") as handle:
                for chunk in iter(lambda: handle.read(1 << 20), b""):
                    digest.update(chunk)
        except OSError:
            continue
        out[rel] = digest.hexdigest()
    return out


def workspace_digest(root):
    """Return one SHA-256 over the sorted relative-path/file-digest map."""
    files = workspace_files(root)
    digest = hashlib.sha256()
    for rel in sorted(files):
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(files[rel]))
        digest.update(b"\n")
    return digest.hexdigest()
