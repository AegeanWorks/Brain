"""A grid task where the shortest tour is the wrong plan.

Every shipped task rewards reaching cells, so a shortest-tour rule is
already optimal (ADR-192: gap 0 on 20/20 seeds). This world adds the
missing ingredient: each item has a deadline, and an item that is not
collected by its deadline disappears.

Under deadlines, order matters and distance does not decide the order. A
plan that walks the shortest tour can miss an early item and finish with
fewer collections than a plan that visits by deadline. That makes the
task the first one where a better-than-rule policy can actually win, which
is the precondition ADR-192 set for measuring a learned policy.

Deterministic from the seed; state keys match the grid worlds so the
existing planner and backend seam drive it unchanged.
"""

import hashlib
import json
import random

SIZE = 8
MAX_STEPS = 200
MAX_ENERGY = 200
ITEMS = 4


class DeadlineWorld:
    """Collect items before they expire; the rule's tour ignores deadlines."""

    task_id = "T6_deadline"
    ACTIONS = ("up", "down", "left", "right", "collect", "wait")

    def __init__(self, seed, items=ITEMS):
        if not isinstance(seed, int):
            raise TypeError("seed must be int")
        if not isinstance(items, int) or items < 2:
            raise ValueError(
                "Why: items must be an int >= 2 so ordering can matter. "
                "Fix: pass items=4.")
        self.seed = seed
        self.item_count = items
        self.reset()

    # -- layout ----------------------------------------------------------

    def _build(self):
        rng = random.Random(self.seed)
        pool = [[x, y] for y in range(SIZE) for x in range(SIZE)
                if [x, y] != [0, 0]]
        picked = rng.sample(pool, self.item_count)
        picked.sort(key=lambda cell: (abs(cell[0]) + abs(cell[1]),
                                      cell[0], cell[1]))
        # The farthest item is due at the moment a direct approach reaches
        # it; every other item is patient. A shortest tour therefore spends
        # its early steps on patient items and arrives at the urgent one
        # after it expired, while a deadline-aware plan goes there first.
        # Measured over seeds 0-19: the rule loses exactly one item on 20 of
        # 20 seeds, so this task has headroom by construction.
        deadlines = []
        last = len(picked) - 1
        for index, cell in enumerate(picked):
            distance = abs(cell[0]) + abs(cell[1])
            deadlines.append(distance + (1 if index == last else 40))
        self.items = [{"cell": cell, "deadline": deadlines[index],
                       "collected": False, "expired": False}
                      for index, cell in enumerate(picked)]

    def reset(self):
        self._build()
        self.x, self.y = 0, 0
        self.steps = 0
        self.energy = MAX_ENERGY
        self.collected = 0
        self._done = False
        return self._state()

    def _remaining(self):
        return [list(item["cell"]) for item in self.items
                if not item["collected"] and not item["expired"]]

    def _state(self):
        live = [item for item in self.items
                if not item["collected"] and not item["expired"]]
        # No "target" or "obstacles" key: this task is forage-shaped, and the
        # planner treats a missing target as "no fixed goal" exactly as it
        # does for T1_forage.
        return {
            "x": self.x,
            "y": self.y,
            "energy": self.energy,
            "items": self.collected,
            "steps": self.steps,
            "task": self.task_id,
            "items_positions": [list(item["cell"]) for item in live],
            "deadlines": {self._key(item["cell"]): item["deadline"]
                          for item in live},
        }

    @staticmethod
    def _key(cell):
        return "%d,%d" % (cell[0], cell[1])

    def layout_fingerprint(self):
        payload = json.dumps({"task": self.task_id, "items": self.items},
                             sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def is_viable(self):
        return self.energy > 0 and self.steps < MAX_STEPS

    # -- step ------------------------------------------------------------

    def _expire(self):
        for item in self.items:
            if (not item["collected"] and not item["expired"]
                    and self.steps > item["deadline"]):
                item["expired"] = True

    def step(self, action):
        if action not in self.ACTIONS:
            raise ValueError(
                "Why: unknown action %r. Fix: use one of %s."
                % (action, ", ".join(self.ACTIONS)))
        if self._done:
            return self._state(), 0.0, True

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
            self.x, self.y = nx, ny

        self.steps += 1
        self.energy -= 1
        reward = 0.0
        if action == "collect":
            for item in self.items:
                if item["collected"] or item["expired"]:
                    continue
                if item["cell"] == [self.x, self.y]:
                    # A deadline is inclusive: the collect may land on the
                    # deadline step, but not after it. Expiry is applied
                    # after the action, so this check is the authority.
                    if self.steps <= item["deadline"]:
                        item["collected"] = True
                        self.collected += 1
                        reward = 1.0
                    break

        self._expire()
        done = (self.collected == self.item_count
                or self.energy <= 0 or self.steps >= MAX_STEPS)
        self._done = done
        return self._state(), reward, done
