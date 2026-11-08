"""Replay a log's actions through the world its header names.

``verify_chain`` proves the recorded bytes were not edited after writing;
``verify_episode_header`` proves the header's config is internally
consistent. Neither reads the action sequence, so a rewritten trajectory
with a recomputed chain verifies: replacing every action with ``wait`` and
re-emitting through ``Telemetry`` yields ``chain ok`` and ``header ok``
while the world never moves.

This module closes that gap by replaying the logged actions through
``GridWorld(task, seed)`` and comparing the world's own observations and
rewards against what the log recorded. It is read-only, deterministic, and
needs no trust in the log's self-reported summaries.
"""

from worlds.grid import GridWorld


def logged_steps(records):
    """Return the action records that carry a step, in log order."""
    return [record for record in records
            if record.get("type") == "action"
            and record.get("kind") == "step"
            and isinstance(record.get("args"), dict)
            and isinstance(record["args"].get("action"), str)]


def replay_actions(task, seed, actions, max_steps=200):
    """Replay ``actions`` through a fresh world; return the visited states."""
    world = GridWorld(task, seed)
    world.reset()
    states = []
    for index, action in enumerate(actions):
        if index >= int(max_steps):
            break
        state, reward, done = world.step(action)
        states.append({"state": state, "reward": float(reward),
                       "done": bool(done)})
        if done:
            break
    return states


def verify_action_replay(log_path, records=None, max_steps=200):
    """Replay a log's actions and report where the trajectory diverges.

    The header supplies ``task``/``seed``; each ``kind == "step"`` action
    record supplies one action. The replayed world's reward-bearing
    terminal state is compared with the log's own ``done`` flag and with
    the reward the log recorded for that step. Findings name the first
    divergence instead of reporting a bare boolean.
    """
    from telemetry.log import Telemetry

    if records is None:
        records = Telemetry(log_path).read_all()
    headers = [record for record in records if record.get("type") == "header"]
    steps = logged_steps(records)
    findings = []
    if not headers:
        return {"ok": False, "findings": ["missing-header"],
                "steps": len(steps), "replayed": 0}
    header = headers[0]
    task, seed = header.get("task"), header.get("seed")
    if not isinstance(task, str) or not task:
        return {"ok": False, "findings": ["invalid-task"],
                "steps": len(steps), "replayed": 0}
    if isinstance(seed, bool) or not isinstance(seed, int):
        return {"ok": False, "findings": ["missing-seed"],
                "steps": len(steps), "replayed": 0}
    actions = [record["args"]["action"] for record in steps]
    try:
        replay = replay_actions(task, seed, actions, max_steps=max_steps)
    except (ValueError, TypeError) as exc:
        return {"ok": False, "findings": ["unreplayable-action: %s" % exc],
                "steps": len(steps), "replayed": 0}
    for index, (record, replayed) in enumerate(zip(steps, replay)):
        recorded_reward = float((record.get("args") or {}).get("reward", 0.0))
        if abs(recorded_reward - replayed["reward"]) > 1e-9:
            findings.append("reward-mismatch:%d" % index)
            break
    if replay and steps:
        logged_done = bool((steps[-1].get("args") or {}).get("done"))
        if logged_done != replay[-1]["done"]:
            findings.append("done-mismatch")
    if len(replay) < len(steps):
        findings.append("replay-short:%d<%d" % (len(replay), len(steps)))
    return {
        "ok": not findings,
        "findings": findings,
        "steps": len(steps),
        "replayed": len(replay),
        "terminal": replay[-1]["state"] if replay else None,
    }
