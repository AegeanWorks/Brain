"""Generation manifest fingerprints: determinism + prompt-set versioning.

Transferred idea: ModelDuck generation manifests (prompt/history/
settings/model identity fingerprints) and benchmark test-hash
discipline, Brain-sized for the model seam. Same inputs always give
the same sha256; any prompt-set change gives a different one, so
before/after batteries prove they ran identical prompts.
"""

import json
import unittest
from unittest import mock

from agent import Planner
from models.backend import ModelBackend
from models.llamacpp import build_prompt
from models.manifest import manifest_for, prompt_set_manifest


class _CompletionResponse:
    """Minimal urlopen response for a successful /v1/chat/completions call."""

    def __init__(self, content):
        self._body = json.dumps(
            {"choices": [{"message": {"content": content}}]}).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._body


def _enriched_obs():
    return {"task": "T3_navigate", "x": 5, "y": 0, "steps": 7,
            "legal": ["up", "down", "left", "right", "collect", "wait"],
            "target": [6, 7], "obstacles": [[6, 1]],
            "visits": [[4, 0, 1], [5, 0, 2]]}


def _sampling():
    return {"temperature": 0.0, "seed": 0, "n_predict": 24,
            "cache_prompt": True}


class TestManifest(unittest.TestCase):
    def test_same_inputs_same_sha256(self):
        obs = _enriched_obs()
        prompt = build_prompt(obs)
        first = manifest_for(prompt, obs, model_id="m", checkpoint="c",
                             sampling=_sampling())["sha256"]
        for _ in range(3):
            again = manifest_for(prompt, obs, model_id="m",
                                 checkpoint="c",
                                 sampling=_sampling())["sha256"]
            self.assertEqual(again, first)
        self.assertEqual(len(first), 64)

    def test_prompt_change_changes_sha256(self):
        obs = _enriched_obs()
        minimal = {k: obs[k] for k in ("task", "x", "y", "steps", "legal")}
        full = manifest_for(build_prompt(obs), obs, sampling=_sampling())
        slim = manifest_for(build_prompt(minimal), minimal,
                            sampling=_sampling())
        self.assertNotEqual(full["sha256"], slim["sha256"])
        self.assertNotIn("Target", build_prompt(minimal))
        self.assertIn("Target", build_prompt(obs))

    def test_visits_change_changes_sha256(self):
        obs = _enriched_obs()
        other = dict(obs)
        other["visits"] = [[4, 0, 1], [5, 0, 3]]
        a = manifest_for(build_prompt(obs), obs, sampling=_sampling())
        b = manifest_for(build_prompt(other), other, sampling=_sampling())
        self.assertNotEqual(a["sha256"], b["sha256"])

    def test_planner_obs_prompt_manifest_chain_stable(self):
        seen = []

        class Cap(ModelBackend):
            def generate(self, observation):
                seen.append(dict(observation))
                return "north"

        state = {"task": "T3_navigate", "x": 5, "y": 0, "steps": 7,
                 "target": [6, 7], "obstacles": [[6, 1]]}
        Planner(backend=Cap()).plan(dict(state), [{"x": 5, "y": 0},
                                                  {"x": 4, "y": 0}])
        obs = seen[0]
        first = manifest_for(build_prompt(obs), obs, sampling=_sampling())
        again = manifest_for(build_prompt(dict(obs)), dict(obs),
                             sampling=_sampling())
        self.assertEqual(first["sha256"], again["sha256"])

    def test_prompt_set_manifest_order_independent(self):
        a = manifest_for("p1", {"x": 1}, sampling=_sampling())["sha256"]
        b = manifest_for("p2", {"x": 2}, sampling=_sampling())["sha256"]
        self.assertEqual(prompt_set_manifest([a, b]),
                         prompt_set_manifest([b, a]))
        self.assertNotEqual(prompt_set_manifest([a, b]),
                            prompt_set_manifest([a, "other"]))

    def test_backend_exposes_last_manifest_slot(self):
        from models.llamacpp import LlamaCppBackend
        backend = LlamaCppBackend("server-exe", "model.gguf")
        self.assertIsNone(backend.last_manifest)

    def test_generate_records_last_manifest(self):
        # ADR-021 promises a manifest on every generate(), not just the
        # constructor slot. Stub urlopen so a successful call must record one.
        from models.llamacpp import LlamaCppBackend
        backend = LlamaCppBackend("server-exe", "model.gguf")
        with mock.patch("urllib.request.urlopen",
                        return_value=_CompletionResponse("up")):
            action = backend.generate(_enriched_obs())
        self.assertEqual(action, "up")
        manifest = backend.last_manifest
        self.assertIsInstance(manifest, dict)
        self.assertEqual(len(manifest["sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
