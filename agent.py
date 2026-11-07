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
import hashlib
import itertools
import json

SIZE = 8

_LEGAL_ACTIONS = ("up", "down", "left", "right", "collect", "wait")

PLANNER_POLICY = {
    "name": "grid-rule/planner",
    "viability": "leaf",
    "corridor_avoidance": True,
    "visits_tiebreak": True,
    "recall": "full-history+goal",
    "detour_pooling": "visits",
    "pool_corridor": ">=2",
}


def _canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True)


def policy_digest(policy=None):
    """SHA-256 over the canonical declared planner configuration.

    Binds a run header to the policy that produced it (Assay +
    research-engine 3b evidence binding, adapted: declared config
    instead of code bytes, so behavior-preserving refactors do not
    invalidate evidence while any policy change does).
    """
    body = _canonical_json(dict(policy) if policy is not None else dict(PLANNER_POLICY))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def model_label(backend):
    """Stable model label for run headers: 'rule' with no backend."""
    if backend is None:
        return "rule"
    path = getattr(backend, "model_path", None)
    if path:
        return str(path).replace("\\", "/").split("/")[-1]
    return type(backend).__name__


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


def _first_of_best_tour(pos, cells):
    """First cell of the shortest Manhattan tour from pos through cells.

    Exhaustive over permutations in deterministic order (cells sorted,
    first strictly-shortest tour wins ties). Forage tasks present 3 items.
    """
    uniq = sorted({(c[0], c[1]) for c in cells})
    best = None
    best_len = None
    for perm in itertools.permutations(uniq):
        total = abs(perm[0][0] - pos[0]) + abs(perm[0][1] - pos[1])
        for a, b in zip(perm, perm[1:]):
            total += abs(a[0] - b[0]) + abs(a[1] - b[1])
        if best_len is None or total < best_len:
            best_len = total
            best = perm
    first = best[0]
    return [first[0], first[1]]


def _enters_blocked_corridor(nxt, goal, obstacles):
    """True when stepping onto the goal's column/row while an obstacle
    still lies between that cell and the goal: entering now forces a
    later exit and re-entry (+2). Past-the-block entries (nothing
    between) return False and stay preferred. Pure function of its
    inputs; extracted to module level so tests can disable it as an
    executable negative control (research-engine EVID-008/009)."""
    try:
        gx, gy = int(goal[0]), int(goal[1])
        nx, ny = int(nxt[0]), int(nxt[1])
    except (TypeError, ValueError, IndexError):
        return False
    for ob in (obstacles or []):
        try:
            ox, oy = int(ob[0]), int(ob[1])
        except (TypeError, ValueError, IndexError):
            continue
        if nx == gx and ox == gx and min(ny, gy) < oy < max(ny, gy):
            return True
        if ny == gy and oy == gy and min(nx, gx) < ox < max(nx, gx):
            return True
    return False


def _step_toward(pos, goal, obstacles, visits=None):
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
    counts = visits if isinstance(visits, dict) else {}

    def _free(cell):
        return 0 <= cell[0] < SIZE and 0 <= cell[1] < SIZE and tuple(cell) not in blocked

    def _exits(cell):
        ddx = goal[0] - cell[0]
        ddy = goal[1] - cell[1]
        out = []
        if ddx > 0:
            out.append([cell[0] + 1, cell[1]])
        elif ddx < 0:
            out.append([cell[0] - 1, cell[1]])
        if ddy > 0:
            out.append([cell[0], cell[1] + 1])
        elif ddy < 0:
            out.append([cell[0], cell[1] - 1])
        return out

    def _has_exit(cell):
        # Viability is a one-step check: a candidate cell is viable when
        # stepping onto it leaves a free distance-reducing exit (or it is
        # the goal). Deeper chains were proven dead weight: depth-1, -2
        # and -4 produce byte-identical action sequences on all 3906
        # T3 configs, because corridor avoidance plus visits ordering
        # already determine every decision.
        if list(cell) == list(goal):
            return True
        return any(_free(e) for e in _exits(cell))

    free_ordered = [(name, nxt) for name, nxt in ordered if _free(nxt)]
    # Prefer viable exits, then least-visited cells; the x-first axis order
    # survives inside each group because the sort is stable.
    viable = [pair for pair in free_ordered if _has_exit(pair[1])]
    dead = [pair for pair in free_ordered if not _has_exit(pair[1])]

    def _enters_blocked(nxt):
        return _enters_blocked_corridor(nxt, goal, obstacles)

    for group in (viable, dead):
        group.sort(key=lambda pair: (_enters_blocked(pair[1]),
                                      counts.get((pair[1][0], pair[1][1]), 0)))
    backup = []
    for name, delta in (("up", [0, -1]), ("down", [0, 1]), ("left", [-1, 0]), ("right", [1, 0])):
        nxt = [pos[0] + delta[0], pos[1] + delta[1]]
        if _free(nxt):
            backup.append((name, nxt))
    backup.sort(key=lambda pair: counts.get((pair[1][0], pair[1][1]), 0))
    if not obstacles:
        for name, _nxt in viable + dead:
            return name
        for name, _nxt in backup:
            return name
        return "wait"
    # Obstacle navigation pools viable goal steps with backup detours by
    # least-visited; dead goal steps stay last. Open-field forage keeps
    # the proven viable-first order (T1 39711/39711 optimal); the pool
    # fixes multi-blocker truncations while single-obstacle exhaustive
    # stays 3906/3906 optimal and seed-74 blind truncation is preserved.
    # Two-or-more blockers also weigh blocked-corridor entry after visits;
    # single blockers stay visits-only so corridor alone cannot solve a
    # trap without memory (seed-74 coupling). (5,0) is the honest
    # exception: corridor+pool suffices there without visits, like the
    # single-obstacle seeds 15/65 where lookahead suffices.
    pool = viable + backup
    seen = set()
    uniq = []
    for name, cell in pool:
        key = (cell[0], cell[1])
        if key not in seen:
            seen.add(key)
            uniq.append((name, cell))
    if len(obstacles or []) >= 2:
        uniq.sort(key=lambda pair: (counts.get((pair[1][0], pair[1][1]), 0),
                                    _enters_blocked(pair[1])))
    else:
        uniq.sort(key=lambda pair: counts.get((pair[1][0], pair[1][1]), 0))
    for name, _nxt in uniq + dead:
        return name
    return "wait"


class Planner:
    """Fixed rule-based policy over the state dict.

    An optional ModelBackend proposes the action first; any missing,
    invalid, or raising proposal falls back to the rule policy and is
    counted in fallbacks. With backend None the rule path is exact.
    """

    def __init__(self, backend=None):
        self._get_hub = None
        self.backend = backend
        self.fallbacks = 0

    def bind_hub(self, getter):
        self._get_hub = getter

    def read_hub(self):
        if self._get_hub is None:
            return {}
        return self._get_hub()

    def plan(self, state, memories=None):
        hub = self.read_hub()
        try:
            collected = list(hub.get("collected_positions", [])) if hub else []
        except Exception:
            collected = []
        recent = list(memories)[-4:] if memories else []
        positions = []
        for m in recent:
            if isinstance(m, dict) and "x" in m and "y" in m:
                positions.append((m["x"], m["y"]))
        x, y = state["x"], state["y"]
        pos = [x, y]
        visits = {}
        for px, py in positions:
            visits[(px, py)] = visits.get((px, py), 0) + 1
        steps = state.get("steps", 0)
        mem_list = list(memories) if memories else []

        def _recall(key):
            if state.get(key) is not None:
                return state.get(key)
            for m in reversed(mem_list):
                if isinstance(m, dict) and m.get(key) is not None:
                    return m.get(key)
            return None

        if state.get("obstacles") is not None:
            obstacles = list(state.get("obstacles", []))
        else:
            recalled_ob = _recall("obstacles")
            obstacles = list(recalled_ob) if recalled_ob is not None else []
        if "obstacle" in state and state["obstacle"] not in obstacles:
            obstacles.append(state["obstacle"])

        def _toward(goal):
            return _step_toward(pos, goal, obstacles, visits)

        remaining = state.get("items_positions")
        if remaining is None:
            remaining = _recall("items_positions")
        if remaining is not None and collected:
            try:
                done_set = set()
                for c in collected:
                    done_set.add((int(c[0]), int(c[1])))
                remaining = [c for c in list(remaining)
                             if (int(c[0]), int(c[1])) not in done_set]
            except Exception:
                remaining = list(remaining)
        recalled_target = _recall("target")
        if "cue" in state:
            cue_val = state.get("cue")
        else:
            cue_val = _recall("cue")
        if self.backend is not None:
            obs = {"task": state.get("task"), "x": x, "y": y,
                   "steps": steps, "legal": list(_LEGAL_ACTIONS)}
            if recalled_target is not None:
                obs["target"] = list(recalled_target)
            if remaining is not None:
                obs["items_positions"] = [list(c) for c in remaining]
            if obstacles is not None:
                obs["obstacles"] = [list(c) for c in obstacles]
            if cue_val is not None or "cue" in state or any(
                    isinstance(m, dict) and "cue" in m for m in mem_list):
                if cue_val is not None:
                    obs["cue"] = cue_val
            if visits:
                obs["visits"] = [[int(px), int(py), int(visits[(px, py)])]
                                 for (px, py) in sorted(visits)]
            try:
                proposed = self.backend.generate(obs)
            except Exception:
                proposed = None
            if isinstance(proposed, str) and proposed in _LEGAL_ACTIONS:
                return proposed
            self.fallbacks += 1
        if remaining:
            if pos in [list(c) for c in remaining]:
                return "collect"
            goal = _first_of_best_tour(pos, [list(c) for c in remaining])
            return _toward(goal)

        target = recalled_target
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

    Persistent outcome accounting: each loop step records cost 1.0 into
    self_model with ok True only when that step's reward is positive
    (reward > 0.0); unrewarded steps record ok False. Snapshot error_rate
    is therefore the fraction of unrewarded steps, and S vectors carry
    reward-timing variance. Failures inside persistent updates never raise:
    each is counted in substrate_errors() by module key and the loop
    continues. substrate_errors() returns all-zero counts on clean runs.

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
        self._substrate_errors = {
            "bind": 0,
            "memory_store": 0,
            "planner_tracker": 0,
            "self_model": 0,
            "telemetry_log": 0,
            "verdict": 0,
        }
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
                    self._substrate_errors["bind"] += 1

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
            memories = self.memory.recall(limit=None)  # recall for planner
            action = self.planner.plan(state, memories)  # plan
            new_state, reward, done = self.world.step(action)  # act
            self.telemetry.log({"step": i, "action": action, "reward": reward, "done": done})
            self.selfmodel.record(new_state, action, reward, done)
            self.hub_write({"last_step": i, "last_action": action, "last_reward": reward})
            if action == "collect" and float(reward) > 0.0:
                try:
                    cur = self.get_hub().get("collected_positions", [])
                    nxt = list(cur) + [[int(new_state.get("x", 0)), int(new_state.get("y", 0))]]
                    seen = set()
                    uniq = []
                    for c in nxt:
                        key = (int(c[0]), int(c[1]))
                        if key not in seen:
                            seen.add(key)
                            uniq.append([int(key[0]), int(key[1])])
                    self.hub_write({"collected_positions": uniq})
                except Exception:
                    self._substrate_errors["bind"] += 1
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
                    self._substrate_errors["memory_store"] += 1
            if self.planner_tracker is not None:
                try:
                    nxt = self.planner_tracker.next()
                    if nxt is not None:
                        self.planner_tracker.mark_ok()
                except Exception:
                    self._substrate_errors["planner_tracker"] += 1
            if self.self_model is not None:
                try:
                    _conf_sm = 1.0 if float(reward) > 0.0 else 0.5
                    _ok_sm = float(reward) > 0.0
                    self.self_model.record(1.0, _ok_sm, _conf_sm)
                except Exception:
                    self._substrate_errors["self_model"] += 1
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
                    self._substrate_errors["telemetry_log"] += 1
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
        self.telemetry_log.write_header(task_id, max_steps,
                                          policy=PLANNER_POLICY["name"],
                                          policy_sha256=policy_digest(),
                                          model=model_label(self.planner.backend))
        from worlds.grid import GridWorld

        self.world = GridWorld(task_id, seed)
        self._reset_episode()
        trace = self.run(max_steps=max_steps)
        verdict = "done" if (trace and trace[-1].get("done")) else "truncated"
        reason = "steps=%d" % len(trace)
        try:
            self.telemetry_log.write_verdict(verdict, reason)
        except Exception:
            self._substrate_errors["verdict"] += 1
        return trace

    def substrate_errors(self):
        """Return a copy of per-module persistent-substrate failure counts."""
        return dict(self._substrate_errors)
