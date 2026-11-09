"""ModelBackend interface and deterministic StubBackend for protocol pins."""

import abc


class ModelBackend(abc.ABC):
    """Propose one action token for an observation mapping.

    Observation keys: task, x, y, steps, legal (action token list).
    Implementations must be deterministic given a fixed seed config;
    any failure mode must raise (the caller counts the fallback).

    ``identity()`` is part of the protocol, not a convenience: run headers
    pin it, so a historical episode can only be re-verified if the label is
    stable across a class rename. A provider that relies on the default gets
    a name derived from its class, which ``models.conformance`` flags.
    """

    @abc.abstractmethod
    def generate(self, observation):
        """Return one action token string for the observation."""
        raise NotImplementedError

    def identity(self):
        """Return a stable, human-readable provider identity for run pins.

        Override this. The default is honest about being a fallback: it
        embeds the class name, so ``conformance`` can name a provider that
        never declared an identity of its own.
        """
        return "%s:%s" % (self.__class__.__module__.split(".")[-1],
                          type(self).__name__)


class StubBackend(ModelBackend):
    """Replay a canned action script indexed by observation steps.

    Raises IndexError once the script is exhausted so overruns are
    visible instead of silently repeating.
    """

    def __init__(self, script):
        self._script = list(script)

    def identity(self):
        return "stub:%s" % StubBackend.__name__

    def generate(self, observation):
        idx = int(observation.get("steps", 0))
        if 0 <= idx < len(self._script):
            return self._script[idx]
        raise IndexError("stub script exhausted at step %d" % idx)
