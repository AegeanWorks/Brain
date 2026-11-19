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
        #: True once a confidence has been recorded before its outcome, which
        #: makes the pairs a real forecast rather than a restatement of them.
        self._pre_outcome = False
        #: Per-pair counterpart of ``_pre_outcome``: a single model-wide flag
        #: cannot describe a model that mixes pre-action forecasts with
        #: post-hoc records, so each pair carries its own provenance.
        self._pre_flags = []

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
        self._pre_flags.append(False)
        return self.snapshot()

    def record_prediction(self, cost, ok, predicted):
        """Log one step with a confidence formed *before* the outcome.

        Unlike :meth:`record`, ``predicted`` is supplied by the caller from
        pre-action information, so the resulting pairs are a real forecast
        and their Brier/skill are not circular.
        """
        self._budget_used += float(cost)
        self._steps += 1
        if not ok:
            self._errors += 1
        self._confs.append(float(predicted))
        self._outcomes.append(1 if ok else 0)
        self._pre_outcome = True
        self._pre_flags.append(True)
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
        self._pre_outcome = False
        self._pre_flags = []

    def calibration(self, min_resolved=10):
        """Score recorded confidence/outcome pairs with Brier/log loss.

        When the pairs came from :meth:`record` the confidence was formed
        after the reward was known, so the score is circular and carries a
        ``confidence-is-outcome`` warning. When they came from
        :meth:`record_prediction` the confidence was formed before the
        action, so the score is a real forecast measure and the warning is
        not applied — even though such a forecast legitimately separates
        the outcome classes, which is the case the diagnosis must not flag.
        When a model mixes both kinds, the warning is decided from the
        post-hoc pairs alone so a real forecast cannot mask later circular
        records.
        """
        from calibration import confidence_is_outcome, summary
        forecasts = [
            {"id": str(index), "probability": conf, "outcome": outcome}
            for index, (conf, outcome) in enumerate(
                zip(self._confs, self._outcomes))
        ]
        result = summary(forecasts, min_resolved=min_resolved)
        # Only pairs whose confidence was formed after the outcome are
        # circular. Scoring the mixed set as one would let an earlier
        # forecast hide later post-hoc records, so judge the post-hoc pairs
        # on their own.
        post_hoc = [forecast for forecast, pre in zip(forecasts, self._pre_flags)
                    if not pre]
        if confidence_is_outcome(post_hoc):
            result["warnings"].append(
                "confidence-is-outcome: recorded after the outcome, so Brier "
                "restates the base rate and skill is not a forecast measure")
        return result

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
