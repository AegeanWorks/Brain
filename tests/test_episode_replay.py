"""Action-replay verification: a valid chain does not prove the trajectory.

``verify_chain`` proves the recorded bytes were not edited after writing and
``verify_episode_header`` proves the header's config is self-consistent.
Neither reads the action sequence. Measured: replacing every action with
``wait`` and re-emitting the log through ``Telemetry`` produced
``chain ok: True`` and ``episode header ok: True`` while replaying those
actions left the world at (0, 0) with no reward.

``episode_replay.verify_action_replay`` closes that gap by replaying the
logged actions through ``GridWorld(task, seed)`` and comparing the world's
own rewards and terminal flag with the log.
"""

import os
import tempfile
import unittest

from agent import Agent
from episode_replay import logged_steps, replay_actions, verify_action_replay
from telemetry.log import Telemetry, verify_chain


def _write_log(directory, name, task="T3_navigate", seed=15):
    path = os.path.join(directory, name)
    trace = Agent().run_task_logged(task, seed, max_steps=200, log_path=path)
    return path, trace


def _rewrite(log_path, out_path, action="wait"):
    """Re-emit a log through Telemetry with every step action replaced."""
    tel = Telemetry(out_path)
    for record in Telemetry(log_path).read_all():
        kind = record.get("type")
        if kind == "header":
            tel.write_header(
                record["task"], record["budget"], policy=record.get("policy"),
                policy_sha256=record.get("policy_sha256"),
                model=record.get("model"),
                episode_sha256=record.get("episode_sha256"),
                workspace_sha256=record.get("workspace_sha256"),
                seed=record.get("seed"),
                manifest_sha256=record.get("manifest_sha256"))
        elif kind == "action":
            args = dict(record.get("args") or {})
            if record.get("kind") == "step":
                args["action"] = action
            tel.append_action(record["seq"], record.get("kind") or "exec", args,
                              M=record.get("M"), P=record.get("P"),
                              S=record.get("S"), hub=record.get("hub"))
        elif kind == "result":
            tel.append_result(record["seq"], bool(record.get("ok")),
                              record.get("output"), record.get("cost"),
                              M=record.get("M"), P=record.get("P"),
                              S=record.get("S"), hub=record.get("hub"))
        elif kind == "verdict":
            tel.write_verdict(record.get("verdict"), record.get("reason"))
    return out_path


class TestActionReplay(unittest.TestCase):
    def test_logged_steps_are_the_step_actions(self):
        with tempfile.TemporaryDirectory() as d:
            path, trace = _write_log(d, "run.jsonl")
            steps = logged_steps(Telemetry(path).read_all())
        self.assertEqual(len(steps), len(trace))
        self.assertEqual([s["args"]["action"] for s in steps],
                         [r["action"] for r in trace])

    def test_replay_reproduces_the_recorded_trajectory(self):
        with tempfile.TemporaryDirectory() as d:
            path, trace = _write_log(d, "run.jsonl")
            result = verify_action_replay(path)
        self.assertTrue(result["ok"], result["findings"])
        self.assertEqual(result["steps"], len(trace))
        self.assertEqual(result["replayed"], len(trace))
        self.assertEqual(result["terminal"]["x"], 6)
        self.assertEqual(result["terminal"]["y"], 7)

    def test_valid_chain_with_replaced_actions_is_caught(self):
        with tempfile.TemporaryDirectory() as d:
            path, trace = _write_log(d, "run.jsonl")
            forged = _rewrite(path, os.path.join(d, "forged.jsonl"))
            # The forgery is chain-valid: this is the whole point.
            self.assertTrue(verify_chain(forged)["ok"])
            result = verify_action_replay(forged)
        self.assertFalse(result["ok"])
        self.assertTrue(any(f.startswith("reward-mismatch")
                            or f == "done-mismatch"
                            for f in result["findings"]), result["findings"])

    def test_replay_stops_at_the_world_terminal(self):
        with tempfile.TemporaryDirectory() as d:
            path, trace = _write_log(d, "run.jsonl")
            records = Telemetry(path).read_all()
            actions = [s["args"]["action"] for s in logged_steps(records)]
            replayed = replay_actions("T3_navigate", 15, actions)
        self.assertEqual(len(replayed), len(trace))
        self.assertTrue(replayed[-1]["done"])
        self.assertAlmostEqual(sum(r["reward"] for r in replayed), 1.0)

    def test_invalid_actions_are_named_not_raised(self):
        with tempfile.TemporaryDirectory() as d:
            path, _trace = _write_log(d, "run.jsonl")
            forged = _rewrite(path, os.path.join(d, "forged.jsonl"),
                              action="teleport")
            result = verify_action_replay(forged)
        self.assertFalse(result["ok"])
        self.assertTrue(result["findings"][0].startswith("unreplayable-action"))

    def test_missing_header_is_named(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "empty.jsonl")
            with open(path, "w", encoding="utf-8"):
                pass
            result = verify_action_replay(path)
        self.assertFalse(result["ok"])
        self.assertEqual(result["findings"], ["missing-header"])


if __name__ == "__main__":
    unittest.main()
