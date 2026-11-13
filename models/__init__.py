"""Swappable small-model backends for Brain policies.

A backend proposes one action token per observation mapping. The
rule-based planner stays the default: a backend is consulted only when
one is attached, and any missing, invalid, or raising proposal falls
back to the rule policy with a counted fallback.

Shipped providers: ``stub`` (deterministic script, protocol pins),
``llamacpp`` (launches and owns a llama-server), and ``openai`` (asks any
OpenAI-compatible server that is already running: llama-server, LM Studio,
Ollama, vLLM). No weights live in this package; the model is always an
external endpoint reached through a bounded-timeout client.
"""
