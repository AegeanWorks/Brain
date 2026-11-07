"""Per-run execution budget: steps, LLM calls, tokens and wall time.

Adapted from ``neurocore/core/execution_budget.py`` (AegeanWorks/
NeuroCore). A budget is created once per top-level agent run and shared
through a context variable, so the loop and the planner spend from the
same allowance. Exhaustion raises :class:`BudgetExceeded` with the
dimension, limit and usage; it is a reported failure, not a silent
fallback. With no budget active every ``spend`` call is a no-op.
"""

import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Dict, Iterator, Optional

DEFAULT_LIMITS = {
    "max_steps": 200,
    "max_llm_calls": 200,
    "max_tokens": 200_000,
    "max_seconds": 600,
}

SPEND_KINDS = ("steps", "llm_calls", "tokens")


def _valid_limits(limits):
    merged = dict(DEFAULT_LIMITS)
    if limits is not None:
        if not isinstance(limits, dict):
            raise ValueError("limits must be a dict or None")
        unknown = set(limits) - set(DEFAULT_LIMITS)
        if unknown:
            raise ValueError("unknown budget limits: %s" % sorted(unknown))
        merged.update(limits)
    for key, value in merged.items():
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("budget limit %s must be a non-negative int" % key)
        if key != "max_seconds" and value < 1:
            raise ValueError("budget limit %s must be positive" % key)
    return merged


class BudgetExceeded(RuntimeError):
    """Raised when one dimension of the run budget is exhausted."""

    def __init__(self, kind, limit, used):
        self.kind = kind
        self.limit = float(limit)
        self.used = float(used)
        super().__init__(
            "execution budget exhausted: %s used %g of %g. "
            "Why: one run may not spend without bound. "
            "Fix: raise the budget limit or reduce the steps/calls/tokens."
            % (kind, self.used, self.limit))


@dataclass
class ExecutionBudget:
    """Limits and usage for one top-level agent run."""

    limits: Dict[str, int] = field(default_factory=lambda: dict(DEFAULT_LIMITS))
    used: Dict[str, float] = field(
        default_factory=lambda: {kind: 0.0 for kind in SPEND_KINDS})
    started_at: float = field(default_factory=time.monotonic)
    exceeded: Optional[str] = None

    def __post_init__(self):
        self.limits = _valid_limits(self.limits)
        for kind in SPEND_KINDS:
            value = self.used.get(kind, 0.0)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
                raise ValueError("used budget values must be non-negative numbers")
            self.used[kind] = float(value)

    def remaining(self, kind):
        """Remaining units for one dimension; seconds uses wall time."""
        if kind == "seconds":
            return max(0.0, float(self.limits["max_seconds"]) - self.elapsed())
        if kind not in SPEND_KINDS:
            raise ValueError("unknown budget dimension %r" % (kind,))
        return max(0.0, float(self.limits["max_" + kind])
                   - self.used.get(kind, 0.0))

    def elapsed(self):
        """Seconds since this budget started."""
        return time.monotonic() - self.started_at

    def spend(self, kind, units=1):
        """Consume units, or raise :class:`BudgetExceeded` naming the dimension."""
        if kind not in SPEND_KINDS:
            raise ValueError("unknown budget dimension %r" % (kind,))
        if (isinstance(units, bool) or not isinstance(units, (int, float))
                or units < 0):
            raise ValueError("budget units must be a non-negative number")
        self.check_time()
        limit = float(self.limits["max_" + kind])
        self.used[kind] = self.used.get(kind, 0.0) + float(units)
        if self.used[kind] > limit:
            self.exceeded = kind
            raise BudgetExceeded(kind, limit, self.used[kind])

    def check_time(self):
        """Raise when wall time has already exceeded the seconds limit."""
        if self.elapsed() > float(self.limits["max_seconds"]):
            self.exceeded = "seconds"
            raise BudgetExceeded("seconds", float(self.limits["max_seconds"]),
                                 self.elapsed())

    @property
    def pressure(self):
        """The fullest non-time dimension as a 0..1 fraction."""
        fractions = [
            self.used.get(kind, 0.0) / float(self.limits["max_" + kind])
            for kind in SPEND_KINDS if self.limits.get("max_" + kind)
        ]
        return min(1.0, max(fractions) if fractions else 0.0)

    def snapshot(self):
        """JSON-ready limits, usage, elapsed time, pressure and exceeded flag."""
        return {
            "limits": dict(self.limits),
            "used": {kind: round(value, 2)
                     for kind, value in self.used.items()},
            "elapsed_seconds": round(self.elapsed(), 2),
            "pressure": round(self.pressure, 3),
            "exceeded": self.exceeded,
        }


_current = ContextVar("execution_budget", default=None)


def current_budget():
    """The active budget for this context, or None."""
    return _current.get()


@contextmanager
def use_budget(budget):
    """Install a budget for the current task; nested runs inherit it."""
    token = _current.set(budget)
    try:
        yield budget
    finally:
        _current.reset(token)


def spend(kind, units=1):
    """Spend from the active budget when one is installed; else no-op."""
    budget = _current.get()
    if budget is not None:
        budget.spend(kind, units)


def push_budget(budget):
    """Install a budget and return the context token; pair with pop_budget."""
    return _current.set(budget)


def pop_budget(token):
    """Restore the previous context budget."""
    _current.reset(token)


def budget_from_limits(limits=None):
    """Build an ExecutionBudget from a partial limit mapping."""
    return ExecutionBudget(limits=limits or {})
