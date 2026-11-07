"""Running counters for cost, step outcomes, and reported confidence.

Pure logic, no I/O. All aggregates derive from recorded events.
"""


class SelfModel:
    """Tally budget use, step counts, errors, and confidence values."""

    def __init__(self):
        """Start all counters at zero with an empty confidence log."""
        self._budget_used = 0.0
        self._steps = 0
        self._errors = 0
        self._confs = []

    def record(self, cost, ok, conf):
        """Log one step: add cost, count ok/error, append confidence.

        Returns the updated snapshot dict.
        """
        self._budget_used += float(cost)
        self._steps += 1
        if not ok:
            self._errors += 1
        self._confs.append(float(conf))
        return self.snapshot()

    def snapshot(self):
        """Return steps, errors, budget, mean_conf, and error_rate."""
        n = self._steps
        mean_conf = sum(self._confs) / len(self._confs) if self._confs else 0.0
        error_rate = (self._errors / n) if n else 0.0
        return {
            "steps": self._steps,
            "errors": self._errors,
            "budget": self._budget_used,
            "mean_conf": mean_conf,
            "error_rate": error_rate,
        }

    def reset(self):
        """Return all counters to zero and clear the confidence log."""
        self._budget_used = 0.0
        self._steps = 0
        self._errors = 0
        self._confs = []
