"""The front door itself: exit codes, piped parity and readable output.

Every test here patches ``brain.resolve`` with an injected client, so the
CLI is exercised exactly as a person would drive it with no socket open.
"""

import contextlib
import io
import os
import time
import unittest
from unittest import mock

import brain
from models.openai_compat import EndpointUnavailable, OpenAIClient


def _transport(text="pong", model="local"):
    def transport(method, url, payload, timeout):
        if url.endswith("/v1/models"):
            return {"data": [{"id": model}]}
        if url.endswith("/v1/chat/completions"):
            return {"model": model,
                    "choices": [{"message": {"role": "assistant",
                                             "content": text}}]}
        raise AssertionError("unexpected request: %s %s" % (method, url))

    return transport


def _client(text="pong", model="local"):
    return OpenAIClient("127.0.0.1:8080", model=model,
                        transport=_transport(text, model))


class TestRunMode(unittest.TestCase):
    def test_a_real_transcript_is_printed_and_the_run_succeeds(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = brain.main(["run", "T3_navigate", "--seed", "15"])
        text = output.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("task T3_navigate, seed 15", text)
        self.assertIn("done (steps=13 reward=1.0)", text)

    def test_a_collection_is_marked_in_the_transcript(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            brain.main(["run", "T1_forage", "--seed", "0"])
        self.assertIn("reward 1.0", output.getvalue())

    def test_an_unknown_task_is_misuse(self):
        with self.assertRaises(SystemExit) as caught:
            with contextlib.redirect_stderr(io.StringIO()):
                brain.main(["run", "T9_nope"])
        self.assertEqual(caught.exception.code, 2)


class TestDoctor(unittest.TestCase):
    def test_a_missing_model_is_reported_and_exits_one(self):
        output = io.StringIO()
        with mock.patch.object(brain, "resolve",
                               side_effect=EndpointUnavailable("no server")):
            with contextlib.redirect_stdout(output):
                code = brain.main(["doctor"])
        self.assertEqual(code, 1)
        self.assertIn("Brain doctor", output.getvalue())
        self.assertIn("NOT AVAILABLE", output.getvalue())

    def test_a_live_model_is_described(self):
        output = io.StringIO()
        with mock.patch.object(brain, "resolve",
                               return_value=(_client(), "test source")):
            with contextlib.redirect_stdout(output):
                code = brain.main(["doctor"])
        text = output.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("model access: ok", text)
        self.assertIn("local", text)
        self.assertIn("test source", text)

    def test_a_failing_probe_message_is_reported(self):
        output = io.StringIO()
        client = _client()
        with mock.patch.object(brain, "resolve",
                               return_value=(client, "test")):
            with mock.patch.object(client, "chat",
                                   side_effect=EndpointUnavailable("Why: down.")):
                with contextlib.redirect_stdout(output):
                    code = brain.main(["doctor", "--say", "hi"])
        self.assertEqual(code, 1)
        self.assertIn("FAILED", output.getvalue())


class TestChatMode(unittest.TestCase):
    def test_piped_lines_are_asked_in_order_without_prompt_noise(self):
        output = io.StringIO()
        stdin = io.StringIO("hello\nthere\n/quit\n")
        with mock.patch.object(brain, "resolve",
                               return_value=(_client(), "test")):
            with mock.patch.object(brain.sys, "stdin", stdin):
                with contextlib.redirect_stdout(output):
                    code = brain.main(["chat"])
        text = output.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("you: hello", text)
        self.assertIn("you: there", text)
        self.assertIn("model: pong", text)
        self.assertNotIn("you: /quit", text)

    def test_one_prompt_answers_and_exits(self):
        output = io.StringIO()
        with mock.patch.object(brain, "resolve",
                               return_value=(_client("42"), "test")):
            with contextlib.redirect_stdout(output):
                code = brain.main(["chat", "--prompt", "meaning?"])
        self.assertEqual(code, 0)
        self.assertIn("you: meaning?", output.getvalue())
        self.assertIn("model: 42", output.getvalue())

    def test_commands_do_not_reach_the_model(self):
        output = io.StringIO()
        stdin = io.StringIO("/help\n/model\n/reset\n/quit\n")
        with mock.patch.object(brain, "resolve",
                               return_value=(_client(), "test")):
            with mock.patch.object(brain.sys, "stdin", stdin):
                with contextlib.redirect_stdout(output):
                    code = brain.main(["chat"])
        text = output.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("/help", text)
        self.assertIn("forgot 0 messages", text)
        self.assertNotIn("model: pong", text)

    def test_a_failed_call_exits_one_without_a_traceback(self):
        class _Broken:
            model = "local"

            def identify(self):
                return "local", "http://127.0.0.1:8080"

            def chat(self, *_args, **_kwargs):
                raise EndpointUnavailable("Why: gone. Fix: start it.")

        with mock.patch.object(brain, "resolve",
                               return_value=(_Broken(), "test")):
            with mock.patch.object(brain.sys, "stdin", io.StringIO("hi\n")):
                with contextlib.redirect_stdout(io.StringIO()):
                    with contextlib.redirect_stderr(io.StringIO()):
                        code = brain.main(["chat"])
        self.assertEqual(code, 1)

    def test_an_unreachable_model_exits_one_before_any_prompt(self):
        with mock.patch.object(brain, "resolve",
                               side_effect=EndpointUnavailable("No local model")):
            with contextlib.redirect_stdout(io.StringIO()):
                with contextlib.redirect_stderr(io.StringIO()):
                    code = brain.main(["chat"])
        self.assertEqual(code, 1)


class TestStartup(unittest.TestCase):
    def test_help_is_fast_and_lists_the_modes(self):
        output = io.StringIO()
        started = time.time()
        with self.assertRaises(SystemExit) as caught:
            with contextlib.redirect_stdout(output):
                brain.main(["--help"])
        self.assertEqual(caught.exception.code, 0)
        self.assertLess(time.time() - started, 1.0)
        text = output.getvalue()
        for mode in ("chat", "doctor", "run"):
            self.assertIn(mode, text)

    def test_the_module_documents_the_model_fallbacks(self):
        path = os.path.join(os.path.dirname(brain.__file__), "brain.py")
        with open(path, encoding="utf-8") as handle:
            self.assertIn("BRAIN_ENDPOINT", handle.read())


class TestConsoleSafety(unittest.TestCase):
    """Windows consoles are often cp1254/cp437; a smart dash shows as '?'.

    This was a real defect seen on a live run: the banner printed
    "Brain chat ?" because an em dash could not be encoded. Runtime text is
    now plain ASCII, and this test keeps it that way.
    """

    def _rendered_texts(self):
        from chat_session import ChatSession
        from models.openai_compat import describe_available
        client = _client()
        return [
            ChatSession.banner(client, "test"),
            ChatSession.help_text(),
            ChatSession.footer({"model": "m", "seconds": 1.0}),
            describe_available(),
        ]

    def test_every_rendered_string_fits_a_legacy_console(self):
        for text in self._rendered_texts():
            text.encode("cp1254")

    def test_the_runtime_modules_hold_no_non_ascii_literals(self):
        import ast
        for name in ("brain.py", "chat_session.py", "models/openai_compat.py"):
            path = os.path.join(os.path.dirname(brain.__file__),
                                *name.split("/"))
            with open(path, encoding="utf-8") as handle:
                tree = ast.parse(handle.read())
            docstrings = {id(node.body[0].value) for node in ast.walk(tree)
                          if isinstance(node, (ast.Module, ast.FunctionDef,
                                               ast.ClassDef))
                          and node.body and isinstance(node.body[0], ast.Expr)
                          and isinstance(node.body[0].value, ast.Constant)}
            for node in ast.walk(tree):
                if not isinstance(node, ast.Constant):
                    continue
                if not isinstance(node.value, str) or id(node) in docstrings:
                    continue
                self.assertTrue(node.value.isascii(),
                                "%s:%d has non-ASCII text %r"
                                % (name, node.lineno, node.value[:40]))

    def test_doctor_output_is_ascii(self):
        output = io.StringIO()
        with mock.patch.object(brain, "resolve",
                               return_value=(_client(), "test source")):
            with contextlib.redirect_stdout(output):
                brain.main(["doctor"])
        output.getvalue().encode("cp1254")


if __name__ == "__main__":
    unittest.main()
