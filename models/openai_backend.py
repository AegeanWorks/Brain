"""Drive any OpenAI-compatible local server as an action backend.

``LlamaCppBackend`` owns its server: you must pass a binary and a GGUF.
That is fine for a pin, but it means the agent could not use the server a
person already has running. This backend closes that gap: it asks the same
``/v1/chat/completions`` endpoint the chat CLI discovered, so one local
runtime serves both the conversation and the agent.

Contract notes:

* ``generate`` returns one legal token, or ``None`` when the model said
  something unusable. ``None`` is a fallback, not a crash: the planner
  counts it and continues with the rule action.
* A server that is not running raises ``EndpointUnavailable`` with the
  start-a-server text, on the first call, not at construction. Construction
  must stay cheap so ``run_agent --help`` and the registry stay fast.
* ``identity`` is derived from the pinned model id, never the class name,
  so a rename cannot invalidate historical run headers.
"""

from models.backend import ModelBackend
from models.llamacpp import build_prompt, parse_action, prompt_stats
from models.manifest import manifest_for
from models.openai_compat import OpenAIClient, resolve

#: Token budget for one action proposal. An action is one word, so this is
#: generous and keeps a chatty model from spending the step budget.
ACTION_TOKENS = 8


class OpenAIBackend(ModelBackend):
    """Propose one action token through an OpenAI-compatible endpoint."""

    def __init__(self, client=None, endpoint=None, model=None,
                 max_tokens=ACTION_TOKENS, prompt_budget=None, seed=0):
        if client is not None and (endpoint or model):
            raise ValueError(
                "Why: pass either a ready client or an endpoint/model, not both. "
                "Fix: OpenAIBackend(client=...) or OpenAIBackend(endpoint=...).")
        if prompt_budget is not None and (isinstance(prompt_budget, bool)
                                          or not isinstance(prompt_budget, int)
                                          or prompt_budget < 1):
            raise ValueError(
                "Why: prompt_budget must be a positive int or None. "
                "Fix: pass prompt_budget=120 or None.")
        self._client = client
        self._endpoint = endpoint
        self._model = model
        self._max_tokens = int(max_tokens)
        self._prompt_budget = prompt_budget
        self._seed = int(seed)
        self.last_manifest = None
        self.last_prompt_stats = None

    # -- seam ------------------------------------------------------------

    def identity(self):
        """Stable pin: provider plus the pinned model id (never the class)."""
        return "openai:%s" % (self._model or "auto")

    def client(self):
        """Return the client, resolving a local endpoint on first use.

        Resolution also pins the served model id so ``identity()`` reports
        what answered rather than the word ``auto``. Nothing touches the
        network at construction, which keeps ``--help`` and the registry
        cheap.
        """
        if self._client is None:
            self._client, _source = resolve(endpoint=self._endpoint,
                                            model=self._model)
            if not self._model:
                served, _base = self._client.identify()
                self._model = served
        return self._client

    def generate(self, observation):
        """Ask for one action; return a legal token or ``None``."""
        client = self.client()
        prompt = build_prompt(observation, max_tokens=self._prompt_budget)
        self.last_prompt_stats = prompt_stats(observation, self._prompt_budget)
        model_id = getattr(client, "model", None) or self._model or "auto"
        self.last_manifest = manifest_for(
            prompt, observation, model_id=model_id, checkpoint=model_id,
            sampling={"temperature": 0.0, "seed": self._seed,
                      "max_tokens": self._max_tokens})
        result = client.chat([{"role": "user", "content": prompt}],
                             temperature=0.0, max_tokens=self._max_tokens)
        return parse_action(result.get("text"))


def build_openai(**config):
    """Registry factory: build an ``OpenAIBackend`` from config keywords."""
    return OpenAIBackend(**config)
