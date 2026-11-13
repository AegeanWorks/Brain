"""Model access must be reachable, honest and testable without a socket.

The complaint this answers is "we cannot access the model". These tests pin
the parts of that fix that can be checked offline:

* endpoint parsing accepts what people paste and rejects nothing valid;
* an unreachable server produces a message naming the address and the fix
  (never an empty reply, never a silent fallback);
* discovery prefers an explicit endpoint over $BRAIN_ENDPOINT over probing;
* the chat session keeps the system prompt, trims oldest turns, and shows a
  footer so a reply is attributable.
"""

import os
import unittest
from unittest import mock

from chat_session import COMMANDS, ChatSession
from models.openai_compat import (CANDIDATES, ENDPOINT_ENV, OpenAIClient,
                                  _message_text, describe_available,
                                  normalize_endpoint, resolve)


def _fake_transport(replies):
    """Return a transport that pops canned ``(method, path)`` replies.

    ``replies`` maps a path suffix to a body dict; an exception value is
    raised instead, which is how the unreachable case is simulated.
    """
    calls = []

    def transport(method, url, payload, timeout):
        calls.append((method, url, payload, timeout))
        for suffix, body in replies.items():
            if url.endswith(suffix):
                if isinstance(body, Exception):
                    raise body
                return body
        raise AssertionError("unexpected request: %s %s" % (method, url))

    transport.calls = calls
    return transport


def _chat_body(text, model="local-model"):
    return {"model": model,
            "choices": [{"message": {"role": "assistant", "content": text}}],
            "usage": {"total_tokens": 12}}


class TestNormalize(unittest.TestCase):
    def test_a_bare_host_port_gets_a_scheme(self):
        self.assertEqual(normalize_endpoint("localhost:8080"),
                         "http://localhost:8080")

    def test_trailing_slash_and_v1_are_removed(self):
        self.assertEqual(normalize_endpoint("http://127.0.0.1:1234/"),
                         "http://127.0.0.1:1234")
        self.assertEqual(normalize_endpoint("http://127.0.0.1:11434/v1"),
                         "http://127.0.0.1:11434")
        self.assertEqual(
            normalize_endpoint("http://127.0.0.1:11434/v1/chat/completions"),
            "http://127.0.0.1:11434")

    def test_an_empty_endpoint_is_refused_with_a_fix(self):
        for bad in ("", "   ", None):
            with self.assertRaises(RuntimeError) as caught:
                normalize_endpoint(bad)
            self.assertIn("Fix:", str(caught.exception))


class TestMessageText(unittest.TestCase):
    def test_a_normal_choice_is_read(self):
        self.assertEqual(_message_text(_chat_body("  hello  ")), "hello")

    def test_a_legacy_text_choice_is_read(self):
        self.assertEqual(_message_text({"choices": [{"text": "hi"}]}), "hi")

    def test_a_missing_or_odd_body_is_empty_not_a_crash(self):
        for body in ({}, {"choices": []}, {"choices": [{}]},
                     {"choices": "nope"}, {"choices": [{"message": {}}]}):
            self.assertEqual(_message_text(body), "")


class TestClient(unittest.TestCase):
    def test_chat_returns_text_model_and_timing(self):
        transport = _fake_transport({
            "/v1/chat/completions": _chat_body("pong", "qwen2.5-3b")})
        client = OpenAIClient("127.0.0.1:8080", transport=transport)
        result = client.chat([{"role": "user", "content": "ping"}])
        self.assertEqual(result["text"], "pong")
        self.assertEqual(result["model"], "qwen2.5-3b")
        self.assertGreaterEqual(result["seconds"], 0.0)
        method, url, payload, _timeout = transport.calls[0]
        self.assertEqual(method, "POST")
        self.assertEqual(url, "http://127.0.0.1:8080/v1/chat/completions")
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["messages"][0]["content"], "ping")

    def test_a_pinned_model_is_sent(self):
        transport = _fake_transport({"/v1/chat/completions": _chat_body("ok")})
        client = OpenAIClient("127.0.0.1:8080", model="pinned",
                              transport=transport)
        client.chat([{"role": "user", "content": "x"}])
        self.assertEqual(transport.calls[0][2]["model"], "pinned")

    def test_an_unreachable_server_names_address_and_fix(self):
        transport = _fake_transport({
            "/v1/chat/completions": OSError("connection refused")})
        client = OpenAIClient("127.0.0.1:9999", transport=transport)
        with self.assertRaises(RuntimeError) as caught:
            client.chat([{"role": "user", "content": "x"}])
        message = str(caught.exception)
        self.assertIn("http://127.0.0.1:9999", message)
        self.assertIn("Fix:", message)
        self.assertIn("llama-server", message)

    def test_an_empty_reply_is_an_error_not_an_empty_bubble(self):
        transport = _fake_transport({
            "/v1/chat/completions": {"choices": [{"message": {"content": ""}}]}})
        client = OpenAIClient("127.0.0.1:8080", transport=transport)
        with self.assertRaises(RuntimeError) as caught:
            client.chat([{"role": "user", "content": "x"}])
        self.assertIn("returned no text", str(caught.exception))

    def test_models_lists_ids_and_is_empty_when_absent(self):
        listed = _fake_transport({"/v1/models": {
            "data": [{"id": "a"}, {"id": "b"}, {"nope": 1}]}})
        self.assertEqual(OpenAIClient("h:1", transport=listed).models(),
                         ["a", "b"])
        empty = _fake_transport({"/v1/models": {}})
        self.assertEqual(OpenAIClient("h:1", transport=empty).models(), [])

    def test_identify_prefers_the_pin_then_the_first_served_model(self):
        listed = _fake_transport({"/v1/models": {"data": [{"id": "served"}]}})
        self.assertEqual(OpenAIClient("h:1", transport=listed).identify(),
                         ("served", "http://h:1"))
        self.assertEqual(
            OpenAIClient("h:1", model="pinned", transport=listed).identify(),
            ("pinned", "http://h:1"))

    def test_is_alive_is_false_not_fatal(self):
        dead = _fake_transport({"/v1/models": OSError("refused")})
        self.assertFalse(OpenAIClient("h:1", transport=dead).is_alive())


class TestResolve(unittest.TestCase):
    def test_an_explicit_endpoint_wins_and_is_labelled(self):
        client, source = resolve(endpoint="127.0.0.1:7777",
                                 probe=lambda _c: True)
        self.assertEqual(source, "--endpoint")
        self.assertEqual(client.base, "http://127.0.0.1:7777")

    def test_an_explicit_dead_endpoint_fails_loudly(self):
        with self.assertRaises(RuntimeError) as caught:
            resolve(endpoint="127.0.0.1:7777", probe=lambda _c: False)
        self.assertIn("nothing answered", str(caught.exception))

    def test_the_environment_variable_is_used_when_no_argument_given(self):
        from models import openai_compat as module
        with mock.patch.object(module, "ENDPOINT_ENV", "BRAIN_TEST_ENDPOINT"):
            with mock.patch.dict(os.environ, {"BRAIN_TEST_ENDPOINT":
                                              "127.0.0.1:6666"}):
                client, source = resolve(probe=lambda _c: True)
        self.assertEqual(source, "$BRAIN_TEST_ENDPOINT")
        self.assertEqual(client.base, "http://127.0.0.1:6666")

    def test_discovery_reports_which_runtime_answered(self):
        seen = []

        def probe(client):
            seen.append(client.base)
            return client.base.endswith(":1234")

        client, source = resolve(probe=probe)
        self.assertIn("LM Studio", source)
        self.assertEqual(client.base, "http://127.0.0.1:1234")
        self.assertEqual(seen[0], CANDIDATES[0][0])

    def test_nothing_answering_lists_every_way_to_start_a_server(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError) as caught:
                resolve(probe=lambda _c: False)
        message = str(caught.exception)
        for name in ("llama.cpp", "LM Studio", "Ollama", "vLLM"):
            self.assertIn(name, message)
        self.assertIn("brain.py run", message)

    def test_the_shared_hint_names_a_concrete_command(self):
        text = describe_available()
        self.assertIn("llama-server -m", text)
        self.assertIn("ollama pull", text)


class TestChatSession(unittest.TestCase):
    def _session(self, texts=("one", "two"), **kwargs):
        client = OpenAIClient(
            "h:1", transport=_fake_transport({
                "/v1/chat/completions": _chat_body(texts[0])}))
        return ChatSession(client, **kwargs)

    def test_a_turn_appends_the_question_and_answer(self):
        session = self._session()
        result = session.ask("hello")
        self.assertEqual(result["text"], "one")
        roles = [m["role"] for m in session.messages]
        self.assertEqual(roles, ["system", "user", "assistant"])
        self.assertEqual(session.messages[1]["content"], "hello")
        self.assertEqual(session.turns, 1)

    def test_the_system_prompt_survives_a_reset(self):
        session = self._session()
        session.ask("hello")
        self.assertEqual(session.reset(), 2)
        self.assertEqual([m["role"] for m in session.messages], ["system"])
        self.assertEqual(session.turns, 0)

    def test_the_cap_drops_oldest_turns_but_keeps_the_system_prompt(self):
        session = self._session(max_turns=2)
        for turn in range(4):
            session.client = OpenAIClient(
                "h:1", transport=_fake_transport({
                    "/v1/chat/completions": _chat_body("r%d" % turn)}))
            session.ask("q%d" % turn)
        self.assertLessEqual(len(session.messages) - 1, 2)
        self.assertEqual(session.messages[0]["role"], "system")
        self.assertEqual(session.messages[-1]["content"], "r3")

    def test_an_empty_message_is_refused_before_any_request(self):
        session = self._session()
        with self.assertRaises(ValueError):
            session.ask("   ")
        self.assertEqual(session.turns, 0)
        self.assertEqual(len(session.messages), 1)

    def test_a_tiny_cap_is_refused(self):
        with self.assertRaises(ValueError):
            ChatSession(OpenAIClient("h:1"), max_turns=1)

    def test_the_footer_names_the_model_and_the_time(self):
        line = ChatSession.footer({"model": "qwen2.5-3b", "seconds": 1.234})
        self.assertEqual(line, "[qwen2.5-3b, 1.2s]")
        self.assertEqual(ChatSession.footer({}), "[unknown model, 0.0s]")

    def test_the_banner_states_the_target_and_how_to_leave(self):
        client = OpenAIClient("127.0.0.1:8080", model="m",
                              transport=_fake_transport({
                                  "/v1/models": {"data": [{"id": "m"}]}}))
        banner = ChatSession.banner(client, "llama-server on 8080")
        self.assertIn("m at http://127.0.0.1:8080", banner)
        self.assertIn("llama-server on 8080", banner)
        self.assertIn("/quit", banner)

    def test_help_lists_every_supported_command(self):
        text = ChatSession.help_text()
        for name in COMMANDS:
            self.assertIn(name, text)


if __name__ == "__main__":
    unittest.main()
