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

    def __init__(self, seed, latents=None):
        if not isinstance(seed, int):
            raise TypeError("seed must be int")
        self.seed = seed
        self.i = 0
        self._pinned = None
        if latents is not None:
            pairs = []
            for pair in latents:
                if len(pair) != 2:
                    raise ValueError(
                        "Why: each latent pair must have two values. "
                        "Fix: pass [(a, b), ...].")
                pairs.append((int(pair[0]), int(pair[1])))
            if not pairs:
                raise ValueError(
                    "Why: pinned latents must not be empty. "
                    "Fix: pass one (a, b) pair per phase.")
            self._pinned = pairs
        self._build()

    def _build(self):
        if self._pinned is not None:
            self.latents = list(self._pinned)
            return
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


class ChoiceDualWorld(DualWorld):
    """The correct action is the XOR of the two latents.

    Same latents and pre-action context as ``DualWorld``, but here the
    agent can *act* on the pair: ``right`` is rewarded when ``a ^ b == 1``
    and ``left`` when ``a ^ b == 0``. Every other action scores 0.0, so the
    reward is not reachable without reading both latents, and the base rate
    of a blind policy is 0.5.
    """

    task_id = "T5_choice"
    ACTIONS = ("left", "right")

    def _state(self):
        state = super()._state()
        state["context"] = [state["a"], state["b"]]
        return state

    def correct_action(self):
        """Return the rewarded action for the current phase."""
        a, b = self.latents[self._phase()]
        return "right" if (a ^ b) else "left"

    def step(self, action):
        if self.i >= PHASES:
            return self._state(), 0.0, True
        reward = 1.0 if action == self.correct_action() else 0.0
        self.i += 1
        return self._state(), reward, self.i >= PHASES
