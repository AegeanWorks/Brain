"""A name-to-provider registry so a backend can be selected without code.

``evals/trust.py`` already keeps a local ``BACKENDS`` dict of test doubles,
which is the right shape at the wrong scope. This module is the shared one:
a provider is registered under a name and built by that name, so a caller
never has to import a concrete class.

An unknown name **raises** and names the choices. A silent fallback would
let a run proceed under a provider the caller did not ask for, which is the
failure mode this repository exists to prevent.
"""

from models.backend import StubBackend

#: Registered providers, name -> factory. ``llamacpp`` is imported lazily
#: inside its factory so this module has no subprocess or socket import.
BACKENDS = {}


def register(name, factory):
    """Register ``factory`` under ``name``; a duplicate name raises."""
    if not isinstance(name, str) or not name:
        raise ValueError(
            "Why: a backend name must be a non-empty string. "
            "Fix: pass name='stub'.")
    if name in BACKENDS:
        raise ValueError(
            "Why: backend %r is already registered. "
            "Fix: pick another name or use a distinct provider." % name)
    BACKENDS[name] = factory
    return factory


def build(name, **config):
    """Build the provider registered under ``name`` with ``config``.

    Raises ``KeyError`` naming both the requested name and the available
    ones, so a typo is visible instead of silently selecting a default.
    """
    try:
        factory = BACKENDS[name]
    except KeyError:
        raise KeyError(
            "Why: %r is not a registered backend. Fix: pass one of %s."
            % (name, sorted(BACKENDS)))
    return factory(**config)


def names():
    """Return the registered backend names, sorted."""
    return sorted(BACKENDS)


def _build_llamacpp(**config):
    from models.llamacpp import LlamaCppBackend
    return LlamaCppBackend(**config)


def _build_openai(**config):
    from models.openai_backend import OpenAIBackend
    return OpenAIBackend(**config)


register("stub", StubBackend)
register("llamacpp", _build_llamacpp)
register("openai", _build_openai)
