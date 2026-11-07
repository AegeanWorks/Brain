"""Deterministic 8x8 grid worlds with fixed-step updates.

Tasks:
  T1_forage: collect 3 items placed by seeded RNG.
  T2_delayed_match: cue in {0, 1} shown in state; match target depends
    on cue ([0, 7] for cue 0, [7, 0] for cue 1); collect on the target
    is rewarded only after at least 2 steps have elapsed.
  T3_navigate: reach a seeded target cell; one seeded obstacle cell
    blocks entry.

State dict base keys: x, y, energy, items, steps. Task extras are part
of the same state dict, so the dict is the only observation channel.
No additional lookup or oracle exists outside the state dict.

Stdlib only. Deterministic via random.Random(seed).
"""

import hashlib
import json
import random

SIZE = 8
MAX_STEPS = 200
MAX_ENERGY = 200

TASKS = ("T1_forage", "T2_delayed_match", "T3_navigate")
ACTIONS = ("up", "down", "left", "right", "collect", "wait")


def stable_hash(state):
    """Return sha256 hex digest of JSON state with sorted keys."""
    payload = json.dumps(state, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def viability(state):
    """Vc viability predicate: energy > 0 and steps < 200."""
    try:
        return state["energy"] > 0 and state["steps"] < MAX_STEPS
    except (KeyError, TypeError):
        return False


def _manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class GridWorld:
    """Deterministic grid world for one task id and seed."""

    def __init__(self, task_id: str, seed: int):
        if task_id not in TASKS:
            raise ValueError("unknown task_id: %r (expected one of %s)" % (task_id, TASKS))
        if not isinstance(seed, int):
            raise TypeError("seed must be int")
        self.task_id = task_id
        self.seed = seed
        self._rng = random.Random(seed)
        self.x = 0
        self.y = 0
        self.energy = MAX_ENERGY
        self.collected = 0
        self.steps = 0
        self._done = False
        self._cue = 0
        self._target = [0, 0]
        self._obstacles = []
        self._initial_items = []
        self._remaining = []
        self._build_layout(self._rng)

    # -- layout ---------------------------------------------------------

    def _all_cells(self):
        return [[x, y] for y in range(SIZE) for x in range(SIZE)]

    def _build_layout(self, rng):
        start = [0, 0]
        if self.task_id == "T1_forage":
            pool = [c for c in self._all_cells() if c != start]
            picked = rng.sample(pool, 3)
            self._initial_items = [list(c) for c in picked]
            self._remaining = [list(c) for c in picked]
            self._target = []
            self._obstacles = []
            self._cue = 0
        elif self.task_id == "T2_delayed_match":
            self._cue = int(rng.randrange(2))
            self._target = [0, 7] if self._cue == 0 else [7, 0]
            self._initial_items = []
            self._remaining = []
            self._obstacles = []
        elif self.task_id == "T3_navigate":
            pool = [c for c in self._all_cells() if c != start]
            target = list(rng.choice(pool))
            rest = [c for c in pool if c != target]
            obstacle = list(rng.choice(rest))
            self._target = target
            self._obstacles = [obstacle]
            self._initial_items = []
            self._remaining = []
            self._cue = 0
        else:  # guarded by __init__, kept for clarity
            raise ValueError("unknown task_id: %r" % (self.task_id,))

    # -- state ----------------------------------------------------------

    def _state(self):
        state = {
            "x": self.x,
            "y": self.y,
            "energy": self.energy,
            "items": self.collected,
            "steps": self.steps,
            "task": self.task_id,
        }
        if self.task_id == "T1_forage":
            state["items_positions"] = [list(c) for c in self._remaining]
        elif self.task_id == "T2_delayed_match":
            state["cue"] = self._cue
            state["target"] = list(self._target)
        elif self.task_id == "T3_navigate":
            state["target"] = list(self._target)
            state["obstacles"] = [list(c) for c in self._obstacles]
        return state

    def is_viable(self):
        """Return True while energy > 0 and steps < 200."""
        return self.energy > 0 and self.steps < MAX_STEPS

    def reset(self):
        """Rebuild layout from seed and return the initial state dict."""
        self._rng = random.Random(self.seed)
        self.x = 0
        self.y = 0
        self.energy = MAX_ENERGY
        self.collected = 0
        self.steps = 0
        self._done = False
        self._build_layout(self._rng)
        return self._state()

    # -- stepping --------------------------------------------------------

    def _blocked(self, nx, ny):
        if self.task_id == "T3_navigate":
            for ob in self._obstacles:
                if nx == ob[0] and ny == ob[1]:
                    return True
        return False

    def step(self, action: str):
        """Apply one fixed-step action.

        Returns (state, reward, done). Movement is clamped to the
        8x8 board. Each call costs 1 energy and 1 step.
        """
        if self._done:
            return self._state(), 0.0, True
        if action not in ACTIONS:
            raise ValueError("unknown action: %r (expected one of %s)" % (action, ACTIONS))

        nx, ny = self.x, self.y
        if action == "up":
            ny = max(0, self.y - 1)
        elif action == "down":
            ny = min(SIZE - 1, self.y + 1)
        elif action == "left":
            nx = max(0, self.x - 1)
        elif action == "right":
            nx = min(SIZE - 1, self.x + 1)

        if action in ("up", "down", "left", "right"):
            if not self._blocked(nx, ny):
                self.x, self.y = nx, ny

        self.steps += 1
        self.energy -= 1

        reward = 0.0
        done = False
        pos = [self.x, self.y]

        if self.task_id == "T1_forage":
            if action == "collect" and pos in self._remaining:
                self._remaining.remove(pos)
                self.collected += 1
                reward = 1.0
                if self.collected >= 3:
                    done = True
        elif self.task_id == "T2_delayed_match":
            if pos == list(self._target) and action == "collect" and self.steps >= 2:
                self.collected = 1
                reward = 1.0
                done = True
        elif self.task_id == "T3_navigate":
            if pos == list(self._target):
                self.collected = 1
                reward = 1.0
                done = True

        if self.energy <= 0 or self.steps >= MAX_STEPS:
            done = True
        self._done = done
        return self._state(), reward, done
