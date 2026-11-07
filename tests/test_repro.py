"""Repro mode: triple-run determinism gate for the standing pins.

Transferred idea: ModelDuck determinism lockdown (IDEA-1627 batch-1 +
triple-run) and its --deterministic repro mode (each variant 3x with a
noise-floor report). Every pin seed must replay byte-identical action
sequences 3x; any future nondeterminism (ordering, clock, RNG) fails
loudly instead of hiding in variance notes.
"""

import hashlib
import unittest

from agent import Agent
from models.manifest import canonical

PIN_SEEDS = (
    ("T1_forage", 71),
    ("T2_delayed_match", 3),
    ("T3_navigate", 15),
    ("T3_navigate", 65),
    ("T3_navigate", 74),
    ("T3_navigate", 202),
    ("T3_navigate", 272),
    ("T3_navigate", 307),
    ("T3_navigate", 479),
)


def _fingerprint(trace):
    body = canonical([r["action"] for r in trace])
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


class TestRepro(unittest.TestCase):
    def test_pin_seeds_triple_run_identical(self):
        for task, seed in PIN_SEEDS:
            first = Agent().run_task(task, seed)
            fp = _fingerprint(first)
            steps = len(first)
            reward = sum(r["reward"] for r in first)
            for _ in range(2):
                again = Agent().run_task(task, seed)
                self.assertEqual(len(again), steps, "%s:%d" % (task, seed))
                self.assertEqual(sum(r["reward"] for r in again), reward)
                self.assertEqual(_fingerprint(again), fp,
                                 "%s:%d" % (task, seed))


if __name__ == "__main__":
    unittest.main()
