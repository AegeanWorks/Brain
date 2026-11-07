"""Independent verification of a log header's episode digest.

The header carries the task, seed, budget, policy digest and
``episode_sha256``. This verifier rebuilds the deterministic initial
state with ``GridWorld(task, seed).reset()`` and recomputes
``input_digest`` with the stored fields. It is read-only; a missing seed
or a mismatch is named.
"""

from identity import input_digest
from telemetry.log import Telemetry
from worlds.grid import GridWorld


def _valid_digest(value):
    return (isinstance(value, str) and len(value) == 64
            and all(ch in "0123456789abcdef" for ch in value))


def verify_episode_header(log_path):
    """Rebuild the episode identity from one log's header fields."""
    try:
        records = Telemetry(log_path).read_all()
    except (OSError, ValueError) as exc:
        raise ValueError("log %s is unreadable: %s" % (log_path, exc))
    headers = [record for record in records
               if isinstance(record, dict) and record.get("type") == "header"]
    if not headers:
        return {"ok": False, "headers": 0,
                "findings": ["missing-header"], "results": []}
    findings = []
    results = []
    for header in headers:
        task = header.get("task")
        seed = header.get("seed")
        budget = header.get("budget")
        policy = header.get("policy_sha256")
        episode = header.get("episode_sha256")
        if seed is None:
            findings.append("missing-seed")
            continue
        if (not isinstance(task, str) or not task
                or isinstance(seed, bool) or not isinstance(seed, int)
                or isinstance(budget, bool) or not isinstance(budget, int)
                or not isinstance(policy, str) or not policy):
            findings.append("invalid-header")
            continue
        if not _valid_digest(episode):
            findings.append("invalid-episode")
            continue
        try:
            state = GridWorld(task, seed).reset()
            recomputed, _projection = input_digest(state, {
                "task": task, "seed": seed, "max_steps": budget,
                "policy_sha256": policy,
            })
        except Exception as exc:
            findings.append("unverifiable-header: %s" % exc)
            continue
        results.append({
            "task": task,
            "seed": seed,
            "episode_sha256": episode,
            "recomputed": recomputed,
        })
        if recomputed != episode:
            findings.append("episode-mismatch")
    return {
        "ok": not findings,
        "headers": len(headers),
        "findings": findings,
        "results": results,
    }
