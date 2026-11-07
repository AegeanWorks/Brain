"""llama.cpp backend: deterministic prompt building and action parsing."""

import unittest

from models.llamacpp import build_prompt, parse_action

OBS = {"task": "T3_navigate", "x": 5, "y": 0, "steps": 7,
       "legal": ["up", "down", "left", "right", "collect", "wait"]}


class TestLlamaCppProtocol(unittest.TestCase):
    def test_build_prompt_deterministic_and_complete(self):
        first = build_prompt(OBS)
        self.assertEqual(first, build_prompt(dict(OBS)))
        for token in ("T3_navigate", "[5, 0]", "up", "down", "left",
                      "right", "collect", "wait"):
            self.assertIn(token, first)

    def test_parse_action_first_legal_token_wins(self):
        self.assertEqual(parse_action(" go RIGHT!"), "right")
        self.assertEqual(parse_action("Collect."), "collect")
        self.assertEqual(parse_action("up then down"), "up")

    def test_parse_action_rejects_garbage(self):
        self.assertIsNone(parse_action("north"))
        self.assertIsNone(parse_action(""))
        self.assertIsNone(parse_action("do a barrel roll"))


if __name__ == "__main__":
    unittest.main()
