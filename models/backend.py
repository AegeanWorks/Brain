"""ModelBackend interface and deterministic StubBackend for protocol pins."""

import abc


class ModelBackend(abc.ABC):
    """Propose one action token for an observation mapping.

    Observation keys: task, x, y, steps, legal (action token list).
    Implementations must be deterministic given a fixed seed config;
    any failure mode must raise (the caller counts the fallback).
    """

    @abc.abstractmethod
    def generate(self, observation):
        """Return one action token string for the observation."""
        raise NotImplementedError


class StubBackend(ModelBackend):
    """Replay a canned action script indexed by observation steps.

    Raises IndexError once the script is exhausted so overruns are
    visible instead of silently repeating.
    """

    def __init__(self, script):
        self._script = list(script)

    def generate(self, observation):
        idx = int(observation.get("steps", 0))
        if 0 <= idx < len(self._script):
            return self._script[idx]
        raise IndexError("stub script exhausted at step %d" % idx)
