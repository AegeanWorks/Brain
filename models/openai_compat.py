"""Talk to any OpenAI-compatible local model server, with no surprises.

Every local runtime a normal person already has — llama.cpp's
``llama-server``, LM Studio, Ollama, vLLM — exposes the same
``/v1/chat/completions`` contract. This module is the one place that speaks
it, so the rest of the app never builds URLs or guesses ports.

Two deliberate choices:

* **No silent fallback.** If nothing answers, the error says which
  addresses were tried and what to start. It never pretends to be a model.
* **Injectable transport.** ``transport(method, url, payload, timeout)`` is
  a parameter, so the client is testable without a socket, a thread or a
  sleep.

Stdlib only.
"""

import json
import os
import time
import urllib.error
import urllib.request

#: Local runtimes people actually install, in the order we probe them.
CANDIDATES = (
    ("http://127.0.0.1:8080", "llama-server"),
    ("http://127.0.0.1:1234", "LM Studio"),
    ("http://127.0.0.1:11434", "Ollama"),
    ("http://127.0.0.1:8000", "vLLM"),
)

#: Env var that wins over discovery (read with getenv, never indexed).
ENDPOINT_ENV = "BRAIN_ENDPOINT"
MODEL_ENV = "BRAIN_MODEL"

DEFAULT_TIMEOUT = 120.0
PROBE_TIMEOUT = 2.0


class EndpointUnavailable(RuntimeError):
    """Raised when no model server answers; the message is user-facing."""


def normalize_endpoint(text):
    """Return ``scheme://host[:port]`` with no trailing slash or ``/v1``.

    Accepts what a person actually pastes: ``localhost:8080``,
    ``http://127.0.0.1:1234/``, ``http://localhost:11434/v1``.
    """
    if not isinstance(text, str) or not text.strip():
        raise EndpointUnavailable(
            "Why: the endpoint is empty. "
            "Fix: pass --endpoint http://127.0.0.1:8080")
    value = text.strip().rstrip("/")
    if "://" not in value:
        value = "http://" + value
    for suffix in ("/v1", "/v1/chat/completions"):
        if value.endswith(suffix):
            value = value[: -len(suffix)]
    return value.rstrip("/")


def url_for(base, path):
    """Join a normalized base URL and a ``/``-prefixed API path."""
    return base + path


def _http_transport(method, url, payload, timeout):
    """Default transport: one JSON request, no retries, bounded wait."""
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers,
                                     method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8", "replace")
    try:
        return json.loads(body) if body else {}
    except json.JSONDecodeError:
        return {"raw": body}


def _explain_failure(base, cause):
    """Turn a transport exception into a message a person can act on."""
    return EndpointUnavailable(
        "Why: no model server answered at %s (%s: %s). "
        "Fix: start one, then rerun - llama-server: "
        "`llama-server -m model.gguf --port 8080`; LM Studio: enable the "
        "local server; Ollama: `ollama serve` and `ollama pull qwen2.5:3b`."
        % (base, type(cause).__name__, cause))


def describe_available():
    """Return the human text listing the usual ways to get a model."""
    return (
        "No local model server answered. Start one of:\n"
        "  llama.cpp   llama-server -m <model.gguf> --port 8080\n"
        "  LM Studio   Developer tab -> Start Server (port 1234)\n"
        "  Ollama      ollama serve   then   ollama pull qwen2.5:3b\n"
        "  vLLM        vllm serve <model> --port 8000\n"
        "Then rerun, or pass --endpoint http://host:port and/or --model <id>.\n"
        "You can still run the offline rule agent: brain.py run T3_navigate")


class OpenAIClient:
    """A minimal chat client for an OpenAI-compatible local server.

    ``transport`` is injectable so tests never open a socket. ``model``
    pins a model id when the server hosts several; otherwise the server
    picks its default.
    """

    def __init__(self, base_url, model=None, timeout=DEFAULT_TIMEOUT,
                 transport=None):
        self.base = normalize_endpoint(base_url)
        self.model = model
        self.timeout = float(timeout)
        self._transport = transport or _http_transport

    # -- probing ---------------------------------------------------------

    def models(self):
        """Return the model ids this server advertises (may be empty)."""
        body = self._request("GET", "/v1/models", None, PROBE_TIMEOUT)
        entries = body.get("data")
        if not isinstance(entries, list):
            return []
        return [str(entry.get("id")) for entry in entries
                if isinstance(entry, dict) and entry.get("id")]

    def is_alive(self):
        """True when the server answers its model list at all."""
        try:
            self.models()
            return True
        except EndpointUnavailable:
            return False

    def identify(self):
        """Return ``(model_id, server_name)`` for a human summary line."""
        try:
            available = self.models()
        except EndpointUnavailable:
            available = []
        chosen = self.model or (available[0] if available else None)
        return chosen, self.base

    # -- chatting --------------------------------------------------------

    def chat(self, messages, temperature=0.2, max_tokens=512):
        """Send ``messages`` and return ``{text, model, seconds}``.

        Raises :class:`EndpointUnavailable` with a start-the-server hint
        when the transport cannot reach the endpoint, and reports an empty
        reply as an error rather than an empty string, because an empty
        bubble looks like a UI bug.
        """
        payload = {
            "messages": list(messages),
            "temperature": float(temperature),
            "max_tokens": int(max_tokens),
            "stream": False,
        }
        if self.model:
            payload["model"] = self.model
        started = time.time()
        body = self._request("POST", "/v1/chat/completions", payload,
                             self.timeout)
        elapsed = time.time() - started
        text = _message_text(body)
        if not text:
            raise EndpointUnavailable(
                "Why: %s returned no text (choices=%r). "
                "Fix: check the model is a chat model, or pass --model."
                % (self.base, body.get("choices")))
        model = body.get("model") or self.model
        return {"text": text, "model": model, "seconds": elapsed,
                "usage": body.get("usage") or {}}

    # -- internals -------------------------------------------------------

    def _request(self, method, path, payload, timeout):
        try:
            return self._transport(method, url_for(self.base, path), payload,
                                   timeout)
        except EndpointUnavailable:
            raise
        except (urllib.error.URLError, OSError, ValueError) as cause:
            raise _explain_failure(self.base, cause)


def _message_text(body):
    """Pull one string out of a chat-completion body, or return ``""``."""
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            return content.strip()
    text = first.get("text")
    return text.strip() if isinstance(text, str) else ""


def resolve(client_factory=None, probe=None, endpoint=None, model=None):
    """Find a live endpoint: explicit argument, env, then local defaults.

    Returns ``(client, source)`` where ``source`` is a human label such as
    ``"--endpoint"``, ``"$BRAIN_ENDPOINT"`` or ``"LM Studio on :1234"``.
    Raises :class:`EndpointUnavailable` with the start-a-server text when
    nothing answers, so the caller never has to invent a message.
    """
    factory = client_factory or (lambda url, model=None: OpenAIClient(url, model=model))
    model = model or os.getenv(MODEL_ENV) or None

    for text, source in ((endpoint, "--endpoint"),
                         (os.getenv(ENDPOINT_ENV), "$%s" % ENDPOINT_ENV)):
        if not text:
            continue
        candidate = factory(text, model)
        # An explicit endpoint is a claim, not proof that a server answers.
        # Probe it the same way discovery probes its candidates, even when
        # no probe was injected (the production path), so a dead address is
        # refused here with an actionable message instead of failing later
        # inside chat() with a generic transport error.
        alive = probe(candidate) if probe is not None else candidate.is_alive()
        if alive:
            return candidate, source
        raise EndpointUnavailable(
            "Why: %s points at %s but nothing answered there. "
            "Fix: correct the address, or omit it to allow discovery."
            % (source, normalize_endpoint(text)))

    for base, name in CANDIDATES:
        candidate = factory(base, model)
        alive = probe(candidate) if probe is not None else candidate.is_alive()
        if alive:
            return candidate, "%s on %s" % (name, base.rsplit(":", 1)[-1])
    raise EndpointUnavailable(describe_available())
