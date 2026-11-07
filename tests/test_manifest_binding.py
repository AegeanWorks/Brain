"""Model-manifest binding: every model decision carries its generation hash.

Failing-first: before the probe, a backend can compute ``last_manifest``
(model id, checkpoint, prompt, observation, sampling) but the run log
discards it, so a checkpoint swap is invisible. After, each
``model_decision`` carries ``model_manifest_sha256``; the action trace
and prompts are unchanged.
"""

import itertools
import json
import os
import tempfile
import unittest

from agent import Agent, PLANNER_POLICY, Planner, policy_digest
from models.backend import ModelBackend
from models.llamacpp import build_prompt
from models.manifest import manifest_for
from telemetry.log import Telemetry

SAMPLING = {"temperature": 0.0, "seed": 7,
            "n_predict": 0, "cache_prompt": True}
_RUNS = itertools.count()


class ManifestBackend(ModelBackend):
    """Record the observation, compute its manifest, then decline."""

    def __init__(self, checkpoint="A", model_id="manifest-stub"):
        self.checkpoint = checkpoint
        self.model_id = model_id
        self.seen = []
        self.calls = 0
        self.last_manifest = None

    def generate(self, observation):
        self.calls += 1
        obs = json.loads(json.dumps(observation, sort_keys=True))
        self.seen.append(obs)
        self.last_manifest = manifest_for(
            build_prompt(obs), obs, model_id=self.model_id,
            checkpoint=self.checkpoint, sampling=SAMPLING)
        return None


class StaleRaisingBackend(ModelBackend):
    """Leave a stale manifest behind, then raise before computing a new one."""

    def __init__(self):
        self.last_manifest = {"sha256": "stale"}

    def generate(self, observation):
        raise RuntimeError("injected backend failure")


def _run(tmp, backend, probe_manifest=True):
    log_path = os.path.join(tmp, "run-%d.jsonl" % next(_RUNS))
    agent = Agent(planner=Planner(backend=backend,
                                  probe_manifest=probe_manifest),
                  telemetry_log=Telemetry(log_path))
    trace = agent.run_task("T3_navigate", 15, max_steps=200)
    steps = [record for record in Telemetry(log_path).read_all()
             if record.get("type") == "action"
             and record.get("kind") == "step"]
    return agent, trace, steps


def _decision(record):
    return record["args"]["probe"]["model_decision"]


class TestManifestBinding(unittest.TestCase):
    def test_each_decision_binds_its_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            backend = ManifestBackend("A")
            _agent, trace, steps = _run(tmp, backend)
        self.assertEqual(len(steps), len(trace))
        self.assertEqual(backend.calls, len(trace))
        for index, record in enumerate(steps):
            observation = backend.seen[index]
            want = manifest_for(
                build_prompt(observation), observation,
                model_id="manifest-stub", checkpoint="A",
                sampling=SAMPLING)["sha256"]
            self.assertEqual(_decision(record)["model_manifest_sha256"], want)

    def test_checkpoint_swap_changes_manifest_not_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            first_backend = ManifestBackend("A")
            _a, first_trace, first_steps = _run(tmp, first_backend)
            second_backend = ManifestBackend("B")
            _b, second_trace, second_steps = _run(tmp, second_backend)
        self.assertEqual([record["action"] for record in first_trace],
                         [record["action"] for record in second_trace])
        self.assertNotEqual(
            _decision(first_steps[0])["model_manifest_sha256"],
            _decision(second_steps[0])["model_manifest_sha256"])

    def test_probe_off_removes_binding_without_changing_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            _a, intact_trace, intact_steps = _run(tmp, ManifestBackend("A"))
            _b, ablated_trace, ablated_steps = _run(
                tmp, ManifestBackend("A"), probe_manifest=False)
        self.assertEqual([record["action"] for record in intact_trace],
                         [record["action"] for record in ablated_trace])
        self.assertIn("model_manifest_sha256", _decision(intact_steps[0]))
        self.assertNotIn("model_manifest_sha256", _decision(ablated_steps[0]))

    def test_raising_backend_does_not_leak_stale_manifest(self):
        backend = StaleRaisingBackend()
        agent = Agent(planner=Planner(backend=backend))
        agent.run_task("T3_navigate", 15, max_steps=2)
        decision = agent.planner.last_probe["model_decision"]
        self.assertIsNone(decision["model_manifest_sha256"])

    def test_policy_declares_manifest_probe(self):
        self.assertEqual(PLANNER_POLICY.get("model_manifest_probe"), "on")
        legacy = dict(PLANNER_POLICY)
        legacy.pop("model_manifest_probe", None)
        self.assertNotEqual(policy_digest(), policy_digest(legacy))
        altered = dict(PLANNER_POLICY)
        altered["model_manifest_probe"] = "off"
        self.assertNotEqual(policy_digest(), policy_digest(altered))

    def test_invalid_manifest_probe_rejected(self):
        with self.assertRaises(ValueError):
            Planner(probe_manifest="yes")


if __name__ == "__main__":
    unittest.main()
