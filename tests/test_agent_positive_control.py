"""An agent-produced positive control for the signed module scan.

The earlier positive control (ADR-157) was a synthetic JSONL and the
agent-path tests were all negative. This control runs a test-only
``XorWorld``: four states per episode, reward ``x XOR y``, with ``y`` tied
to the visit index (M0) and ``x`` exposed as the planner's alternatives
count (P0). M0 and P0 jointly determine the target, neither marginal does,
so a valid M-P interaction is planted through the real Agent signal path.

Measured: twenty train seeds and twenty holdout seeds, 80 rows each. The
signed holdout selects three positive pairs and rejects none; ``(0,2)``
M-P reads ``syn +0.2722``, ``(1,2)`` ``+0.3352`` and ``(2,5)`` ``+0.3715``,
all stable and replicated. A noise control with a fixed reward at one step
selects nothing, and disabled signals produce no rows.
"""

import random
import unittest

from agent import Agent
from evals.module_state import signals_from_trace
from evals.replication import scan_with_holdout


class _BaseWorld:
    task_id = "C_xor"

    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.xs = [self.rng.randint(0, 1) for _ in range(4)]
        self.i = 0

    def reset(self):
        self.i = 0
        return self._state()

    def _state(self):
        index = min(self.i, 3)
        return {"x": self.xs[index], "y": index % 2, "target": [0, 0],
                "obstacles": [], "items_positions": []}


class XorWorld(_BaseWorld):
    """Reward is x XOR y; y is the visit-index parity."""

    def step(self, action):
        index = self.i
        reward = float(self.xs[index] ^ (index % 2))
        self.i += 1
        return self._state(), reward, self.i >= 4


class NoiseWorld(_BaseWorld):
    """Reward is fixed at one step, independent of x/y."""

    def step(self, action):
        index = self.i
        reward = 1.0 if index == 2 else 0.0
        self.i += 1
        return self._state(), reward, self.i >= 4


class _ProbePlanner:
    """Return a constant action and expose x as the alternatives count."""

    def __init__(self):
        self.last_probe = {}

    def plan(self, state, memories):
        x = int(state.get("x", 0))
        self.last_probe = {
            "state": [], "memory": [], "persistent": [], "store_reads": 0,
            "rule": {"distance": 0, "ties": 1,
                     "alternatives": [{"action": "wait", "visits": 0}]
                     * (x + 1)},
        }
        return "wait"


def _rows(world_class, seeds):
    rows = []
    for seed in seeds:
        agent = Agent(world=world_class(seed), planner=_ProbePlanner())
        rows.extend(signals_from_trace(agent.run(max_steps=4)))
    return rows, [row[-1] for row in rows]


class TestAgentPositiveControl(unittest.TestCase):
    def test_planted_xor_is_selected_and_replicated(self):
        train_rows, train_target = _rows(XorWorld, range(20))
        holdout_rows, holdout_target = _rows(XorWorld, range(20, 40))
        result = scan_with_holdout(train_rows, train_target,
                                   holdout_rows, holdout_target, trials=100)
        selected = [item["candidate"]["columns"]
                    for item in result["selected"]]
        self.assertIn([0, 2], selected)
        self.assertIn([1, 2], selected)
        self.assertIn([2, 5], selected)
        for item in result["selected"]:
            self.assertEqual(item["direction"], "positive")
            self.assertTrue(item["stable"] and item["replicated"])

    def test_noise_control_selects_nothing(self):
        train_rows, train_target = _rows(NoiseWorld, range(20))
        holdout_rows, holdout_target = _rows(NoiseWorld, range(20, 40))
        result = scan_with_holdout(train_rows, train_target,
                                   holdout_rows, holdout_target, trials=100)
        self.assertEqual(result["selected"], [])

    def test_disabled_signals_have_no_rows(self):
        rows = []
        for seed in range(4):
            agent = Agent(world=XorWorld(seed), planner=_ProbePlanner(),
                          module_signals=False)
            rows.extend(signals_from_trace(agent.run(max_steps=4)))
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
