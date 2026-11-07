"""Read-only verification of claim verdict refs against logged episodes.

A verdict ref is caller-provided; this module checks it against the
``episode_sha256`` values written in one or more telemetry log headers.
It reports verified, unverified and unreferenced verdicts, names the
claim/verdict for an unknown episode, and writes nothing.
"""

from pathlib import Path

from claims import ClaimLedger
from telemetry.log import Telemetry


def _normalise_paths(log_paths):
    if isinstance(log_paths, (str, Path)):
        paths = [log_paths]
    elif isinstance(log_paths, (list, tuple)):
        paths = list(log_paths)
    else:
        raise ValueError(
            "Why: log_paths must be a path or a list/tuple of paths. "
            "Fix: pass one log path or a list of them.")
    if not paths:
        raise ValueError(
            "Why: at least one log is required for ref verification. "
            "Fix: pass a logged run path.")
    for path in paths:
        if not isinstance(path, (str, Path)):
            raise ValueError(
                "Why: each log path must be a string or Path. "
                "Fix: pass strings/paths only.")
    return [Path(path) for path in paths]


def _log_episodes(path):
    if not Path(path).exists():
        raise ValueError(
            "log %s does not exist. Fix: pass a logged run path." % path)
    try:
        records = Telemetry(path).read_all()
    except (OSError, ValueError) as exc:
        raise ValueError("log %s is unreadable: %s" % (path, exc))
    episodes = set()
    for record in records:
        if not isinstance(record, dict) or record.get("type") != "header":
            continue
        digest = record.get("episode_sha256")
        if isinstance(digest, str) and digest:
            episodes.add(digest)
    if not episodes:
        raise ValueError(
            "log %s has no episode_sha256 header. "
            "Fix: pass a logged run whose header carries an episode digest."
            % path)
    return episodes


def verify_claim_refs(ledger, log_paths):
    """Check every verdict ref against the episodes found in the logs."""
    if not isinstance(ledger, ClaimLedger):
        raise ValueError(
            "Why: ledger must be a ClaimLedger. "
            "Fix: build or load a ClaimLedger first.")
    paths = _normalise_paths(log_paths)
    logs = {}
    episodes = set()
    for path in paths:
        found = _log_episodes(path)
        logs[str(path)] = sorted(found)
        episodes.update(found)
    verified = 0
    unverified = 0
    unreferenced = 0
    findings = []
    for claim in ledger.claims():
        for index, verdict in enumerate(claim.verdicts):
            ref = verdict.ref
            if ref is None:
                unreferenced += 1
                continue
            if ref in episodes:
                verified += 1
            else:
                unverified += 1
                findings.append({
                    "claim": claim.id,
                    "verdict": index,
                    "ref": ref,
                    "reason": "unknown-episode",
                })
    return {
        "ok": unverified == 0,
        "verified": verified,
        "unverified": unverified,
        "unreferenced": unreferenced,
        "episodes": sorted(episodes),
        "logs": logs,
        "findings": findings,
    }


def verify_claim_store(store_path, log_paths):
    """Load a claim-store snapshot and verify its verdict refs."""
    from claims_store import load_ledger

    return verify_claim_refs(load_ledger(store_path), log_paths)
