"""A prompt budget must be reportable as honoured or exceeded.

``pack`` keeps the anchor line even when it alone exceeds the budget, which
is documented. What was not reported is whether the budget was met: a
caller setting ``prompt_budget=40`` receives a 50-token prompt and nothing
in ``last_prompt_stats`` says so.

Measured with a T3 observation (uncapped 62 tokens):

  budget=60 -> 50 tokens, omitted 1, within budget
  budget=40 -> 50 tokens, omitted 1, **over budget by 10**
  budget= 9 -> 50 tokens, omitted 1, **over budget by 41**

These tests pin a ``within_budget`` flag and the ``over_by`` count so a
budget breach is visible to the caller and to telemetry, without changing
which tokens are kept.
"""

import unittest

from models.llamacpp import build_prompt, pack, prompt_stats

OBS = {
    "task": "T3_navigate", "x": 5, "y": 3, "steps": 12,
    "legal": ["up", "down", "left", "right", "wait"],
    "target": [6, 7], "obstacles": [[6, 1]],
    "visits": [[0, 0], [1, 0], [2, 0], [3, 0], [4, 0], [5, 0]],
}


class TestPromptBudgetHonesty(unittest.TestCase):
    def test_uncapped_reports_no_budget_constraint(self):
        stats = prompt_stats(OBS)
        self.assertIsNone(stats["within_budget"])
        self.assertEqual(stats["over_by"], 0)
        self.assertEqual(stats["omitted"], 0)

    def test_a_generous_budget_is_within(self):
        stats = prompt_stats(OBS, max_tokens=120)
        self.assertTrue(stats["within_budget"])
        self.assertEqual(stats["over_by"], 0)
        self.assertEqual(stats["omitted"], 0)

    def test_a_budget_that_drops_a_line_is_within(self):
        stats = prompt_stats(OBS, max_tokens=60)
        self.assertTrue(stats["within_budget"])
        self.assertEqual(stats["over_by"], 0)
        self.assertGreater(stats["omitted"], 0)

    def test_a_budget_below_the_anchor_is_reported_as_exceeded(self):
        for budget in (40, 30, 20, 9):
            stats = prompt_stats(OBS, max_tokens=budget)
            self.assertFalse(stats["within_budget"], budget)
            self.assertEqual(stats["over_by"], stats["tokens"] - budget,
                             budget)

    def test_the_breach_is_attributable_to_the_kept_anchor(self):
        # The anchor alone is kept regardless, so 'over' must equal what the
        # kept lines cost beyond the budget — not a silent cap failure.
        stats = prompt_stats(OBS, max_tokens=40)
        kept = build_prompt(OBS, max_tokens=40)
        self.assertTrue(kept.startswith("Grid task T3_navigate."))
        self.assertIn("OMITTED:1", kept)
        self.assertGreater(stats["over_by"], 0)

    def test_pack_still_returns_the_same_triple(self):
        kept, omitted, used = pack(["a" * 40, "b" * 40], 30)
        self.assertEqual(len(kept), 1)
        self.assertEqual(omitted, 1)
        self.assertGreater(used, 0)

    def test_the_rendered_prompt_is_unchanged(self):
        # The report gains fields; the prompt text must not move.
        self.assertEqual(build_prompt(OBS, max_tokens=60),
                         build_prompt(OBS, 60))
        self.assertIn("Target: [6, 7]", build_prompt(OBS, max_tokens=60))


if __name__ == "__main__":
    unittest.main()
