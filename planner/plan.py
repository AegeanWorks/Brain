"""Ordered step tracker with explicit ok/fail marks and recovery.

Pure logic, no I/O. Each step is a dict:
{"name": str, "op": str, "status": "pending"|"ok"|"failed"}.
The cursor idx points at the current step.

``LearnedPlanner`` is the acting counterpart of the online predictor: it
picks the action whose learned reward probability is highest, so the agent
can use what it learned to *act* instead of only to predict.
"""

from self_model.online import context_feature_key

#: Action order used to break ties, so the policy is deterministic.
DEFAULT_ACTIONS = ("left", "right")


class Planner:
    """Track a linear sequence of named operations."""

    def __init__(self, steps=None):
        """Build a tracker from an optional initial step list.

        Each entry may be a dict with name/op keys, a (name, op)
        pair, or a plain name string (op defaults to the name).
        """
        self._steps = []
        self._idx = 0
        for item in list(steps) if steps else []:
            if isinstance(item, dict):
                self.add_step(item.get("name", ""), item.get("op", ""))
            elif isinstance(item, (tuple, list)) and len(item) >= 2:
                self.add_step(item[0], item[1])
            else:
                self.add_step(str(item), str(item))

    def add_step(self, name, op):
        """Append one pending step. Returns its index."""
        self._steps.append({"name": str(name), "op": str(op), "status": "pending"})
        return len(self._steps) - 1

    def next(self):
        """Return the current step dict copy, or None when drained."""
        if 0 <= self._idx < len(self._steps):
            return dict(self._steps[self._idx])
        return None

    def mark_ok(self):
        """Mark the current step ok and advance. Returns True if moved."""
        if 0 <= self._idx < len(self._steps):
            self._steps[self._idx]["status"] = "ok"
            self._idx += 1
            return True
        return False

    def mark_fail(self):
        """Mark the current step failed. Cursor holds for recover()."""
        if 0 <= self._idx < len(self._steps):
            self._steps[self._idx]["status"] = "failed"
            return True
        return False

    def recover(self):
        """Skip failed entries and return the next viable step or None."""
        while 0 <= self._idx < len(self._steps):
            status = self._steps[self._idx]["status"]
            if status == "failed":
                self._idx += 1
                continue
            if status == "pending":
                return dict(self._steps[self._idx])
            self._idx += 1
        return None

    def state(self):
        """Return cursor plus per-step status list."""
        return {
            "idx": self._idx,
            "total": len(self._steps),
            "status": [s["status"] for s in self._steps],
            "steps": [dict(s) for s in self._steps],
            "done": self._idx >= len(self._steps),
        }

class LearnedPlanner:
    """Choose the action with the highest learned reward probability.

    The planner holds no knowledge of the reward rule. It asks a bound
    ``OnlinePredictor`` for each candidate action's probability given the
    current state (and, when ``use_context`` is true, the pre-action world
    context) and returns the argmax in ``ACTIONS`` order. Without a bound
    predictor or without a context the policy is the deterministic prior
    over actions, which is the blind baseline.
    """

    def __init__(self, actions=None, use_context=True, task_id=None):
        self._actions = tuple(actions) if actions else DEFAULT_ACTIONS
        self._use_context = bool(use_context)
        self._task_id = task_id
        self._predictor = None
        self.last_probe = {}

    def bind_predictor(self, predictor):
        """Bind the online predictor this policy reads estimates from."""
        self._predictor = predictor

    def _context(self, state):
        if not self._use_context or not isinstance(state, dict):
            return None
        context = state.get("context")
        return context if isinstance(context, (list, tuple)) else None

    def scores(self, state):
        """Return ``{action: probability}`` for the current state."""
        context = self._context(state)
        task = self._task_id or (state.get("task") if isinstance(state, dict) else None)
        scores = {}
        for action in self._actions:
            if self._predictor is None:
                scores[action] = 0.5
            else:
                key = context_feature_key(task, state, action, context)
                scores[action] = self._predictor.predict(key)
        return scores

    def plan(self, state, memories):
        """Return the argmax action; ties follow ``ACTIONS`` order."""
        scores = self.scores(state)
        best = None
        for action in self._actions:
            if best is None or scores[action] > scores[best]:
                best = action
        self.last_probe = {
            "state": [], "memory": [], "persistent": [], "store_reads": 0,
            "rule": {"distance": 0, "ties": 1, "alternatives": []},
            "scores": dict(scores),
            "context": self._context(state),
        }
        return best
