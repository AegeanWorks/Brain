"""Ablation transform checks."""

import unittest

from telemetry.ablate import hub_zero, module_lesion, shuffle_hub


def _trace():
    return [
        {"seq": 1, "M": [1, 2], "P": [3, 4], "S": [5, 6], "hub": [0.5, 1.5, -2.0]},
        {"seq": 2, "M": [7, 8], "P": [9, 10], "S": [11, 12], "hub": [2.5, 3.5, 4.5]},
    ]


class TestAblation(unittest.TestCase):
    def test_hub_zero_kills_hub_content(self):
        trace = _trace()
        out = hub_zero(trace)
        self.assertEqual(len(out), 2)
        for rec in out:
            self.assertEqual(rec["hub"], [0, 0, 0] if rec["hub"] != [0.0, 0.0, 0.0] else rec["hub"])
            self.assertTrue(all(v == 0 for v in rec["hub"]))
        # other columns preserved
        self.assertEqual(out[0]["M"], [1, 2])
        self.assertEqual(out[1]["P"], [9, 10])
        # input not mutated
        self.assertEqual(trace[0]["hub"], [0.5, 1.5, -2.0])

    def test_lesion_isolates(self):
        trace = _trace()
        out = module_lesion(trace, "M")
        self.assertTrue(all(v == 0 for v in out[0]["M"]))
        self.assertTrue(all(v == 0 for v in out[1]["M"]))
        # non-target columns unchanged
        self.assertEqual(out[0]["P"], [3, 4])
        self.assertEqual(out[0]["S"], [5, 6])
        self.assertEqual(out[0]["hub"], [0.5, 1.5, -2.0])
        out_p = module_lesion(trace, "P")
        self.assertTrue(all(v == 0 for v in out_p[0]["P"]))
        self.assertEqual(out_p[0]["M"], [1, 2])
        self.assertEqual(out_p[0]["hub"], [0.5, 1.5, -2.0])
        with self.assertRaises(ValueError):
            module_lesion(trace, "X")

    def test_shuffle_deterministic_and_preserves_multiset(self):
        trace = _trace()
        first = shuffle_hub(trace, 7)
        second = shuffle_hub(trace, 7)
        self.assertEqual(first, second)
        for src, dst in zip(trace, first):
            self.assertEqual(sorted(src["hub"]), sorted(dst["hub"]))
            self.assertEqual(src["M"], dst["M"])
        # input not mutated
        self.assertEqual(trace[0]["hub"], [0.5, 1.5, -2.0])


if __name__ == "__main__":
    unittest.main()
