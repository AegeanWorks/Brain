"""A deterministic world whose reward is an interaction of two independent bits.

The three shipped grid tasks expose state that is a function of elapsed
time, so every module signal is collinear with the step index and no pair
can demonstrate an interaction (ADR-142, ADR-148, ADR-149). ``DualWorld``
is the missing substrate: each episode runs four phases, and each phase has
a latent pair ``(a, b)`` drawn from two **independent** random streams.
The reward of a step is ``a XOR b``, so neither latent alone predicts it.

The world also exposes the pair through ``signal_context``: a pre-action,
non-leaky readout the agent copies into its ``signals`` block. That makes
the interaction measurable on real agent traces instead of only in a
test-only world.
"""

import hashlib
import json
import random

PHASES = 4
MAX_ENERGY = 200


class DualWorld:
    """Two independent latents per phase; reward is their XOR."""

    task_id = "T4_dual"

    def __init__(self, seed):
        if not isinstance(seed, int):
            raise TypeError("seed must be int")
        self.seed = seed
        self.i = 0
        self._build()

    def _build(self):
        first = random.Random(self.seed * 2 + 1)
        second = random.Random(self.seed * 2 + 2)
        self.latents = [(first.randrange(2), second.randrange(2))
                        for _ in range(PHASES)]

    def _phase(self):
        return min(self.i, PHASES - 1)

    def _state(self):
        index = self._phase()
        a, b = self.latents[index]
        return {
            "x": 0,
            "y": 0,
            "energy": MAX_ENERGY - self.i,
            "items": 0,
            "steps": self.i,
            "phase": index,
            "a": a,
            "b": b,
            "task": self.task_id,
            "target": [0, 0],
            "obstacles": [],
            "items_positions": [],
        }

    def signal_context(self, state):
        """Return the pre-action latent pair as floats ``[a, b]``."""
        return [float(state.get("a", 0)), float(state.get("b", 0))]

    def layout_fingerprint(self):
        geometry = {"task": self.task_id, "latents": [list(p) for p in self.latents]}
        payload = json.dumps(geometry, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def is_viable(self):
        return self.i < PHASES

    def reset(self):
        self.i = 0
        self._build()
        return self._state()

    def step(self, action):
        if self.i >= PHASES:
            return self._state(), 0.0, True
        a, b = self.latents[self.i]
        reward = float(a ^ b)
        self.i += 1
        return self._state(), reward, self.i >= PHASES


class NoiseDualWorld(DualWorld):
    """Same latents and context, but the reward ignores both of them."""

    task_id = "T4_dual_noise"

    def step(self, action):
        index = self.i
        reward = 1.0 if index == 2 else 0.0
        self.i += 1
        return self._state(), reward, self.i >= PHASES
