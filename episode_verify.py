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


def verify_episode_header(log_path, expected_policy_sha256=None,
                          expected_workspace_sha256=None,
                          expected_model=None):
    """Rebuild the episode identity from one log's header fields.

    ``expected_policy_sha256`` optionally pins the producing policy; a
    header with a different stored policy reports ``policy-mismatch``
    even when its episode digest is internally consistent.
    ``expected_workspace_sha256`` optionally pins the source tree; a
    missing or different stored workspace is named. Malformed stored
    policy/workspace digests are reported as invalid.
    ``expected_model`` optionally pins the backend label: a header naming a
    different model reports ``model-mismatch``, and one with no model
    reports ``missing-model``. Nothing is checked when the pin is omitted.
    """
    for name, value in (("expected_policy_sha256", expected_policy_sha256),
                        ("expected_workspace_sha256",
                         expected_workspace_sha256)):
        if value is not None and not _valid_digest(value):
            raise ValueError(
                "Why: %s must be a 64-hex digest or None. "
                "Fix: pass the expected digest or omit it." % name)
    if expected_model is not None and (not isinstance(expected_model, str)
                                       or not expected_model.strip()):
        raise ValueError(
            "Why: expected_model must be a non-empty string or None. "
            "Fix: pass the expected backend label or omit it.")
    try:
        headers = Telemetry(log_path).read_headers()
    except (OSError, ValueError) as exc:
        raise ValueError("log %s is unreadable: %s" % (log_path, exc))
    if not headers:
        return {"ok": False, "headers": 0,
                "findings": ["missing-header"], "results": [],
                "expected_policy_sha256": expected_policy_sha256,
                "expected_workspace_sha256": expected_workspace_sha256,
                "expected_model": expected_model}
    findings = []
    results = []
    for header in headers:
        task = header.get("task")
        seed = header.get("seed")
        budget = header.get("budget")
        policy = header.get("policy_sha256")
        episode = header.get("episode_sha256")
        workspace = header.get("workspace_sha256")
        if seed is None:
            findings.append("missing-seed")
            continue
        if (not isinstance(task, str) or not task
                or isinstance(seed, bool) or not isinstance(seed, int)
                or isinstance(budget, bool) or not isinstance(budget, int)
                or not isinstance(policy, str) or not policy):
            findings.append("invalid-header")
            continue
        if not _valid_digest(policy):
            findings.append("invalid-policy")
            continue
        if not _valid_digest(episode):
            findings.append("invalid-episode")
            continue
        if workspace is not None and not _valid_digest(workspace):
            findings.append("invalid-workspace")
            continue
        if (expected_policy_sha256 is not None
                and policy != expected_policy_sha256):
            findings.append("policy-mismatch")
        if expected_workspace_sha256 is not None:
            if workspace is None:
                findings.append("missing-workspace")
            elif workspace != expected_workspace_sha256:
                findings.append("workspace-mismatch")
        if expected_model is not None:
            model = header.get("model")
            if not isinstance(model, str) or not model:
                findings.append("missing-model")
            elif model != expected_model:
                findings.append("model-mismatch")
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
        "expected_policy_sha256": expected_policy_sha256,
        "expected_workspace_sha256": expected_workspace_sha256,
        "expected_model": expected_model,
    }
