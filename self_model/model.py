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
        self._outcomes = []

    def record(self, cost, ok, conf):
        """Log one step: add cost, count ok/error, append confidence.

        Returns the updated snapshot dict.
        """
        self._budget_used += float(cost)
        self._steps += 1
        if not ok:
            self._errors += 1
        self._confs.append(float(conf))
        self._outcomes.append(1 if ok else 0)
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
        self._outcomes = []

    def calibration(self, min_resolved=10):
        """Score recorded confidence/outcome pairs with Brier/log loss."""
        from calibration import summary
        forecasts = [
            {"id": str(index), "probability": conf, "outcome": outcome}
            for index, (conf, outcome) in enumerate(
                zip(self._confs, self._outcomes))
        ]
        return summary(forecasts, min_resolved=min_resolved)

    def forecast_count(self):
        """Return the number of recorded confidence/outcome pairs."""
        return len(self._confs)

    def forecasts(self, prefix="run", start=0):
        """Return recorded pairs as forecast records with ids ``prefix:index``.

        ``start`` selects the first absolute index, so a caller can
        append only the pairs recorded during the current run.
        """
        if not isinstance(prefix, str) or not prefix.strip():
            raise ValueError(
                "Why: prefix must be a non-empty string. "
                "Fix: pass a run prefix.")
        if (isinstance(start, bool) or not isinstance(start, int)
                or start < 0 or start > len(self._confs)):
            raise ValueError(
                "Why: start must be an integer in [0, forecast_count()]. "
                "Fix: pass start=0 or the count captured before the run.")
        pairs = list(zip(self._confs, self._outcomes))[start:]
        return [
            {"id": "%s:%d" % (prefix, start + index),
             "probability": probability, "outcome": outcome}
            for index, (probability, outcome) in enumerate(pairs)
        ]
