"""Random-policy floor: rule must beat chance by a margin.

Transferred idea: Crucible random-patch controls (a win must beat the
best of 3 randoms). Three seeded random policies play the 9 pin seeds;
the rule's 89 steps / 11.0 reward must beat the best random by >=10x
fewer steps and >=5 more reward. If the tasks ever become trivially
solvable (or the rule degrades toward chance), this fails loudly.

Thresholds are pre-registered here, not fitted: steps margin x10,
reward margin 5, best-of-3 randoms (seeds 9001-9003, mirroring the
3-random control convention).
"""

import random
import unittest

from agent import Agent, Planner
from models.backend import ModelBackend

PIN_SEEDS = (
    ("T1_forage", 71, 16, 3.0),
    ("T2_delayed_match", 3, 8, 1.0),
    ("T3_navigate", 15, 13, 1.0),
    ("T3_navigate", 65, 6, 1.0),
    ("T3_navigate", 74, 9, 1.0),
    ("T3_navigate", 202, 7, 1.0),
    ("T3_navigate", 272, 14, 1.0),
    ("T3_navigate", 307, 6, 1.0),
    ("T3_navigate", 479, 10, 1.0),
)

RANDOM_SEEDS = (9001, 9002, 9003)
STEP_MARGIN = 10
REWARD_MARGIN = 5.0


class RandomBackend(ModelBackend):
    """Uniform choice among legal actions, seeded for determinism."""

    def __init__(self, seed):
        self.rng = random.Random(seed)

    def generate(self, observation):
        return self.rng.choice(list(observation.get("legal", ["wait"])))


def _run(task, seed, backend):
    # Raw floor: disable the stall-trust gate so this control measures
    # the backend alone, not the planner's safety fallback.
    return Agent(planner=Planner(backend=backend, trust_window=None)).run_task(task, seed)


class TestRandomFloor(unittest.TestCase):
    def test_rule_beats_best_of_three_randoms(self):
        rule_steps = 0
        rule_reward = 0.0
        for task, seed, want_steps, want_reward in PIN_SEEDS:
            trace = Agent().run_task(task, seed)
            self.assertEqual(len(trace), want_steps, "%s:%d" % (task, seed))
            self.assertEqual(sum(r["reward"] for r in trace), want_reward)
            rule_steps += len(trace)
            rule_reward += sum(r["reward"] for r in trace)
        best_steps = None
        best_reward = None
        for rs in RANDOM_SEEDS:
            total = 0
            reward = 0.0
            for task, seed, _, _ in PIN_SEEDS:
                trace = _run(task, seed, RandomBackend(rs * 100000 + seed))
                self.assertTrue(trace[-1]["done"])
                total += len(trace)
                reward += sum(r["reward"] for r in trace)
            if best_steps is None or total < best_steps:
                best_steps = total
            if best_reward is None or reward > best_reward:
                best_reward = reward
        self.assertLessEqual(rule_steps * STEP_MARGIN, best_steps)
        self.assertGreaterEqual(rule_reward - best_reward, REWARD_MARGIN)

    def test_random_backend_deterministic(self):
        first = _run("T3_navigate", 15, RandomBackend(42))
        again = _run("T3_navigate", 15, RandomBackend(42))
        self.assertEqual([r["action"] for r in first],
                         [r["action"] for r in again])


if __name__ == "__main__":
    unittest.main()
