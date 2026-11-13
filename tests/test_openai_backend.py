"""The agent must be able to use the server a person already has running.

`LlamaCppBackend` requires a binary path and a GGUF, so the agent could only
reach a model Brain launched itself. `OpenAIBackend` closes that gap by
proposing actions through the same endpoint the chat CLI discovered.

Measured end to end against a real HTTP stub: `run_agent --backend openai`
completed T3_navigate seed 15 in 13 steps with reward 1.0, identical to the
rule policy. These tests pin the seam without a socket (injected client) and
pin the live CLI wiring through `run_agent`.
"""

import unittest

from agent import Agent, Planner
from models.openai_compat import EndpointUnavailable
from models.openai_backend import ACTION_TOKENS, OpenAIBackend, build_openai
from models.registry import build, names


class _Client:
    """A chat client double: fixed reply, records every call."""

    def __init__(self, text="right", model="fake-model"):
        self.text = text
        self.model = model
        self.calls = []

    def chat(self, messages, temperature=0.2, max_tokens=512):
        self.calls.append({"messages": list(messages),
                           "temperature": temperature,
                           "max_tokens": max_tokens})
        return {"text": self.text, "model": self.model, "seconds": 0.0,
                "usage": {}}


class _BrokenClient(_Client):
    def chat(self, *args, **kwargs):
        raise EndpointUnavailable(
            "Why: no server. Fix: start one with llama-server -m model.gguf.")


class TestIdentity(unittest.TestCase):
    def test_the_identity_names_the_model_not_the_class(self):
        self.assertEqual(OpenAIBackend(model="qwen2.5-3b").identity(),
                         "openai:qwen2.5-3b")
        self.assertEqual(OpenAIBackend().identity(), "openai:auto")

    def test_a_ready_client_and_an_endpoint_are_exclusive(self):
        with self.assertRaises(ValueError) as caught:
            OpenAIBackend(client=_Client(), endpoint="127.0.0.1:1")
        self.assertIn("Fix:", str(caught.exception))

    def test_a_bad_prompt_budget_is_refused(self):
        for bad in (0, -1, True, "12"):
            with self.assertRaises(ValueError):
                OpenAIBackend(client=_Client(), prompt_budget=bad)


class TestGenerate(unittest.TestCase):
    def test_a_legal_action_is_parsed_from_noisy_text(self):
        for text, expected in (("Right.", "right"), ("  UP  ", "up"),
                               ("I choose COLLECT", "collect"),
                               ("action: left!", "left")):
            backend = OpenAIBackend(client=_Client(text))
            self.assertEqual(backend.generate({"task": "T3_navigate"}),
                             expected, text)

    def test_unusable_text_returns_none_rather_than_raising(self):
        for text in ("banana", "", None, "12345"):
            backend = OpenAIBackend(client=_Client(text))
            self.assertIsNone(backend.generate({"task": "T3_navigate"}), text)

    def test_the_prompt_states_the_task_and_the_legal_actions(self):
        client = _Client("wait")
        backend = OpenAIBackend(client=client)
        backend.generate({"task": "T3_navigate", "x": 2, "y": 1, "steps": 3,
                          "legal": ["up", "down", "left", "right",
                                    "collect", "wait"]})
        prompt = client.calls[0]["messages"][0]["content"]
        self.assertIn("T3_navigate", prompt)
        self.assertIn("wait", prompt)
        self.assertEqual(client.calls[0]["temperature"], 0.0)
        self.assertEqual(client.calls[0]["max_tokens"], ACTION_TOKENS)

    def test_stats_and_manifest_are_recorded_for_provenance(self):
        backend = OpenAIBackend(client=_Client("down"))
        backend.generate({"task": "T1_forage", "x": 0, "y": 0, "steps": 0,
                          "legal": ["up", "down"]})
        self.assertGreater(backend.last_prompt_stats["tokens"], 0)
        self.assertEqual(len(backend.last_manifest["sha256"]), 64)

    def test_construction_does_not_touch_the_network(self):
        backend = OpenAIBackend(endpoint="127.0.0.1:1", model="m")
        self.assertEqual(backend.identity(), "openai:m")
        with self.assertRaises(EndpointUnavailable) as caught:
            backend.generate({"task": "T3_navigate", "x": 0, "y": 0,
                              "steps": 0, "legal": ["wait"]})
        self.assertIn("Fix:", str(caught.exception))


class TestRegistryAndCli(unittest.TestCase):
    def test_the_openai_backend_is_registered(self):
        self.assertIn("openai", names())
        backend = build("openai", endpoint="127.0.0.1:1", model="pinned")
        self.assertIsInstance(backend, OpenAIBackend)
        self.assertEqual(backend.identity(), "openai:pinned")

    def test_the_factory_builds_the_same_backend(self):
        self.assertEqual(build_openai(model="m").identity(), "openai:m")

    def test_run_agent_builds_the_backend_from_flags(self):
        import run_agent
        backend = run_agent._build_backend(
            "openai", [], endpoint="127.0.0.1:8199", model="served")
        self.assertIsInstance(backend, OpenAIBackend)
        self.assertEqual(backend.identity(), "openai:served")

    def test_run_agent_refuses_an_unknown_backend(self):
        import run_agent
        with self.assertRaises(SystemExit) as caught:
            run_agent._build_backend("nope", [])
        self.assertEqual(caught.exception.code, 2)


class TestAgentIntegration(unittest.TestCase):
    def _agent(self, client):
        backend = OpenAIBackend(client=client)
        return Agent(planner=Planner(backend=backend)), backend

    def test_the_model_is_consulted_and_the_episode_still_completes(self):
        client = _Client("right")
        agent, backend = self._agent(client)
        trace = agent.run_task("T3_navigate", 15, max_steps=200)
        self.assertTrue(client.calls, "the backend was never consulted")
        # Guard paths (distrust, progress skip) deliberately bypass the backend,
        # so a 13-step episode consults it 11 times rather than 13.
        self.assertGreaterEqual(len(client.calls), len(trace) - 3)
        self.assertEqual(trace[-1].get("done"), True)
        self.assertEqual(sum(float(s.get("reward", 0.0)) for s in trace), 1.0)

    def test_a_dead_server_falls_back_to_the_rule_policy(self):
        backend = OpenAIBackend(client=_BrokenClient())
        agent = Agent(planner=Planner(backend=backend))
        trace = agent.run_task("T3_navigate", 15, max_steps=200)
        self.assertEqual(len(trace), 13)
        self.assertEqual(trace[-1].get("done"), True,
                         "a raising backend must not stop the episode")


if __name__ == "__main__":
    unittest.main()
