"""Swappable small-model backends for Brain policies.

A backend proposes one action token per observation mapping. The
rule-based planner stays the default: a backend is consulted only when
one is attached, and any missing, invalid, or raising proposal falls
back to the rule policy with a counted fallback. Providers
(llama.cpp, Ollama, in-process weights) implement ModelBackend;
tonight only the deterministic StubBackend lives here for protocol
pins. No weights, binaries, or network clients in this package.
"""
