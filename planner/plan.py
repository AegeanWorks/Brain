"""Ordered step tracker with explicit ok/fail marks and recovery.

Pure logic, no I/O. Each step is a dict:
{"name": str, "op": str, "status": "pending"|"ok"|"failed"}.
The cursor idx points at the current step.
"""


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
