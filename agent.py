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
        hub = self.read_hub()
        _ = hub.get("last_action") if hub else None
        recent = list(memories)[-4:] if memories else []
        positions = []
        for m in recent:
            if isinstance(m, dict) and "x" in m and "y" in m:
                positions.append((m["x"], m["y"]))
        x, y = state["x"], state["y"]
        pos = [x, y]
        stuck = positions.count((x, y)) >= 2
        steps = state.get("steps", 0)
        obstacles = list(state.get("obstacles", []))
        if "obstacle" in state and state["obstacle"] not in obstacles:
            obstacles.append(state["obstacle"])

        def _toward(goal):
            if stuck:
                dx = goal[0] - pos[0]
                dy = goal[1] - pos[1]
                for name, nxt in (("down", [pos[0], pos[1] + 1]) if dy > 0 else ("up", [pos[0], pos[1] - 1]),) if dy != 0 else ():
                    if 0 <= nxt[0] < SIZE and 0 <= nxt[1] < SIZE and tuple(nxt) not in {tuple(o) for o in obstacles}:
                        return name
            return _step_toward(pos, goal, obstacles)

        remaining = state.get("items_positions")
        if remaining:
            if pos in [list(c) for c in remaining]:
                return "collect"
            goal = _nearest(pos, [list(c) for c in remaining])
            return _toward(goal)

        target = state.get("target")
        if target is not None:
            target = list(target)
            if pos == target:
                if state.get("task") == "T2_delayed_match" and steps < 2:
                    return "wait"
                return "collect"
            return _toward(target)

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
        memory_store: optional persistent store with count() and
            save(key, content, conf). Reads as memory count.
        planner_tracker: optional tracker with state() idx/status
            plus next()/mark_ok(). Reads as planner idx/pending.
        self_model: optional counters with record(cost, ok, conf)
            and snapshot() errors/budget. Reads as S vector.
        telemetry_log: optional file log (telemetry/log.py Telemetry)
            receiving per-step kind "step" action+result records.
    """

    def __init__(self, memory=None, planner=None, selfmodel=None, telemetry=None, world=None,
                 memory_store=None, planner_tracker=None, self_model=None, telemetry_log=None):
        self.memory = memory if memory is not None else Memory()
        self.planner = planner if planner is not None else Planner()
        self.selfmodel = selfmodel if selfmodel is not None else SelfModel()
        self.telemetry = telemetry if telemetry is not None else Telemetry()
        self.world = world
        self.memory_store = memory_store
        self.planner_tracker = planner_tracker
        self.self_model = self_model
        self.telemetry_log = telemetry_log
        self._hub = {}
        for mod in (self.memory, self.planner, self.selfmodel, self.telemetry,
                    self.memory_store, self.planner_tracker, self.self_model,
                    self.telemetry_log):
            if mod is None:
                continue
            bind = getattr(mod, "bind_hub", None)
            if callable(bind):
                try:
                    bind(self.get_hub)
                except Exception:
                    pass

    @property
    def log_path(self):
        """Return file path of telemetry_log when present, else None."""
        tel = getattr(self, "telemetry_log", None)
        p = getattr(tel, "path", None)
        if p is None:
            return None
        try:
            return str(p)
        except Exception:
            return None

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

    def _step_vectors(self, idx, new_state, reward, memories):
        """Build numeric M/P/S/hub vectors for one step.

        M = [memory count, recall hits].
        P = [planner idx, pending count].
        S = [errors, budget].
        hub = [x, y, reward].
        Counts reflect state after persistent updates for this step.
        """
        if self.memory_store is not None:
            try:
                mem_count = int(self.memory_store.count())
            except Exception:
                mem_count = len(self.memory)
        else:
            mem_count = len(self.memory)
        try:
            recall_hits = len(memories) if isinstance(memories, list) else 0
        except Exception:
            recall_hits = 0
        m_vec = [mem_count, recall_hits]
        if self.planner_tracker is not None:
            try:
                st = self.planner_tracker.state()
                p_idx = int(st.get("idx", 0))
                pending = sum(1 for s in st.get("status", []) if s == "pending")
            except Exception:
                p_idx, pending = 0, 0
            p_vec = [p_idx, pending]
        else:
            p_vec = [0, 0]
        if self.self_model is not None:
            try:
                snap = self.self_model.snapshot()
                s_vec = [int(snap.get("errors", 0)), float(snap.get("budget", 0.0))]
            except Exception:
                s_vec = [0, float(idx + 1)]
        else:
            try:
                blen = len(self.selfmodel.history())
            except Exception:
                blen = idx + 1
            s_vec = [0, float(blen)]
        try:
            hx = new_state.get("x", 0)
            hy = new_state.get("y", 0)
        except Exception:
            hx, hy = 0, 0
        hub_vec = [hx, hy, float(reward)]
        return m_vec, p_vec, s_vec, hub_vec

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
            # -- persistent substrate update (stdlib only, deterministic) --
            if self.memory_store is not None:
                try:
                    import json as _json
                    try:
                        _tid = getattr(self.world, "task_id", "task")
                        _seed = getattr(self.world, "seed", 0)
                        _key = "%s:%s:%d" % (_tid, _seed, i)
                    except Exception:
                        _key = "step-%d" % i
                    _content = _json.dumps(new_state, sort_keys=True)
                    _conf = 1.0 if float(reward) > 0.0 else 0.5
                    self.memory_store.save(_key, _content, _conf)
                except Exception:
                    pass
            if self.planner_tracker is not None:
                try:
                    nxt = self.planner_tracker.next()
                    if nxt is not None:
                        self.planner_tracker.mark_ok()
                except Exception:
                    pass
            if self.self_model is not None:
                try:
                    _conf_sm = 1.0 if float(reward) > 0.0 else 0.5
                    self.self_model.record(1.0, True, _conf_sm)
                except Exception:
                    pass
            m_vec, p_vec, s_vec, hub_vec = self._step_vectors(i, new_state, reward, memories)
            if self.telemetry_log is not None:
                args = {
                    "action": action,
                    "reward": float(reward),
                    "done": bool(done),
                    "M": list(m_vec),
                    "P": list(p_vec),
                    "S": list(s_vec),
                    "hub": list(hub_vec),
                }
                try:
                    self.telemetry_log.append_action(
                        i + 1, "step", args,
                        M=list(m_vec), P=list(p_vec), S=list(s_vec), hub=list(hub_vec),
                    )
                    self.telemetry_log.append_result(
                        i + 1, True, action, 1.0,
                        M=list(m_vec), P=list(p_vec), S=list(s_vec), hub=list(hub_vec),
                    )
                except Exception:
                    pass
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

    def run_task_logged(self, task_id, seed, max_steps=200, log_path=None):
        """Run task with header, per-step actions+results, and verdict.

        Writes header (seq 0), one kind "step" action plus one result
        per grid step with numeric M/P/S/hub vectors, then a verdict.
        Returns the in-memory trace list with unchanged shape.
        """
        if log_path is not None:
            from telemetry.log import Telemetry as _FileTelemetry

            self.telemetry_log = _FileTelemetry(log_path)
        if self.telemetry_log is None:
            raise ValueError("telemetry_log or log_path is required")
        self.telemetry_log.write_header(task_id, max_steps)
        from worlds.grid import GridWorld

        self.world = GridWorld(task_id, seed)
        self._reset_episode()
        trace = self.run(max_steps=max_steps)
        verdict = "done" if (trace and trace[-1].get("done")) else "truncated"
        reason = "steps=%d" % len(trace)
        try:
            self.telemetry_log.write_verdict(verdict, reason)
        except Exception:
            pass
        return trace
