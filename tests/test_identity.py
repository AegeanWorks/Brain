"""Episode identity and resume policy (neurocore transfer).

Failing-first: there is no canonical projection/digest or resume/new/ask
decision. A stable digest must ignore volatile keys, bind task/seed/
max_steps/policy, and appear in logged run headers so a rerun can be
compared with a stored episode.
"""

import json
import os
import tempfile
import unittest

from agent import Agent, policy_digest
from identity import (canonical_projection, digest_projection, input_digest,
                      normalise_policy, prepare_resume, resume_decision,
                      resume_guard)
from telemetry.log import Telemetry
from worlds.grid import GridWorld

STATE = {
    "task": "T3_navigate", "x": 0, "y": 0, "energy": 200, "items": 0,
    "steps": 0, "target": [3, 3], "obstacles": [[3, 2]], "ts": 123,
}
CONFIG = {"task": "T3_navigate", "seed": 15, "max_steps": 200,
          "policy_sha256": "a" * 64}


class FakeEpisode:
    def __init__(self, sha):
        self.input_sha256 = sha
        self.input_projection = None
        self.phase = "active"
        self.pauses = 0

    def update_phase(self, phase):
        self.phase = phase
        self.pauses += 1


class FakeSession:
    def __init__(self):
        self.saved = []

    def save_episode_state(self, **kwargs):
        self.saved.append(kwargs)


class TestEpisodeIdentity(unittest.TestCase):
    def test_volatile_fields_are_ignored(self):
        first = dict(STATE, ts=1, created_at="a", session_id="x")
        second = dict(STATE, ts=999, created_at="b", session_id="y")
        self.assertEqual(input_digest(first, CONFIG)[0],
                         input_digest(second, CONFIG)[0])

    def test_changed_target_changes_digest(self):
        changed = dict(STATE, target=[7, 7])
        self.assertNotEqual(input_digest(STATE, CONFIG)[0],
                            input_digest(changed, CONFIG)[0])

    def test_changed_config_changes_digest(self):
        base = input_digest(STATE, CONFIG)[0]
        for change in ({"seed": 16}, {"max_steps": 100},
                       {"policy_sha256": "b" * 64}):
            altered = dict(CONFIG, **change)
            self.assertNotEqual(base, input_digest(STATE, altered)[0])

    def test_projection_is_canonical(self):
        first = canonical_projection(STATE, CONFIG)
        second = canonical_projection(dict(STATE), dict(CONFIG))
        self.assertEqual(first, second)
        self.assertEqual(digest_projection(first), digest_projection(second))
        json.dumps(first, sort_keys=True)

    def test_resume_decision_matrix(self):
        self.assertEqual(resume_decision(None, "sha", "strict"), "ask")
        self.assertEqual(resume_decision("sha", "sha", "strict"), "resume")
        self.assertEqual(resume_decision("sha", "other", "strict"), "new")
        self.assertEqual(resume_decision("sha", "other", "ask"), "ask")
        self.assertEqual(resume_decision("sha", "other", "any"), "resume")
        self.assertEqual(resume_decision("sha", "other", "strict",
                                         resume_any=True), "resume")
        self.assertEqual(normalise_policy("bogus"), "strict")

    def test_resume_guard_fake_episode(self):
        sha, _projection = input_digest(STATE, CONFIG)
        episode = FakeEpisode(sha)
        decision, current, projection = resume_guard(
            episode, STATE, CONFIG, "strict")
        self.assertEqual(decision, "resume")
        self.assertEqual(current, sha)
        self.assertIn("request", projection)
        changed = dict(STATE, target=[7, 7])
        decision, current, _ = resume_guard(episode, changed, CONFIG, "strict")
        self.assertEqual(decision, "new")

    def test_prepare_resume_pauses_refused_candidate(self):
        sha, _projection = input_digest(STATE, CONFIG)
        episode = FakeEpisode("old")
        session = FakeSession()
        allowed, decision, current, _ = prepare_resume(
            session, episode, STATE, CONFIG)
        self.assertFalse(allowed)
        self.assertEqual(decision, "new")
        self.assertEqual(current, sha)
        self.assertEqual(episode.phase, "paused")
        self.assertEqual(episode.pauses, 1)
        self.assertEqual(session.saved, [{"phase": "paused",
                                          "add_checkpoint": False}])

    def test_prepare_resume_allows_matching_candidate(self):
        sha, _projection = input_digest(STATE, CONFIG)
        episode = FakeEpisode(sha)
        session = FakeSession()
        allowed, decision, _current, _ = prepare_resume(
            session, episode, STATE, CONFIG)
        self.assertTrue(allowed)
        self.assertEqual(decision, "resume")
        self.assertEqual(episode.phase, "active")
        self.assertEqual(session.saved, [])

    def test_logged_header_carries_episode_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            logs = {}
            for seed in (15, 65, 15):
                path = os.path.join(tmp, "run-%d-%d.jsonl"
                                    % (seed, len(logs)))
                trace = Agent().run_task_logged(
                    "T3_navigate", seed, max_steps=200, log_path=path)
                header = Telemetry(path).read_all()[0]
                logs[(seed, len(logs))] = (header["episode_sha256"],
                                           len(trace))
            first_state = GridWorld("T3_navigate", 15).reset()
            want = input_digest(first_state, {
                "task": "T3_navigate", "seed": 15, "max_steps": 200,
                "policy_sha256": policy_digest(),
            })[0]
        self.assertEqual(logs[(15, 0)][0], want)
        self.assertEqual(logs[(15, 2)][0], want)
        self.assertNotEqual(logs[(65, 1)][0], want)
        self.assertEqual(logs[(15, 0)][1], 13)
        self.assertEqual(logs[(65, 1)][1], 6)


if __name__ == "__main__":
    unittest.main()
