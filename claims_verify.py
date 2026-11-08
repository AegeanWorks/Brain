"""Read-only verification of claim verdict refs against logged episodes.

A verdict ref is caller-provided; this module checks it against the
``episode_sha256`` values written in one or more telemetry log headers.
It reports verified, unverified and unreferenced verdicts, names the
claim/verdict for an unknown episode, and writes nothing.
"""

from pathlib import Path

from claims import ClaimLedger
from telemetry.log import Telemetry, verify_chain


def _validate_options(hmac_key, verify_logs):
    if not isinstance(verify_logs, bool):
        raise ValueError(
            "Why: verify_logs must be a bool. "
            "Fix: pass verify_logs=True or False.")
    if hmac_key is not None:
        if (not isinstance(hmac_key, (bytes, bytearray))
                or not hmac_key):
            raise ValueError(
                "Why: hmac_key must be non-empty bytes or None. "
                "Fix: pass the verifier-held bytes key, or omit it.")
        if not verify_logs:
            raise ValueError(
                "Why: hmac_key needs verify_logs=True. "
                "Fix: enable chain verification or omit hmac_key.")


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


def _normalise_journals(paths, journal_paths):
    if journal_paths is None:
        return {str(path): None for path in paths}
    if isinstance(journal_paths, (str, Path)):
        if len(paths) != 1:
            raise ValueError(
                "Why: a single journal path needs exactly one log. "
                "Fix: pass a mapping of log path to journal path.")
        return {str(paths[0]): Path(journal_paths)}
    if not isinstance(journal_paths, dict):
        raise ValueError(
            "Why: journal_paths must be a path or a mapping of log path to "
            "journal path. Fix: pass one path or a per-log mapping.")
    allowed = {str(path) for path in paths}
    mapping = {}
    for key, value in journal_paths.items():
        if (not isinstance(key, (str, Path))
                or not isinstance(value, (str, Path))):
            raise ValueError(
                "Why: journal mapping keys and values must be paths. "
                "Fix: pass strings/paths only.")
        key_text = str(Path(key))
        if key_text not in allowed:
            raise ValueError(
                "Why: journal mapping key %r is not one of the logs. "
                "Fix: key the mapping by the supplied log paths." % key_text)
        mapping[key_text] = Path(value)
    return {str(path): mapping.get(str(path)) for path in paths}


def _log_episodes(path, hmac_key=None, verify_logs=True,
                  journal_path=None):
    if not Path(path).exists():
        raise ValueError(
            "log %s does not exist. Fix: pass a logged run path." % path)
    if verify_logs:
        chain = verify_chain(path, hmac_key=hmac_key,
                             journal_path=journal_path)
        if not chain["ok"]:
            raise ValueError(
                "log %s failed chain verification: %s. "
                "Fix: repair the log or pass verify_logs=False for "
                "membership-only verification."
                % (path, ", ".join(chain["findings"])))
    try:
        records = Telemetry(path).read_headers()
    except (OSError, ValueError) as exc:
        raise ValueError("log %s is unreadable: %s" % (path, exc))
    episodes = set()
    for record in records:
        digest = record.get("episode_sha256")
        if isinstance(digest, str) and digest:
            episodes.add(digest)
    if not episodes:
        raise ValueError(
            "log %s has no episode_sha256 header. "
            "Fix: pass a logged run whose header carries an episode digest."
            % path)
    return episodes


def verify_claim_refs(ledger, log_paths, hmac_key=None, verify_logs=True,
                      journal_paths=None, verify_episodes=False,
                      expected_policy_sha256=None,
                      expected_workspace_sha256=None, verify_replay=False):
    """Check every verdict ref against the episodes found in the logs.

    ``verify_logs=True`` (default) first verifies each log's hash chain;
    an optional ``hmac_key`` also verifies keyed records and an optional
    ``journal_paths`` witness (one path for one log, or a per-log
    mapping) checks the log head/count against an anchor journal.
    ``verify_episodes=True`` additionally rebuilds each header's episode
    digest from its task/seed/budget/policy and rejects a mismatch; an
    optional ``expected_policy_sha256`` pins the producing policy and an
    optional ``expected_workspace_sha256`` pins the source tree.
    ``verify_replay=True`` additionally replays each log's actions through
    the world its header names, so a ref cannot cite a log whose header is
    intact but whose trajectory is false. A failed check raises instead of
    trusting the header. ``verify_logs=False`` is the membership-only
    ablation and cannot take an hmac_key, a journal or replay.
    """
    if not isinstance(ledger, ClaimLedger):
        raise ValueError(
            "Why: ledger must be a ClaimLedger. "
            "Fix: build or load a ClaimLedger first.")
    if not isinstance(verify_episodes, bool):
        raise ValueError(
            "Why: verify_episodes must be a bool. "
            "Fix: pass verify_episodes=True or False.")
    if not isinstance(verify_replay, bool):
        raise ValueError(
            "Why: verify_replay must be a bool. "
            "Fix: pass verify_replay=True or False.")
    if verify_replay and not verify_logs:
        raise ValueError(
            "Why: verify_replay needs verify_logs=True. "
            "Fix: enable chain verification or omit verify_replay.")
    for name, value in (("expected_policy_sha256", expected_policy_sha256),
                        ("expected_workspace_sha256",
                         expected_workspace_sha256)):
        if value is not None and not verify_episodes:
            raise ValueError(
                "Why: %s needs verify_episodes=True. "
                "Fix: enable episode verification or omit the pin." % name)
    _validate_options(hmac_key, verify_logs)
    paths = _normalise_paths(log_paths)
    journals = _normalise_journals(paths, journal_paths)
    if (any(journal is not None for journal in journals.values())
            and not verify_logs):
        raise ValueError(
            "Why: journal_paths need verify_logs=True. "
            "Fix: enable chain verification or omit journal_paths.")
    if verify_episodes:
        from episode_verify import verify_episode_header

        for path in paths:
            episode = verify_episode_header(
                path, expected_policy_sha256=expected_policy_sha256,
                expected_workspace_sha256=expected_workspace_sha256)
            if not episode["ok"]:
                raise ValueError(
                    "log %s failed episode verification: %s. "
                    "Fix: regenerate the run or repair the header."
                    % (path, ", ".join(episode["findings"])))
    if verify_replay:
        from episode_replay import verify_action_replay

        for path in paths:
            replay = verify_action_replay(str(path))
            if not replay["ok"]:
                raise ValueError(
                    "log %s failed replay verification: %s. "
                    "Fix: regenerate the run, or omit verify_replay for "
                    "header-only verification."
                    % (path, ", ".join(replay["findings"])))
    logs = {}
    episodes = set()
    for path in paths:
        found = _log_episodes(path, hmac_key=hmac_key,
                              verify_logs=verify_logs,
                              journal_path=journals.get(str(path)))
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
        "verify_logs": verify_logs,
        "hmac": hmac_key is not None,
        "journals": {log: str(journal)
                     for log, journal in journals.items()
                     if journal is not None},
        "verify_episodes": verify_episodes,
        "replay": verify_replay,
        "expected_policy_sha256": expected_policy_sha256,
        "expected_workspace_sha256": expected_workspace_sha256,
    }


def verify_claim_store(store_path, log_paths, hmac_key=None,
                       verify_logs=True, journal_paths=None,
                       verify_episodes=False,
                       expected_policy_sha256=None,
                       expected_workspace_sha256=None,
                       store_hmac_key=None, verify_replay=False):
    """Load a claim-store snapshot and verify its verdict refs.

    ``hmac_key`` authenticates the telemetry logs; ``store_hmac_key``
    authenticates the claim snapshot itself, so a keyed store is not
    loaded unauthenticated through the combined verifier.
    ``verify_replay`` replays each log's actions, so a verdict cannot cite
    a log whose header is intact but whose trajectory is false.
    """
    from claims_store import load_ledger

    ledger = load_ledger(store_path, hmac_key=store_hmac_key)
    result = verify_claim_refs(
        ledger, log_paths, hmac_key=hmac_key, verify_logs=verify_logs,
        journal_paths=journal_paths, verify_episodes=verify_episodes,
        expected_policy_sha256=expected_policy_sha256,
        expected_workspace_sha256=expected_workspace_sha256,
        verify_replay=verify_replay)
    result["store_hmac"] = store_hmac_key is not None
    return result
