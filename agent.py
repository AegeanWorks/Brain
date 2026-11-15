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

SIGNALS_VERSION = 2
import hashlib
import itertools
import json
from collections import deque

from budget import BudgetExceeded, spend, use_budget
from identity import input_digest
from self_model.online import OnlinePredictor, context_feature_key, feature_key
from self_model.prediction import predict_outcome
from workspace import workspace_digest

SIZE = 8
MAX_DEADLINE_ITEMS = 7

_LEGAL_ACTIONS = ("up", "down", "left", "right", "collect", "wait")

# Goal fields each known task actually consumes. Unknown task names keep
# the generic all-field fallback so custom worlds still recover.
_TASK_FIELDS = {
    "T1_forage": ("items_positions",),
    "T2_delayed_match": ("target", "cue"),
    "T3_navigate": ("target", "obstacles"),
    "T6_deadline": ("items_positions", "deadlines"),
}

PLANNER_POLICY = {
    "name": "grid-rule/planner",
    "viability": "leaf",
    "corridor_avoidance": True,
    "visits_tiebreak": True,
    "recall": "full-history+goal",
    "recovery_recall": "persistent-layout",
    "backend_trust": "stall>=20->match-only",
    "backend_noop_guard": "on",
    "backend_progress_guard": "single-target-bfs",
    "backend_progress_skip": "streak>=3->match-only",
    "backend_distrust_skip": "on",
    "model_manifest_probe": "on",
    "detour_pooling": "visits",
    "pool_corridor": ">=2",
    "cycle_escape": "repeat>=2->bfs",
    "dead_pool_filter": "2-blockers:live<=dead-bfs",
    "rule_readout": "bfs-move-ties",
    "deadline_ordering": "max-collected-then-shortest",
}


def _canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True)


def _probe_safe(value):
    """Coerce a recalled value into JSON-safe probe data."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_probe_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _probe_safe(item) for key, item in value.items()}
    return str(value)


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
    """Stable model label for run headers: 'rule' with no backend.

    The label is a *pin*: historical headers are re-verified against it, so
    it must not change when a provider class is renamed. A backend that
    declares ``identity()`` supplies it; the llama.cpp ``model_path``
    fallback is kept so existing headers keep matching.
    """
    if backend is None:
        return "rule"
    identity = getattr(backend, "identity", None)
    if callable(identity):
        declared = identity()
        if (isinstance(declared, str) and declared
                and ":" in declared and not declared.endswith(
                    type(backend).__name__)):
            return declared
    path = getattr(backend, "model_path", None)
    if path:
        return str(path).replace("\\", "/").split("/")[-1]
    return type(backend).__name__


def world_fingerprint(world):
    """Return a world's deterministic layout fingerprint, or None.

    A world that exposes ``layout_fingerprint()`` (built-in and
    subclassed GridWorlds do) is distinguished by its task geometry, so
    persisted layouts keyed by (task, seed) do not collide across
    distinct worlds that reuse the same task id and seed.
    """
    if world is None:
        return None
    method = getattr(world, "layout_fingerprint", None)
    if not callable(method):
        return None
    value = method()
    return value if isinstance(value, str) and value else None


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
        """Return stored states, most recent ``limit`` or all when None.

        Each item is a shallow copy of one stored state dict, so a caller
        may rebind or add keys without touching the store. Copying the
        whole history per call is O(n) and the loop calls this once per
        step, so ``limit=None`` (the loop's read) must not deep-copy: the
        planner reads only the last few entries and never mutates them.
        """
        if limit is None:
            return [dict(item) for item in self._items]
        return [dict(item) for item in self._items[-limit:]]

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


def _tour_audit(pos, cells):
    """Audit first-item ties in the exhaustive shortest item tour.

    Returns the sorted items, the lexicographically first shortest-tour
    first item (the rule's choice), the best/chosen tour lengths, every
    first item that achieves the best length, and whether the choice is
    optimal. Readout only; returns None for unusable input.
    """
    try:
        x, y = int(pos[0]), int(pos[1])
        uniq = sorted({(int(c[0]), int(c[1])) for c in cells})
    except (TypeError, ValueError, IndexError):
        return None
    if not uniq:
        return None
    first_lengths = {}
    best_len = None
    best_first = None
    for perm in itertools.permutations(uniq):
        total = abs(perm[0][0] - x) + abs(perm[0][1] - y)
        for a, b in zip(perm, perm[1:]):
            total += abs(a[0] - b[0]) + abs(a[1] - b[1])
        first = perm[0]
        if first not in first_lengths or total < first_lengths[first]:
            first_lengths[first] = total
        if best_len is None or total < best_len:
            best_len = total
            best_first = first
    chosen_length = first_lengths[best_first]
    tied = sorted([list(first) for first, length in first_lengths.items()
                   if length == best_len])
    return {
        "items": [list(cell) for cell in uniq],
        "chosen": list(best_first),
        "best_length": best_len,
        "chosen_length": chosen_length,
        "tied_firsts": tied,
        "tie_count": len(tied),
        "optimal": chosen_length == best_len,
    }


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


def _bfs_step(pos, goal, obstacles):
    """Return one deterministic BFS step toward ``goal`` and its distance.

    Breadth-first search over the 8x8 board with the static obstacle
    set; neighbor order is the world action order. Returns
    ``(action, distance)`` or ``(None, 0)`` when the goal is unreachable
    or the inputs are malformed. Pure function of its inputs.
    """
    try:
        start = (int(pos[0]), int(pos[1]))
        target = (int(goal[0]), int(goal[1]))
        blocked = {(int(o[0]), int(o[1])) for o in (obstacles or [])}
    except (TypeError, ValueError, IndexError):
        return (None, 0)
    if not (0 <= start[0] < SIZE and 0 <= start[1] < SIZE):
        return (None, 0)
    if start == target:
        return (None, 0)
    order = (("up", 0, -1), ("down", 0, 1),
             ("left", -1, 0), ("right", 1, 0))
    queue = deque([start])
    previous = {start: None}
    while queue:
        cell = queue.popleft()
        if cell == target:
            break
        for _name, dx, dy in order:
            nxt = (cell[0] + dx, cell[1] + dy)
            if not (0 <= nxt[0] < SIZE and 0 <= nxt[1] < SIZE):
                continue
            if nxt in blocked or nxt in previous:
                continue
            previous[nxt] = cell
            queue.append(nxt)
    if target not in previous:
        return (None, 0)
    path = []
    cell = target
    while cell is not None:
        path.append(cell)
        cell = previous[cell]
    path.reverse()
    first = path[1]
    for name, dx, dy in order:
        if (start[0] + dx, start[1] + dy) == first:
            return (name, len(path) - 1)
    return (None, 0)


def _bfs_distance(pos, goal, obstacles):
    """Shortest free-cell BFS distance, or None when unreachable.

    Pure geometry helper for the backend progress guard: a movement that
    strictly increases this distance cannot advance a fixed target.
    """
    try:
        start = (int(pos[0]), int(pos[1]))
        target = (int(goal[0]), int(goal[1]))
        blocked = {(int(o[0]), int(o[1])) for o in (obstacles or [])}
    except (TypeError, ValueError, IndexError):
        return None
    if start == target:
        return 0
    order = (("up", 0, -1), ("down", 0, 1),
             ("left", -1, 0), ("right", 1, 0))
    queue = deque([(start, 0)])
    seen = {start}
    while queue:
        cell, distance = queue.popleft()
        for _name, dx, dy in order:
            nxt = (cell[0] + dx, cell[1] + dy)
            if not (0 <= nxt[0] < SIZE and 0 <= nxt[1] < SIZE):
                continue
            if nxt in blocked or nxt in seen:
                continue
            if nxt == target:
                return distance + 1
            seen.add(nxt)
            queue.append((nxt, distance + 1))
    return None


def _deadline_map(raw):
    """Normalize a world-provided deadline map to ``(x, y) -> deadline``.

    Accepts ``{"x,y": deadline}`` as emitted by ``DeadlineWorld`` or a
    mapping keyed by ``[x, y]`` pairs. Returns ``None`` when any entry is
    malformed, so a partial map can never silently drive a schedule.
    """
    if not isinstance(raw, dict):
        return None
    parsed = {}
    for key, value in raw.items():
        try:
            if isinstance(key, str):
                x_text, y_text = key.split(",", 1)
                x, y = int(x_text), int(y_text)
            elif isinstance(key, (list, tuple)) and len(key) == 2:
                x, y = int(key[0]), int(key[1])
            else:
                return None
            deadline = int(value)
        except (TypeError, ValueError):
            return None
        parsed[(x, y)] = deadline
    return parsed


def _first_of_deadline_tour(pos, cells, deadlines, steps=0, obstacles=None):
    """First cell of the order that collects the most items by deadline.

    Enumerates visit orders (at most ``MAX_DEADLINE_ITEMS``) and scores
    each by ``(-collected, finish_time, path, permutation)``: maximize
    the number of items collected before their inclusive deadlines, then
    finish earliest, then keep the lexicographic order deterministic.
    Travel uses BFS distance, so static obstacles are honored. Returns
    ``([x, y], info)`` for a collectible schedule, ``(None, info)`` when
    the planner must fall back to the shortest tour, or ``(None, None)``
    when the deadline metadata is unusable. Pure function.
    """
    try:
        origin = (int(pos[0]), int(pos[1]))
        uniq = sorted({(int(cell[0]), int(cell[1])) for cell in cells})
        clock = int(steps)
    except (TypeError, ValueError, IndexError):
        return (None, None)
    if not uniq or not isinstance(deadlines, dict):
        return (None, None)
    if any(cell not in deadlines for cell in uniq):
        return (None, None)
    if len(uniq) > MAX_DEADLINE_ITEMS:
        return (None, {"order": "fallback-tour", "reason": "item-limit",
                       "items": len(uniq), "limit": MAX_DEADLINE_ITEMS})
    points = [origin] + uniq
    distances = {}
    for start in points:
        for goal in points:
            distances[(start, goal)] = (
                0 if start == goal else _bfs_distance(start, goal, obstacles))
    best = None
    for order in itertools.permutations(uniq):
        current = origin
        time = clock
        path = []
        for cell in order:
            hop = distances[(current, cell)]
            if hop is None:
                continue
            arrival = time + hop + 1
            if arrival <= deadlines[cell]:
                time = arrival
                path.append(cell)
                current = cell
        if not path:
            continue
        key = (-len(path), time, tuple(path), order)
        if best is None or key < best[0]:
            best = (key, path, time)
    if best is None:
        return (None, {"order": "fallback-tour",
                       "reason": "no-collectible-item",
                       "items": len(uniq), "steps": clock})
    _key, path, finish = best
    chosen = path[0]
    hop = distances[(origin, chosen)]
    arrival = clock + hop + 1
    info = {
        "order": "max-collected-then-shortest",
        "chosen": [chosen[0], chosen[1]],
        "deadline": int(deadlines[chosen]),
        "distance": int(hop),
        "steps": clock,
        "arrival": int(arrival),
        "slack": int(deadlines[chosen] - arrival),
        "collectible": len(path),
        "total": len(uniq),
        "schedule": [[cell[0], cell[1]] for cell in path],
        "skipped": [[cell[0], cell[1]] for cell in uniq
                    if cell not in path],
        "finish": int(finish),
    }
    return ([chosen[0], chosen[1]], info)


def _rule_confidence(pos, goal, obstacles, action, visits=None):
    """Return BFS move-tie facts for one rule action and its goal.

    ``ties`` counts free moves with the minimum post-move BFS distance;
    ``confidence`` is ``1/ties``. ``alternatives`` lists each best move
    with its visit count so the current tie-break can be audited. A
    collect/wait at the goal reads distance 0, confidence 1.0 and no
    alternatives. Pure function; returns None when the goal/geometry is
    unusable. The readout never selects an action.
    """
    if goal is None:
        return None
    try:
        x, y = int(pos[0]), int(pos[1])
        gx, gy = int(goal[0]), int(goal[1])
        blocked = {(int(o[0]), int(o[1])) for o in (obstacles or [])}
    except (TypeError, ValueError, IndexError):
        return None
    if not (0 <= x < SIZE and 0 <= y < SIZE):
        return None
    if not (0 <= gx < SIZE and 0 <= gy < SIZE):
        return None
    counts = visits if isinstance(visits, dict) else {}
    if action not in ("up", "down", "left", "right"):
        current = _bfs_distance([x, y], [gx, gy], obstacles)
        if current is None:
            return None
        return {
            "goal": [gx, gy],
            "distance": current,
            "ties": 1,
            "confidence": 1.0 if current == 0 else 0.0,
            "rule_distance": current,
            "optimal": current == 0,
            "alternatives": [],
        }
    distances = {}
    cells = {}
    for name, dx, dy in (("up", 0, -1), ("down", 0, 1),
                         ("left", -1, 0), ("right", 1, 0)):
        nx, ny = x + dx, y + dy
        if not (0 <= nx < SIZE and 0 <= ny < SIZE):
            continue
        if (nx, ny) in blocked:
            continue
        distance = _bfs_distance([nx, ny], [gx, gy], obstacles)
        if distance is not None:
            distances[name] = distance
            cells[name] = (nx, ny)
    if not distances:
        return None
    best = min(distances.values())
    ties = sum(1 for distance in distances.values() if distance == best)
    rule_distance = distances.get(action)
    if rule_distance is None:
        return None
    alternatives = [
        {"action": name, "distance": distances[name],
         "visits": int(counts.get(cells[name], 0))}
        for name in distances if distances[name] == best
    ]
    return {
        "goal": [gx, gy],
        "distance": best,
        "ties": ties,
        "confidence": round(1.0 / ties, 4),
        "rule_distance": rule_distance,
        "optimal": rule_distance == best,
        "alternatives": alternatives,
    }


def _step_toward(pos, goal, obstacles, visits=None, probe=None,
                 dead_pool_filter=True):
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
    if dead_pool_filter and len(obstacles or []) == 2 and dead:
        dead_cells = {(cell[0], cell[1]) for _name, cell in dead}
        live = []
        best_dead = None
        for pair in uniq:
            key = (pair[1][0], pair[1][1])
            _action, distance = _bfs_step(pair[1], goal, obstacles)
            if distance <= 0:
                distance = 10 ** 6
            if key in dead_cells:
                if best_dead is None or distance < best_dead:
                    best_dead = distance
            else:
                live.append((distance, pair))
        if live:
            best_live = min(item[0] for item in live)
            if best_dead is None or best_live <= best_dead:
                excluded = [pair for pair in uniq
                            if (pair[1][0], pair[1][1]) in dead_cells]
                if isinstance(probe, dict):
                    probe["dead_pool"] = {
                        "position": [int(pos[0]), int(pos[1])],
                        "excluded": [[name, [int(cell[0]), int(cell[1])]]
                                     for name, cell in excluded],
                        "live_distance": int(best_live),
                        "dead_distance": (None if best_dead is None
                                          else int(best_dead)),
                    }
                uniq = [item[1] for item in live]
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
    counted in fallbacks. A legal proposal is trusted until the hub
    reports ``steps_since_reward >= trust_window``; after that stall a
    proposal not matching the rule action is rejected and the backend
    stays match-only for the rest of the episode. Independently, a
    no-op proposal (``wait`` or a premature ``collect``) is rejected
    immediately whenever the rule action is productive. With backend
    None the rule path is exact. ``trust_window=None`` disables the
    stall gate and ``noop_guard=False`` disables the no-op guard so raw
    backend controls can be measured. ``progress_guard=True`` rejects a
    legal free-cell movement that strictly increases the BFS distance to
    a fixed target when no items remain (T2/T3); item tours (T1) and
    no-target states are untouched. ``progress_guard=False`` restores
    the old accept-until-stall behavior. After
    ``progress_skip_after`` consecutive progress rejections the planner
    stops calling the backend for the rest of the episode
    (``skipped-progress``); ``progress_skip_after=None`` keeps calling
    it for the guard-only ablation. ``cycle_escape=False`` disables
    the repeated-position BFS escape so the loop can be measured as an
    executable ablation. Once the backend is distrusted, the planner
    stops calling it: match-only means only the rule action can be
    accepted, so the call is redundant. ``skip_after_distrust=False``
    restores the calls for the cost ablation. ``probe_manifest=True``
    copies the backend's ``last_manifest.sha256`` into the decision
    record; ``probe_manifest=False`` removes that readout.
    ``dead_pool_filter=False`` restores the old pool ordering for the
    dead-step ablation. ``rule_readout=True`` records ``probe.rule``
    with the rule goal, best post-move BFS distance, tie count,
    confidence (1/ties), the rule action's distance and whether it is
    optimal; ``rule_readout=False`` removes the field for the readout
    ablation. It never selects an action. ``deadline_ordering=True``
    uses a world-provided ``deadlines`` map to schedule remaining items
    by maximum collectible count then earliest finish, instead of the
    shortest tour; ``False`` restores the tour rule and suppresses the
    deadline readout for the ablation.
    """

    def __init__(self, backend=None, trust_window=20, noop_guard=True,
                 progress_guard=True, progress_skip_after=3,
                 cycle_escape=True, skip_after_distrust=True,
                 probe_manifest=True, dead_pool_filter=True,
                 rule_readout=True, deadline_ordering=True):
        if trust_window is not None:
            if (isinstance(trust_window, bool)
                    or not isinstance(trust_window, int)
                    or trust_window < 1):
                raise ValueError(
                    "Why: trust_window must be a positive int or None. "
                    "Fix: pass trust_window=20 or None.")
        if not isinstance(noop_guard, bool):
            raise ValueError(
                "Why: noop_guard must be a bool. Fix: pass noop_guard=True or False.")
        if not isinstance(progress_guard, bool):
            raise ValueError(
                "Why: progress_guard must be a bool. "
                "Fix: pass progress_guard=True or False.")
        if progress_skip_after is not None:
            if (isinstance(progress_skip_after, bool)
                    or not isinstance(progress_skip_after, int)
                    or progress_skip_after < 1):
                raise ValueError(
                    "Why: progress_skip_after must be a positive int or None. "
                    "Fix: pass progress_skip_after=3 or None.")
        if not isinstance(cycle_escape, bool):
            raise ValueError(
                "Why: cycle_escape must be a bool. "
                "Fix: pass cycle_escape=True or False.")
        if not isinstance(skip_after_distrust, bool):
            raise ValueError(
                "Why: skip_after_distrust must be a bool. "
                "Fix: pass skip_after_distrust=True or False.")
        if not isinstance(probe_manifest, bool):
            raise ValueError(
                "Why: probe_manifest must be a bool. "
                "Fix: pass probe_manifest=True or False.")
        if not isinstance(dead_pool_filter, bool):
            raise ValueError(
                "Why: dead_pool_filter must be a bool. "
                "Fix: pass dead_pool_filter=True or False.")
        if not isinstance(rule_readout, bool):
            raise ValueError(
                "Why: rule_readout must be a bool. "
                "Fix: pass rule_readout=True or False.")
        if not isinstance(deadline_ordering, bool):
            raise ValueError(
                "Why: deadline_ordering must be a bool. "
                "Fix: pass deadline_ordering=True or False.")
        self._get_hub = None
        self.backend = backend
        self.trust_window = trust_window
        self.noop_guard = noop_guard
        self.progress_guard = progress_guard
        self.progress_skip_after = progress_skip_after
        self.cycle_escape = cycle_escape
        self.skip_after_distrust = skip_after_distrust
        self.probe_manifest = probe_manifest
        self.dead_pool_filter = dead_pool_filter
        self.rule_readout = rule_readout
        self.deadline_ordering = deadline_ordering
        self._backend_distrusted = False
        self._progress_distrusted = False
        self._progress_streak = 0
        self.fallbacks = 0
        self.accepted = 0
        self.progress_rejections = 0
        self._recall_source = None
        self._persistent_loaded = False
        self._persistent_cache = None
        self._store_reads = 0
        self.last_probe = {}

    def bind_hub(self, getter):
        self._get_hub = getter

    def bind_recall_source(self, source):
        """Install a callable returning the persisted initial state.

        The source is consulted only when neither the current state nor
        the in-memory episode recall carries a needed field. Passing
        None disables the channel (executable ablation).
        """
        self._recall_source = source
        self.reset_recall_cache()

    def reset_recall_cache(self):
        """Forget any cached layout; called once per episode."""
        self._persistent_loaded = False
        self._persistent_cache = None
        self._store_reads = 0

    def reset_trust(self):
        """Restore full trust in the backend at the start of an episode."""
        self._backend_distrusted = False
        self._progress_distrusted = False
        self._progress_streak = 0

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
        probe = {"state": [], "memory": [], "persistent": [],
                 "store_reads": self._store_reads}
        self.last_probe = probe

        def _persistent_state():
            """Load the persisted initial state once per episode, lazily."""
            if self._persistent_loaded:
                return self._persistent_cache
            self._persistent_loaded = True
            if not callable(self._recall_source):
                return None
            self._store_reads += 1
            probe["store_reads"] = self._store_reads
            try:
                value = self._recall_source()
            except Exception:
                value = None
            if isinstance(value, dict):
                self._persistent_cache = value
            return self._persistent_cache

        def _recall(key):
            if state.get(key) is not None:
                if key not in probe["state"]:
                    probe["state"].append(key)
                return state.get(key)
            for m in reversed(mem_list):
                if isinstance(m, dict) and m.get(key) is not None:
                    if key not in probe["memory"]:
                        probe["memory"].append(key)
                    return m.get(key)
            fields = _TASK_FIELDS.get(state.get("task"))
            if fields is not None and key not in fields:
                return None
            persisted = _persistent_state()
            if isinstance(persisted, dict) and persisted.get(key) is not None:
                if key not in probe["persistent"]:
                    probe["persistent"].append(key)
                return persisted.get(key)
            return None

        if state.get("obstacles") is not None:
            obstacles = list(state.get("obstacles", []))
        else:
            recalled_ob = _recall("obstacles")
            obstacles = list(recalled_ob) if recalled_ob is not None else []
        if "obstacle" in state and state["obstacle"] not in obstacles:
            obstacles.append(state["obstacle"])

        def _toward(goal):
            return _step_toward(pos, goal, obstacles, visits,
                                probe=probe,
                                dead_pool_filter=self.dead_pool_filter)

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
        deadline_map = None
        raw_deadlines = None
        if self.deadline_ordering:
            raw_deadlines = state.get("deadlines")
            if raw_deadlines is None:
                task_fields = _TASK_FIELDS.get(state.get("task"))
                if task_fields is None or "deadlines" in task_fields:
                    raw_deadlines = _recall("deadlines")
            deadline_map = _deadline_map(raw_deadlines)
        deadline_view = None
        if deadline_map is not None:
            try:
                cells_for_view = [(int(c[0]), int(c[1]))
                                  for c in (remaining or [])]
            except (TypeError, ValueError, IndexError):
                cells_for_view = []
            if not cells_for_view:
                cells_for_view = sorted(deadline_map)
            if all(cell in deadline_map for cell in cells_for_view):
                deadline_view = [[cell[0], cell[1], int(deadline_map[cell])]
                                 for cell in cells_for_view]
        recalled_target = _recall("target")
        if "cue" in state:
            cue_val = state.get("cue")
        else:
            cue_val = _recall("cue")
        probe["resolved"] = {
            "target": _probe_safe(recalled_target),
            "items_positions": _probe_safe(remaining),
            "obstacles": _probe_safe(obstacles),
            "cue": _probe_safe(cue_val),
        }
        if deadline_view is not None:
            probe["resolved"]["deadlines"] = _probe_safe(deadline_view)
        self.last_probe = probe
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
            if deadline_view is not None:
                obs["deadlines"] = [list(entry) for entry in deadline_view]
            if visits:
                obs["visits"] = [[int(px), int(py), int(visits[(px, py)])]
                                 for (px, py) in sorted(visits)]
            probe["model_obs_keys"] = sorted(obs)

        deadline_goal = None

        def _rule_action():
            nonlocal deadline_goal
            if remaining:
                cells = [list(c) for c in remaining]
                if deadline_map is not None:
                    goal, info = _first_of_deadline_tour(
                        pos, cells, deadline_map, steps, obstacles)
                    if info is not None:
                        probe["deadline"] = info
                    if goal is not None:
                        deadline_goal = list(goal)
                        if pos == deadline_goal:
                            return "collect"
                        return _toward(deadline_goal)
                    if pos in cells:
                        return "collect"
                elif pos in cells:
                    return "collect"
                goal = _first_of_best_tour(pos, cells)
                return _toward(goal)
            target = recalled_target
            if target is not None:
                target = list(target)
                if pos == target:
                    if state.get("task") == "T2_delayed_match" and steps < 2:
                        return "wait"
                    return "collect"
                if self.cycle_escape and len(obstacles) >= 2:
                    repeated = 0
                    for m in mem_list:
                        if (isinstance(m, dict) and m.get("x") == x
                                and m.get("y") == y):
                            repeated += 1
                    if repeated >= 2:
                        action, distance = _bfs_step(pos, target, obstacles)
                        if action is not None:
                            probe["cycle_escape"] = {
                                "position": [int(x), int(y)],
                                "visits": repeated,
                                "distance": distance,
                                "action": action,
                            }
                            return action
                return _toward(target)
            return "wait"

        occupied = {tuple(cell) for cell in (obstacles or [])}

        def _movement_noop(action):
            if action not in ("up", "down", "left", "right"):
                return False
            nx, ny = pos
            if action == "up":
                ny -= 1
            elif action == "down":
                ny += 1
            elif action == "left":
                nx -= 1
            else:
                nx += 1
            if not (0 <= nx < SIZE and 0 <= ny < SIZE):
                return True
            return (nx, ny) in occupied

        def _distance_after(action):
            """BFS distance after one free movement; None otherwise."""
            if action not in ("up", "down", "left", "right"):
                return None
            nx, ny = pos
            if action == "up":
                ny -= 1
            elif action == "down":
                ny += 1
            elif action == "left":
                nx -= 1
            else:
                nx += 1
            if not (0 <= nx < SIZE and 0 <= ny < SIZE):
                return None
            if (nx, ny) in occupied:
                return None
            return _bfs_distance([nx, ny], recalled_target, obstacles)

        rule_action = _rule_action()
        if self.rule_readout:
            rule_goal = None
            if remaining:
                cells = [list(cell) for cell in remaining]
                if deadline_goal is not None:
                    rule_goal = list(deadline_goal)
                elif pos in cells:
                    rule_goal = list(pos)
                else:
                    rule_goal = _first_of_best_tour(pos, cells)
                    tour = _tour_audit(pos, cells)
                    if tour is not None:
                        probe["tour"] = tour
            elif recalled_target is not None:
                rule_goal = list(recalled_target)
            readout = _rule_confidence(pos, rule_goal, obstacles,
                                       rule_action, visits)
            if readout is not None:
                probe["rule"] = readout
                self.last_probe = probe
        if self.backend is not None:
            since = 0
            if self.trust_window is not None:
                try:
                    since = int(self.read_hub().get("steps_since_reward", 0))
                except Exception:
                    since = 0
            if self.skip_after_distrust and self._backend_distrusted:
                decision = {
                    "proposed": None,
                    "rule": rule_action,
                    "steps_since_reward": since,
                    "trust_window": self.trust_window,
                    "noop_guard": self.noop_guard,
                    "progress_guard": self.progress_guard,
                    "progress_skip_after": self.progress_skip_after,
                    "progress_streak": self._progress_streak,
                    "progress_distrusted": self._progress_distrusted,
                    "distrusted": True,
                    "accepted": False,
                    "reason": "skipped",
                    "skipped": True,
                }
                if self.probe_manifest:
                    decision["model_manifest_sha256"] = None
                probe["model_decision"] = decision
                self.last_probe = probe
                return rule_action
            if (self.progress_skip_after is not None
                    and self._progress_distrusted):
                decision = {
                    "proposed": None,
                    "rule": rule_action,
                    "steps_since_reward": since,
                    "trust_window": self.trust_window,
                    "noop_guard": self.noop_guard,
                    "progress_guard": self.progress_guard,
                    "progress_skip_after": self.progress_skip_after,
                    "progress_streak": self._progress_streak,
                    "progress_distrusted": True,
                    "distrusted": self._backend_distrusted,
                    "accepted": False,
                    "reason": "skipped-progress",
                    "skipped": True,
                }
                if self.probe_manifest:
                    decision["model_manifest_sha256"] = None
                probe["model_decision"] = decision
                self.last_probe = probe
                return rule_action
            manifest_sha = None
            try:
                spend("llm_calls")
                proposed = self.backend.generate(obs)
                stats = getattr(self.backend, "last_prompt_stats", None)
                if isinstance(stats, dict):
                    tokens = stats.get("tokens")
                    if (isinstance(tokens, (int, float))
                            and not isinstance(tokens, bool)):
                        spend("tokens", tokens)
                if self.probe_manifest:
                    manifest = getattr(self.backend, "last_manifest", None)
                    if isinstance(manifest, dict):
                        value = manifest.get("sha256")
                        if isinstance(value, str):
                            manifest_sha = value
            except BudgetExceeded:
                raise
            except Exception:
                proposed = None
                manifest_sha = None
            accepted = False
            reason = "invalid"
            progress = None
            progress_blocked = False
            if isinstance(proposed, str) and proposed in _LEGAL_ACTIONS:
                noop = (self.noop_guard and (
                    (proposed == "wait" and rule_action != "wait")
                    or (proposed == "collect" and rule_action != "collect")
                    or (_movement_noop(proposed)
                        and proposed != rule_action)))
                if (self.progress_guard and not remaining
                        and recalled_target is not None
                        and proposed in ("up", "down", "left", "right")):
                    proposed_distance = _distance_after(proposed)
                    rule_distance = _distance_after(rule_action)
                    if rule_distance is None and rule_action in ("collect",
                                                                 "wait"):
                        rule_distance = _bfs_distance(
                            pos, recalled_target, obstacles)
                    if (proposed_distance is not None
                            and rule_distance is not None
                            and proposed_distance > rule_distance):
                        progress_blocked = True
                        self.progress_rejections += 1
                        self._progress_streak += 1
                        progress = {"proposed": proposed_distance,
                                    "rule": rule_distance}
                if noop:
                    reason = "no-op"
                elif progress_blocked:
                    reason = "no-progress"
                elif self.trust_window is None or proposed == rule_action:
                    accepted = True
                    reason = "accepted"
                elif not self._backend_distrusted and since < self.trust_window:
                    accepted = True
                    reason = "accepted"
                elif self._backend_distrusted:
                    reason = "distrusted"
                elif since >= self.trust_window:
                    self._backend_distrusted = True
                    reason = "stall"
                if not progress_blocked:
                    self._progress_streak = 0
                elif (self.progress_skip_after is not None
                      and self._progress_streak >= self.progress_skip_after):
                    self._progress_distrusted = True
            else:
                self._progress_streak = 0
            decision = {
                "proposed": proposed,
                "rule": rule_action,
                "steps_since_reward": since,
                "trust_window": self.trust_window,
                "noop_guard": self.noop_guard,
                "progress_guard": self.progress_guard,
                "progress_skip_after": self.progress_skip_after,
                "progress_streak": self._progress_streak,
                "progress_distrusted": self._progress_distrusted,
                "distrusted": self._backend_distrusted,
                "accepted": accepted,
                "reason": reason,
                "skipped": False,
            }
            if progress is not None:
                decision["progress"] = progress
            if self.probe_manifest:
                decision["model_manifest_sha256"] = manifest_sha
            probe["model_decision"] = decision
            self.last_probe = probe
            if accepted:
                self.accepted += 1
                return proposed
            self.fallbacks += 1
        return rule_action


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

    def size(self):
        """Return the number of recorded transitions in O(1).

        ``history()`` deep-copies the whole record, so ``len(history())`` is
        O(n) work for an O(1) answer. The loop needs only the length once per
        step, so it calls this instead.
        """
        return len(self._history)

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
                 memory_store=None, planner_tracker=None, self_model=None, telemetry_log=None,
                 module_signals=True, module_s_mode="keys",
                 module_m_mode="turns", module_p_mode="alternatives",
                 learn_context=False):
        self.memory = memory if memory is not None else Memory()
        self.planner = planner if planner is not None else Planner()
        self.selfmodel = selfmodel if selfmodel is not None else SelfModel()
        self.telemetry = telemetry if telemetry is not None else Telemetry()
        self.world = world
        self.memory_store = memory_store
        self.planner_tracker = planner_tracker
        self.self_model = self_model
        self.telemetry_log = telemetry_log
        if not isinstance(module_signals, bool):
            raise ValueError(
                "Why: module_signals must be a bool. "
                "Fix: pass module_signals=True or False.")
        self._emit_module_signals = module_signals
        if module_s_mode not in ("keys", "seen"):
            raise ValueError(
                "Why: module_s_mode must be 'keys' or 'seen'. "
                "Fix: pass module_s_mode='keys'.")
        self._module_s_mode = module_s_mode
        if module_m_mode not in ("turns", "revisits"):
            raise ValueError(
                "Why: module_m_mode must be 'turns' or 'revisits'. "
                "Fix: pass module_m_mode='turns'.")
        self._module_m_mode = module_m_mode
        if module_p_mode not in ("alternatives", "distance"):
            raise ValueError(
                "Why: module_p_mode must be 'alternatives' or 'distance'. "
                "Fix: pass module_p_mode='alternatives'.")
        self._module_p_mode = module_p_mode
        if not isinstance(learn_context, bool):
            raise ValueError(
                "Why: learn_context must be a bool. "
                "Fix: pass learn_context=True or False.")
        self._learn_context = learn_context
        self._hub = {}
        self._steps_since_reward = 0
        #: Laplace-smoothed outcome frequencies, learned online from error
        #: only. Never told the reward rule; scored prequentially.
        self._online = OnlinePredictor()
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
        bind_recall = getattr(self.planner, "bind_recall_source", None)
        if callable(bind_recall):
            try:
                bind_recall(self._persistent_layout)
            except Exception:
                self._substrate_errors["bind"] += 1
        bind_predictor = getattr(self.planner, "bind_predictor", None)
        if callable(bind_predictor):
            try:
                bind_predictor(self._online)
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
        reset_recall = getattr(self.planner, "reset_recall_cache", None)
        if callable(reset_recall):
            reset_recall()
        reset_trust = getattr(self.planner, "reset_trust", None)
        if callable(reset_trust):
            reset_trust()
        self._steps_since_reward = 0
        self._hub = {}

    def online_predictions(self):
        """Return the outcomes learned online so far, keyed by feature.

        This table persists across ``run_task`` calls: it is the agent's
        accumulated estimate of when a step is rewarded, formed only from
        outcomes it has observed.
        """
        return self._online.table()

    def online_predictor(self):
        """Return the active predictor object (for freezing or swapping)."""
        return self._online

    def use_predictor(self, predictor):
        """Install a predictor and rebind the planner; return the old one.

        The predictor is the agent's learned-reward model, so a caller may
        replace it (a frozen wrapper, an alternative learner) without
        reaching into a private attribute. Rebinding the planner keeps the
        policy reading whatever is installed.
        """
        previous = self._online
        self._online = predictor
        bind = getattr(self.planner, "bind_predictor", None)
        if callable(bind):
            try:
                bind(predictor)
            except Exception:
                self._substrate_errors["bind"] += 1
        return previous

    def _persistent_layout(self):
        """Return the persisted initial state for this world, or None.

        The layout is stored once per (task, seed) in a separate table,
        so it survives a process restart even after the per-step memory
        rows have advanced. Any read failure is counted and treated as
        absent: recovery degrades to the old behavior, never a crash.
        """
        store = self.memory_store
        world = self.world
        if store is None or world is None:
            return None
        get_layout = getattr(store, "get_layout", None)
        if not callable(get_layout):
            return None
        task = getattr(world, "task_id", None)
        seed = getattr(world, "seed", None)
        if task is None or seed is None:
            return None
        fingerprint = world_fingerprint(world)
        try:
            content = get_layout(task, seed, fingerprint=fingerprint)
        except Exception:
            self._substrate_errors["memory_store"] += 1
            return None
        if not isinstance(content, str):
            return None
        try:
            value = json.loads(content)
        except (TypeError, ValueError):
            return None
        return value if isinstance(value, dict) else None

    def _layout_complete(self, state):
        """True when a state carries every goal field its task consumes.

        Unknown task names keep the generic all-field fallback, so
        custom worlds are not blocked by the known-task map.
        """
        if not isinstance(state, dict):
            return False
        task = state.get("task")
        if task is None and self.world is not None:
            task = getattr(self.world, "task_id", None)
        fields = _TASK_FIELDS.get(task)
        if fields is None:
            return True
        return all(state.get(key) is not None for key in fields)

    def _remember_layout(self, state):
        """Persist the initial state once; never store an incomplete one.

        A cold-first run must not poison the first-write-wins row: only
        task-complete states are written, and a complete state may
        replace an existing incomplete row. Only stores that expose
        save_layout participate. A failure is counted and never
        interrupts the episode.
        """
        store = self.memory_store
        world = self.world
        if store is None or world is None or not self._layout_complete(state):
            return
        save_layout = getattr(store, "save_layout", None)
        if not callable(save_layout):
            return
        task = getattr(world, "task_id", None)
        seed = getattr(world, "seed", None)
        if task is None or seed is None:
            return
        fingerprint = world_fingerprint(world)
        replace = False
        get_layout = getattr(store, "get_layout", None)
        if callable(get_layout):
            try:
                existing = get_layout(task, seed)
            except Exception:
                self._substrate_errors["memory_store"] += 1
                existing = None
            if existing is not None:
                try:
                    existing_state = json.loads(existing)
                except (TypeError, ValueError):
                    existing_state = None
                if self._layout_complete(existing_state):
                    fp_api = getattr(store, "layout_fingerprint", None)
                    backfill = False
                    if callable(fp_api):
                        try:
                            stored_fp = fp_api(task, seed)
                        except Exception:
                            self._substrate_errors["memory_store"] += 1
                            stored_fp = None
                        # A legacy complete row has no fingerprint; write the
                        # current (complete) state and fingerprint so the
                        # collision guard is active on upgraded stores.
                        backfill = (stored_fp is None and fingerprint is not None)
                    if not backfill:
                        try:
                            same_world = get_layout(task, seed,
                                                    fingerprint=fingerprint)
                        except Exception:
                            self._substrate_errors["memory_store"] += 1
                            same_world = existing
                        if same_world is not None:
                            return
                replace = True
        try:
            save_layout(task, seed, json.dumps(state, sort_keys=True),
                        replace=replace, fingerprint=fingerprint)
        except Exception:
            self._substrate_errors["memory_store"] += 1

    # -- loop ----------------------------------------------------------

    def _module_signals(self, memories, learned, keys, seen):
        """Return pre-action M/P/S state that is not an elapsed-time counter.

        M = [distinct positions, turns or revisits];
        P = [alternatives count or BFS distance, ties];
        S = [online probability, distinct feature keys seen]. These are read from the
        memory contents, the planner's rule probe and the online predictor
        before the step, so they vary with the episode's geometry and
        history rather than with its index.
        """
        try:
            positions = [(int(m.get("x", 0)), int(m.get("y", 0)))
                         for m in (memories or [])
                         if isinstance(m, dict) and "x" in m and "y" in m]
        except (TypeError, ValueError):
            positions = []
        distinct = len(set(positions))
        revisits = len(positions) - distinct
        last = None
        turns = 0
        for first, second in zip(positions, positions[1:]):
            delta = (second[0] - first[0], second[1] - first[1])
            if delta == (0, 0):
                continue
            if last is not None and delta != last:
                turns += 1
            last = delta
        probe = getattr(self.planner, "last_probe", None)
        rule = probe.get("rule") if isinstance(probe, dict) else None
        distance = -1
        ties = 0
        if isinstance(rule, dict):
            try:
                distance = int(rule.get("distance"))
            except (TypeError, ValueError):
                distance = -1
            try:
                ties = int(rule.get("ties", 0))
            except (TypeError, ValueError):
                ties = 0
        if self._module_p_mode == "alternatives":
            alternatives = rule.get("alternatives") if isinstance(rule, dict) else None
            distance = len(alternatives) if isinstance(alternatives, list) else 0
        second = keys if self._module_s_mode == "keys" else seen
        second_m = turns if self._module_m_mode == "turns" else revisits
        return {
            "M": [distinct, second_m],
            "P": [distance, ties],
            "S": [float(learned), int(second)],
        }

    def _learn_context_value(self, state):
        """Return the pre-action learned-context suffix, or None.

        ``learn_context=True`` lets the predictor key on a world's context,
        which is the only way a policy can act on state the distance bucket
        cannot see. ``False`` returns None, so the shipped key is unchanged.
        """
        if not self._learn_context:
            return None
        context = self._world_context(state).get("G")
        return context if context else None

    def _world_context(self, state):
        """Return an optional world-provided context block for signals.

        A world exposes ``signal_context(state)`` when it carries state the
        M/P/S blocks cannot see. The readout is taken from the pre-action
        state, so a context value cannot leak the outcome of the step it
        labels. Worlds without the hook emit no ``G`` block, so every
        shipped row shape is unchanged.
        """
        api = getattr(self.world, "signal_context", None)
        if not callable(api):
            return {}
        try:
            values = api(state)
        except Exception:
            self._substrate_errors["bind"] += 1
            return {}
        if not isinstance(values, (list, tuple)) or not values:
            return {}
        try:
            return {"G": [float(value) for value in values]}
        except (TypeError, ValueError):
            self._substrate_errors["bind"] += 1
            return {}

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
                blen = self.selfmodel.size()
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

    def run(self, max_steps=200, budget=None):
        """Run the loop; optionally install an execution budget.

        A budget caps steps, LLM calls, tokens and wall time. It is
        opt-in: with ``None`` every spend call is a no-op and actions are
        unchanged. Exhaustion raises :class:`BudgetExceeded`.
        """
        if budget is None:
            return self._run_loop(max_steps)
        with use_budget(budget):
            return self._run_loop(max_steps)

    def _require_planner_coverage(self):
        """Refuse a bounded policy that cannot emit the world's actions.

        A policy with a fixed action set (``LearnedPlanner``) can only ever
        propose those actions. Paired with a world whose actions it does not
        cover, it silently spends the whole step budget and scores zero:
        ``LearnedPlanner()`` on ``T1_forage`` runs 200 steps with reward 0.0.
        That is a configuration error, so it is raised here with the missing
        actions named instead of being reported as a bad run.

        The check is skipped when either side does not declare an action
        set, so the rule planner and custom worlds are unaffected.
        """
        declared = getattr(self.planner, "actions", None)
        expected = getattr(self.world, "ACTIONS", None)
        if not isinstance(declared, (list, tuple)) or not declared:
            return
        if not isinstance(expected, (list, tuple)) or not expected:
            return
        missing = [action for action in expected if action not in declared]
        if not missing:
            return
        raise ValueError(
            "Why: %s can only emit %s, but %s requires %s; the run would "
            "spend every step and score nothing. "
            "Fix: use the rule planner for this world or pass "
            "actions=(%s)."
            % (type(self.planner).__name__, ", ".join(declared),
               getattr(self.world, "task_id", type(self.world).__name__),
               ", ".join(expected),
               ", ".join(repr(action) for action in expected)))

    def _run_loop(self, max_steps):
        """Run perceive/plan/act/observe loop; return trace list."""
        if self.world is None:
            raise ValueError("Agent.world is None; pass a world or use run_task")
        if max_steps <= 0:
            raise ValueError("max_steps must be positive")
        self._require_planner_coverage()
        reset_recall = getattr(self.planner, "reset_recall_cache", None)
        if callable(reset_recall):
            reset_recall()
        reset_trust = getattr(self.planner, "reset_trust", None)
        if callable(reset_trust):
            reset_trust()
        self._steps_since_reward = 0
        self.hub_write({"steps_since_reward": 0})
        trace = []
        state = self.world.reset()
        self._remember_layout(state)
        for i in range(int(max_steps)):
            spend("steps")
            self.memory.save(state)  # perceive
            memories = self.memory.recall(limit=None)  # recall for planner
            action = self.planner.plan(state, memories)  # plan
            prediction, prediction_basis = predict_outcome(
                state, action, getattr(self.world, "task_id", None))
            _learn_key = context_feature_key(
                getattr(self.world, "task_id", None), state, action,
                self._learn_context_value(state))
            _learned = self._online.predict(_learn_key)
            _keys = len(self._online.keys())
            _seen = self._online.seen(_learn_key)
            new_state, reward, done = self.world.step(action)  # act
            self._online.observe(_learn_key, float(reward) > 0.0)
            self.telemetry.log({"step": i, "action": action, "reward": reward, "done": done})
            self.selfmodel.record(new_state, action, reward, done)
            if float(reward) > 0.0:
                self._steps_since_reward = 0
            else:
                self._steps_since_reward += 1
            self.hub_write({"last_step": i, "last_action": action,
                            "last_reward": reward,
                            "steps_since_reward": self._steps_since_reward})
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
                    _ok_sm = float(reward) > 0.0
                    self.self_model.record_prediction(1.0, _ok_sm, prediction)
                except Exception:
                    self._substrate_errors["self_model"] += 1
            m_vec, p_vec, s_vec, hub_vec = self._step_vectors(i, new_state, reward, memories)
            _signals = None
            _signals_meta = None
            if self._emit_module_signals:
                _signals = self._module_signals(
                    memories, _learned, _keys, _seen)
                _signals_meta = {
                    "version": SIGNALS_VERSION,
                    "M": self._module_m_mode,
                    "P": self._module_p_mode,
                    "S": self._module_s_mode,
                }
                _signals.update(self._world_context(state))
                if "G" in _signals:
                    _signals_meta["G"] = "world"
                _probe_meta = getattr(self.planner, "last_probe", None)
                _persistent_fields = 0
                _store_reads = 0
                if isinstance(_probe_meta, dict):
                    _persistent = _probe_meta.get("persistent")
                    if isinstance(_persistent, list):
                        _persistent_fields = len(_persistent)
                    _reads = _probe_meta.get("store_reads")
                    if isinstance(_reads, (int, float)) and not isinstance(_reads, bool):
                        _store_reads = int(_reads)
                _signals_meta["persistent_fields"] = _persistent_fields
                _signals_meta["store_reads"] = _store_reads
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
                probe = getattr(self.planner, "last_probe", None)
                if isinstance(probe, dict):
                    args["probe"] = copy.deepcopy(probe)
                if _signals is not None:
                    args["signals"] = _signals
                    args["signals_meta"] = dict(_signals_meta)
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
            record = {"step": i, "state": copy.deepcopy(new_state),
                      "action": action, "reward": reward, "done": done}
            if _signals is not None:
                record["signals"] = _signals
                record["signals_meta"] = dict(_signals_meta)
            trace.append(record)
            state = new_state
            if done:
                break
        return trace

    def run_task(self, task_id, seed, max_steps=200, budget=None):
        """Build GridWorld(task_id, seed) and run the loop."""
        from worlds.grid import GridWorld

        self.world = GridWorld(task_id, seed)
        self._reset_episode()
        return self.run(max_steps=max_steps, budget=budget)

    def _episode_verdict(self, trace, max_steps):
        """Return (verdict, reason) without mistaking the cap for success.

        The world sets done at the energy/step cap as well as on task
        completion, so ``done`` alone is not a success fact. A trace
        that consumed the full budget is truncated even when its last
        record says done; the reason carries steps and reward.
        """
        steps = len(trace)
        reward = sum(float(record.get("reward", 0.0)) for record in trace)
        ended = bool(trace) and bool(trace[-1].get("done"))
        at_cap = steps >= int(max_steps)
        verdict = "done" if ended and not at_cap else "truncated"
        return verdict, "steps=%d reward=%.1f" % (steps, reward)

    def run_task_logged(self, task_id, seed, max_steps=200, log_path=None,
                        budget=None, workspace_root=None,
                        calibration_path=None,
                        calibration_keep_recent=None,
                        calibration_hmac_key=None):
        """Run task with header, per-step actions+results, and verdict.

        Writes header (seq 0), one kind "step" action plus one result
        per grid step with numeric M/P/S/hub vectors, then a verdict.
        The verdict is done only for a pre-cap completion; a full-budget
        run is truncated. Returns the in-memory trace list with
        unchanged shape. When ``calibration_path`` is given, the
        persistent self-model's forecasts for this run are appended to
        the calibration journal after the verdict, under a prefix taken
        from the header digest. ``calibration_keep_recent`` optionally
        rotates the journal immediately after that append, keeping the
        newest N live and archiving older records.
        ``calibration_hmac_key`` appends keyed records and verifies the
        existing journal first. The bridge is opt-in and does not change
        actions; a calibration-store failure raises after the verdict.
        """
        if calibration_hmac_key is not None:
            if calibration_path is None:
                raise ValueError(
                    "Why: calibration_hmac_key needs calibration_path. "
                    "Fix: pass calibration_path=... or omit the key.")
            if (not isinstance(calibration_hmac_key, (bytes, bytearray))
                    or not calibration_hmac_key):
                raise ValueError(
                    "Why: calibration_hmac_key must be non-empty bytes or "
                    "None. Fix: pass the verifier-held bytes key, or omit it.")
        if calibration_keep_recent is not None:
            if calibration_path is None:
                raise ValueError(
                    "Why: calibration_keep_recent needs calibration_path. "
                    "Fix: pass calibration_path=... or omit "
                    "calibration_keep_recent.")
            if (isinstance(calibration_keep_recent, bool)
                    or not isinstance(calibration_keep_recent, int)
                    or calibration_keep_recent < 1):
                raise ValueError(
                    "Why: calibration_keep_recent must be a positive int "
                    "or None. Fix: pass calibration_keep_recent=100.")
        if calibration_path is not None:
            if self.self_model is None:
                raise ValueError(
                    "Why: calibration_path needs a persistent self_model. "
                    "Fix: pass Agent(self_model=SelfModel()) or omit "
                    "calibration_path.")
            for method in ("forecast_count", "forecasts"):
                if not callable(getattr(self.self_model, method, None)):
                    raise ValueError(
                        "Why: calibration_path needs a self_model with "
                        "forecast_count/forecasts. Fix: use "
                        "self_model.model.SelfModel.")
        if log_path is not None:
            from telemetry.log import Telemetry as _FileTelemetry

            self.telemetry_log = _FileTelemetry(log_path)
        if self.telemetry_log is None:
            raise ValueError("telemetry_log or log_path is required")
        from worlds.grid import GridWorld

        self.world = GridWorld(task_id, seed)
        self._reset_episode()
        initial = self.world.reset()
        identity_sha, _projection = input_digest(initial, {
            "task": task_id, "seed": seed, "max_steps": max_steps,
            "policy_sha256": policy_digest(),
        })
        workspace_sha = (workspace_digest(workspace_root)
                         if workspace_root is not None else None)
        self.last_episode_sha256 = identity_sha
        self.last_workspace_sha256 = workspace_sha
        header = self.telemetry_log.write_header(
            task_id, max_steps,
            policy=PLANNER_POLICY["name"],
            policy_sha256=policy_digest(),
            model=model_label(self.planner.backend),
            episode_sha256=identity_sha,
            workspace_sha256=workspace_sha,
            seed=seed)
        forecast_start = (self.self_model.forecast_count()
                          if calibration_path is not None else 0)
        trace = self.run(max_steps=max_steps, budget=budget)
        verdict, reason = self._episode_verdict(trace, max_steps)
        try:
            self.telemetry_log.write_verdict(verdict, reason)
        except Exception:
            self._substrate_errors["verdict"] += 1
        if calibration_path is not None:
            from calibration_store import append_forecasts

            digest = header.get("digest") if isinstance(header, dict) else None
            prefix = str(digest or identity_sha)[:12]
            forecasts = self.self_model.forecasts(
                prefix, start=forecast_start)
            append_forecasts(forecasts, calibration_path,
                             keep_recent=calibration_keep_recent,
                             hmac_key=calibration_hmac_key)
        return trace

    def substrate_errors(self):
        """Return a copy of per-module persistent-substrate failure counts."""
        return dict(self._substrate_errors)
