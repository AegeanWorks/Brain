"""Failing-first tests for genuine review findings in the runtime files.

Each test targets a code path/message, never a historical line number. The
file is added by the runtime-fix subagent; existing test files are untouched.
"""

import os
import unittest
from unittest import mock

from episode_replay import verify_action_replay
from episode_verify import verify_episode_header
from identity import resume_decision
from models.backend import StubBackend
from models.conformance import check_backend
from models.openai_compat import EndpointUnavailable, normalize_endpoint, resolve
from self_model.model import SelfModel

OBS = {"task": "T3_navigate", "legal": ["wait", "up"]}


class TestAnyPolicyResumesLegacy(unittest.TestCase):
    """A legacy episode (no stored digest) must ask, even under 'any'."""

    def test_any_policy_asks_on_a_legacy_episode(self):
        self.assertEqual(resume_decision(None, "sha", "any"), "ask")

    def test_resume_any_flag_asks_on_a_legacy_episode(self):
        self.assertEqual(
            resume_decision(None, "sha", "strict", resume_any=True), "ask")


class TestClaimedKeyOnEarlyReturns(unittest.TestCase):
    """``claimed`` must be reported on every early-return shape."""

    def _check(self, records):
        return verify_action_replay("unused.jsonl", records=records,
                                    check_verdict=True)

    def test_invalid_task_reports_claimed(self):
        result = self._check([{"type": "header", "task": "", "seed": 15}])
        self.assertEqual(result["findings"], ["invalid-task"])
        self.assertIn("claimed", result)
        self.assertIsNone(result["claimed"])

    def test_missing_seed_reports_claimed(self):
        result = self._check([{"type": "header", "task": "T3_navigate",
                               "seed": "bad"}])
        self.assertEqual(result["findings"], ["missing-seed"])
        self.assertIn("claimed", result)
        self.assertIsNone(result["claimed"])

    def test_unreplayable_action_reports_claimed(self):
        records = [{"type": "header", "task": "T3_navigate", "seed": 15},
                   {"type": "action", "kind": "step",
                    "args": {"action": "wait"}}]
        with mock.patch("episode_replay.replay_actions",
                        side_effect=ValueError("bad action")):
            result = self._check(records)
        self.assertEqual(result["findings"], ["unreplayable-action: bad action"])
        self.assertIn("claimed", result)
        self.assertIsNone(result["claimed"])


class TestPinOnEmptyHeaderReturn(unittest.TestCase):
    """The expected_model pin is echoed even when there is no header."""

    def test_missing_header_echoes_expected_model(self):
        path = os.path.join(os.path.dirname(__file__),
                            "no-such-log-for-fix-test.jsonl")
        result = verify_episode_header(path, expected_model="rule")
        self.assertEqual(result["findings"], ["missing-header"])
        self.assertEqual(result["expected_model"], "rule")


class TestClassNameIdentityDetected(unittest.TestCase):
    """A class-name-derived identity is flagged under any prefix."""

    def test_stub_backend_identity_is_flagged(self):
        report = check_backend(StubBackend(["wait"] * 4), OBS)
        self.assertIn("identity-from-class-name", report["findings"])

    def test_a_non_module_prefix_still_flags_class_name(self):
        class VendorProvider(StubBackend):
            def identity(self):
                return "vendor:%s" % type(self).__name__

        report = check_backend(VendorProvider(["wait"] * 4), OBS)
        self.assertIn("identity-from-class-name", report["findings"])


class _DeadClient:
    def __init__(self, url, model=None):
        self.base = normalize_endpoint(url)

    def is_alive(self):
        return False


class _LiveClient(_DeadClient):
    def is_alive(self):
        return True


class TestExplicitEndpointProbed(unittest.TestCase):
    """An explicit endpoint is probed even when no probe is injected."""

    def test_dead_explicit_endpoint_fails_without_a_probe(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(EndpointUnavailable):
                resolve(endpoint="127.0.0.1:7777",
                        client_factory=_DeadClient)

    def test_live_explicit_endpoint_still_resolves(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            client, source = resolve(endpoint="127.0.0.1:7777",
                                     client_factory=_LiveClient)
        self.assertEqual(source, "--endpoint")
        self.assertEqual(client.base, "http://127.0.0.1:7777")


class TestGlobalPreOutcomeFlag(unittest.TestCase):
    """Post-hoc pairs stay flagged after an earlier pre-outcome pair."""

    def test_mixed_pairs_keep_the_circularity_warning(self):
        model = SelfModel()
        model.record_prediction(1.0, True, 0.8)
        model.record_prediction(1.0, False, 0.05)
        model.record(1.0, True, 1.0)
        model.record(1.0, False, 0.5)
        result = model.calibration(min_resolved=1)
        self.assertTrue(any("confidence-is-outcome" in w
                            for w in result["warnings"]))


class TestMojibakeEmDash(unittest.TestCase):
    """The online.py docstrings use a real em dash, not UTF-8 mojibake."""

    def test_no_mojibake_in_online_docstrings(self):
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            "self_model", "online.py")
        with open(path, "rb") as handle:
            text = handle.read().decode("utf-8")
        mojibake = "\u00e2\u20ac\u201d"
        self.assertNotIn(mojibake, text)
        self.assertIn("\u2014", text)


if __name__ == "__main__":
    unittest.main()
