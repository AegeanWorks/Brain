"""Prompt budgeting: estimate_tokens/pack in the model seam.

Failing-first: build_prompt has no max_tokens argument and the module
has no estimate_tokens/pack/prompt_stats. The budget helper keeps the
first line (task/position/legal), then keeps target/items/obstacles/cue
in order, and drops the trailing visits line first. The default
``max_tokens=None`` must keep the existing prompt byte-identical.
"""

import json
import unittest
from unittest import mock

from models.llamacpp import (LEGAL, LlamaCppBackend, build_prompt,
                             estimate_tokens, pack, prompt_stats)

OBS = {"task": "T3_navigate", "x": 5, "y": 0, "steps": 7,
       "legal": list(LEGAL)}
MANY = {
    "task": "T3_navigate", "x": 5, "y": 0, "steps": 7,
    "legal": list(LEGAL),
    "target": [7, 7],
    "obstacles": [[6, 1]],
    "visits": [[x, y, 1] for y in range(8) for x in range(8)],
}


class _FakeResponse:
    def __init__(self, body):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self._body).encode("utf-8")


class TestPromptBudget(unittest.TestCase):
    def test_uncapped_prompt_exact(self):
        self.assertEqual(
            build_prompt(OBS),
            "Grid task T3_navigate. You are at [5, 0] after 7 steps. "
            "Reply with exactly one action word, nothing else. "
            "Legal actions: up, down, left, right, collect, wait.")

    def test_estimate_tokens_is_ceil_chars_over_four(self):
        self.assertEqual(estimate_tokens(""), 0)
        self.assertEqual(estimate_tokens("a"), 1)
        self.assertEqual(estimate_tokens("abcd"), 1)
        self.assertEqual(estimate_tokens("abcde"), 2)

    def test_pack_keeps_first_line_and_counts_omitted(self):
        kept, omitted, used = pack(["first", "second", "third"], 10)
        self.assertEqual(kept[0], "first")
        self.assertGreaterEqual(omitted, 1)
        self.assertGreater(used, 0)

    def test_budget_caps_trailing_visits(self):
        prompt = build_prompt(MANY, max_tokens=120)
        stats = prompt_stats(MANY, max_tokens=120)
        self.assertLessEqual(estimate_tokens(prompt), 120)
        self.assertIn("OMITTED:1", prompt)
        self.assertIn("Target: [7, 7].", prompt)
        self.assertIn("Obstacles: [[6, 1]].", prompt)
        self.assertNotIn("Visits:", prompt)
        self.assertEqual(stats["omitted"], 1)
        self.assertEqual(stats["lines"], 2)
        self.assertEqual(stats["tokens"], estimate_tokens(prompt))

    def test_small_budget_keeps_target_and_obstacles(self):
        prompt = build_prompt(MANY, max_tokens=60)
        self.assertIn("Target: [7, 7].", prompt)
        self.assertIn("Obstacles: [[6, 1]].", prompt)
        self.assertNotIn("Visits:", prompt)
        self.assertIn("OMITTED:1", prompt)
        self.assertLessEqual(estimate_tokens(prompt), 60)

    def test_default_budget_is_uncapped(self):
        stats = prompt_stats(MANY)
        self.assertEqual(stats["omitted"], 0)
        self.assertEqual(stats["tokens"], estimate_tokens(build_prompt(MANY)))
        self.assertIn("Visits:", build_prompt(MANY))

    def test_llamacpp_backend_applies_prompt_budget(self):
        body = {"choices": [{"message": {"content": "wait"}}]}
        with mock.patch("models.llamacpp.urllib.request.urlopen",
                        return_value=_FakeResponse(body)):
            backend = LlamaCppBackend("server.exe", "model.gguf",
                                      prompt_budget=120)
            action = backend.generate(MANY)
        self.assertEqual(action, "wait")
        self.assertEqual(backend.last_prompt_stats["omitted"], 1)
        self.assertLessEqual(backend.last_prompt_stats["tokens"], 120)
        self.assertIn("OMITTED:1",
                      backend.last_manifest["manifest"]["prompt"])

    def test_invalid_prompt_budget_rejected(self):
        for value in (0, -1, True, 1.5, "120"):
            with self.assertRaises(ValueError):
                LlamaCppBackend("server.exe", "model.gguf",
                                prompt_budget=value)


if __name__ == "__main__":
    unittest.main()
