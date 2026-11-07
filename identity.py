"""Episode identity and the resume guard (neurocore transfer).

Adapted from ``neurocore/core/episode_identity.py`` (AegeanWorks/
NeuroCore). An episode is resumed only when the caller addresses the
same episode and the normalised request/config match the stored digest.
A changed digest starts a new episode and leaves the old one paused, so
a stale plan cannot silently run against a different configuration.
Legacy episodes without a digest ask instead of resuming.
"""

import hashlib
import json

VOLATILE_KEYS = {
    "request_id", "trace_id", "session_id", "episode_id", "correlation_id",
    "nonce", "uuid", "timestamp", "timestamps", "ts", "created_at",
    "updated_at", "checkpoint_id", "parent_checkpoint_id",
}

RESUME_POLICIES = ("strict", "ask", "any")


def _clean(value):
    if isinstance(value, dict):
        return {
            key: _clean(item)
            for key, item in value.items()
            if str(key).lower() not in VOLATILE_KEYS
        }
    if isinstance(value, (list, tuple)):
        return [_clean(item) for item in value]
    return value


def canonical_projection(input_data, config=None):
    """The stable part of a request that must match before a resume."""
    config = config or {}
    projection = {
        "request": _clean(input_data or {}),
        "task": config.get("task") or "",
        "seed": config.get("seed"),
        "max_steps": config.get("max_steps"),
        "policy_sha256": config.get("policy_sha256") or "",
    }
    if config.get("plan") is not None:
        projection["plan"] = _clean(config.get("plan"))
    return projection


def digest_projection(projection):
    """SHA-256 over the canonical projection JSON."""
    payload = json.dumps(projection, sort_keys=True, separators=(",", ":"),
                         default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def input_digest(input_data, config=None):
    """Return ``(sha256, projection)`` for one request/config pair."""
    projection = canonical_projection(input_data, config)
    return digest_projection(projection), projection


def normalise_policy(policy):
    """Return a declared resume policy, defaulting to strict."""
    return policy if policy in RESUME_POLICIES else "strict"


def resume_decision(existing_sha, current_sha, policy="strict",
                    resume_any=False):
    """Return ``resume``, ``new`` or ``ask`` for one episode comparison."""
    if resume_any or normalise_policy(policy) == "any":
        return "resume"
    if not existing_sha:
        return "ask"
    if existing_sha == current_sha:
        return "resume"
    if normalise_policy(policy) == "ask":
        return "ask"
    return "new"


def resume_guard(episode, input_data, config=None, policy="strict"):
    """Compare an existing episode with this request.

    Returns ``(decision, current_sha, projection)`` so the caller can
    store the digest on the new episode and name the decision in a log.
    """
    current_sha, projection = input_digest(input_data, config)
    decision = resume_decision(
        getattr(episode, "input_sha256", None),
        current_sha,
        policy,
        bool((config or {}).get("resume_any", False)),
    )
    return decision, current_sha, projection


def prepare_resume(session_manager, episode, input_data, config=None):
    """Guard one candidate episode, pausing it when it must not resume.

    Returns ``(allowed, decision, current_sha, projection)``. A refused
    candidate is left paused on disk for inspection instead of being
    overwritten by the new episode.
    """
    config = config or {}
    policy = config.get("resume_policy", "strict")
    decision, current_sha, projection = resume_guard(
        episode, input_data, config, policy)
    if decision == "resume":
        if not getattr(episode, "input_sha256", None):
            episode.input_sha256 = current_sha
            episode.input_projection = projection
        return True, decision, current_sha, projection
    episode.update_phase("paused")
    session_manager.save_episode_state(phase="paused", add_checkpoint=False)
    return False, decision, current_sha, projection
