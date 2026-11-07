"""Rule-based agent loop over GridWorld state dicts.

No learned model and no network calls. The planner is a fixed
Manhattan-greedy policy that reads only the state dict.

Loop per step in Agent.run:
  perceive: copy state into Memory.save
  plan: Planner.plan(state, Memory.recall())
  act: GridWorld.step(action)
  observe: Telemetry.log + SelfModel.record + hub_write

Hub: Agent owns a dict. hub_write(content) merges a dict into it.
get_hub() returns a copy. Modules may hold a getter installed by the
agent (bind_hub) so all modules can read the same hub mapping.
"""

import copy

SIZE = 8


class Memory:
    """Ordered store of observed state dicts."""

    def __init__(self):
        self._items = []
        self._get_hub = None

    def bind_hub(self, getter):
        self._get_hub = getter

    def read_hub(self):
        if self._get_hub is None:
            return {}
        return self._get_hub()

    def save(self, state):
        self._items.append(copy.deepcopy(state))
        return len(self._items)

    def recall(self, limit=5):
        if limit is None:
            return copy.deepcopy(self._items)
        return copy.deepcopy(self._items[-limit:])

    def clear(self):
        self._items = []

    def __len__(self):
        return len(self._items)


def _nearest(pos, cells):
    best = None
    best_d = None
    for c in cells:
        d = abs(c[0] - pos[0]) + abs(c[1] - pos[1])
        if best_d is None or d < best_d:
            best_d = d
            best = c
    return best


def _step_toward(pos, goal, obstacles):
    dx = goal[0] - pos[0]
    dy = goal[1] - pos[1]
    ordered = []
    # Deterministic axis order: x first, then y.
    if dx > 0:
        ordered.append(("right", [pos[0] + 1, pos[1]]))
    elif dx < 0:
        ordered.append(("left", [pos[0] - 1, pos[1]]))
    if dy > 0:
        ordered.append(("down", [pos[0], pos[1] + 1]))
    elif dy < 0:
        ordered.append(("up", [pos[0], pos[1] - 1]))
    blocked = {tuple(o) for o in (obstacles or [])}
    for name, nxt in ordered:
        if 0 <= nxt[0] < SIZE and 0 <= nxt[1] < SIZE and tuple(nxt) not in blocked:
            return name
    for name, delta in (("up", [0, -1]), ("down", [0, 1]), ("left", [-1, 0]), ("right", [1, 0])):
        nxt = [pos[0] + delta[0], pos[1] + delta[1]]
        if 0 <= nxt[0] < SIZE and 0 <= nxt[1] < SIZE and tuple(nxt) not in blocked:
            return name
    return "wait"


class Planner:
    """Fixed rule-based policy over the state dict."""

    def __init__(self):
        self._get_hub = None

    def bind_hub(self, getter):
        self._get_hub = getter

    def read_hub(self):
        if self._get_hub is None:
            return {}
        return self._get_hub()

    def plan(self, state, memories=None):
        _ = memories
        x, y = state["x"], state["y"]
        pos = [x, y]
        steps = state.get("steps", 0)
        obstacles = list(state.get("obstacles", []))
        if "obstacle" in state and state["obstacle"] not in obstacles:
            obstacles.append(state["obstacle"])

        remaining = state.get("items_positions")
        if remaining:
            if pos in [list(c) for c in remaining]:
                return "collect"
            goal = _nearest(pos, [list(c) for c in remaining])
            return _step_toward(pos, goal, obstacles)

        target = state.get("target")
        if target is not None:
            target = list(target)
            if pos == target:
                if state.get("task") == "T2_delayed_match" and steps < 2:
                    return "wait"
                return "collect"
            return _step_toward(pos, target, obstacles)

        return "wait"


class SelfModel:
    """Record of (state, action, reward, done) transitions."""

    def __init__(self):
        self._history = []
        self._get_hub = None

    def bind_hub(self, getter):
        self._get_hub = getter

    def read_hub(self):
        if self._get_hub is None:
            return {}
        return self._get_hub()

    def record(self, state, action, reward, done):
        self._history.append(
            {"state": copy.deepcopy(state), "action": action, "reward": reward, "done": done}
        )
        return len(self._history)

    def history(self):
        return copy.deepcopy(self._history)

    def clear(self):
        self._history = []


class Telemetry:
    """Append-only log of step events."""

    def __init__(self):
        self._events = []
        self._get_hub = None

    def bind_hub(self, getter):
        self._get_hub = getter

    def read_hub(self):
        if self._get_hub is None:
            return {}
        return self._get_hub()

    def log(self, event):
        self._events.append(copy.deepcopy(dict(event)))
        return len(self._events)

    def events(self):
        return copy.deepcopy(self._events)

    def clear(self):
        self._events = []


class Agent:
    """Closed loop over a GridWorld instance.

    Args:
        memory: Memory instance or None (a default is created).
        planner: Planner instance or None.
        selfmodel: SelfModel instance or None.
        telemetry: Telemetry instance or None.
        world: GridWorld instance or None. run_task builds one when
            a task_id/seed pair is given.
    """

    def __init__(self, memory=None, planner=None, selfmodel=None, telemetry=None, world=None):
        self.memory = memory if memory is not None else Memory()
        self.planner = planner if planner is not None else Planner()
        self.selfmodel = selfmodel if selfmodel is not None else SelfModel()
        self.telemetry = telemetry if telemetry is not None else Telemetry()
        self.world = world
        self._hub = {}
        for mod in (self.memory, self.planner, self.selfmodel, self.telemetry):
            bind = getattr(mod, "bind_hub", None)
            if callable(bind):
                bind(self.get_hub)

    # -- hub ----------------------------------------------------------

    def hub_write(self, content):
        """Merge a dict into the shared hub and return a hub copy."""
        if not isinstance(content, dict):
            raise TypeError("hub content must be a dict")
        self._hub.update(copy.deepcopy(content))
        return self.get_hub()

    def get_hub(self):
        """Return a copy of the shared hub mapping."""
        return copy.deepcopy(self._hub)

    def _reset_episode(self):
        for mod in (self.memory, self.selfmodel, self.telemetry):
            clear = getattr(mod, "clear", None)
            if callable(clear):
                clear()
        self._hub = {}

    # -- loop ----------------------------------------------------------

    def run(self, max_steps=200):
        """Run perceive/plan/act/observe loop; return trace list."""
        if self.world is None:
            raise ValueError("Agent.world is None; pass a world or use run_task")
        if max_steps <= 0:
            raise ValueError("max_steps must be positive")
        trace = []
        state = self.world.reset()
        for i in range(int(max_steps)):
            self.memory.save(state)  # perceive
            memories = self.memory.recall()  # recall for planner
            action = self.planner.plan(state, memories)  # plan
            new_state, reward, done = self.world.step(action)  # act
            self.telemetry.log({"step": i, "action": action, "reward": reward, "done": done})
            self.selfmodel.record(new_state, action, reward, done)
            self.hub_write({"last_step": i, "last_action": action, "last_reward": reward})
            trace.append(
                {"step": i, "state": copy.deepcopy(new_state), "action": action,
                 "reward": reward, "done": done}
            )
            state = new_state
            if done:
                break
        return trace

    def run_task(self, task_id, seed, max_steps=200):
        """Build GridWorld(task_id, seed) and run the loop."""
        from worlds.grid import GridWorld

        self.world = GridWorld(task_id, seed)
        self._reset_episode()
        return self.run(max_steps=max_steps)
