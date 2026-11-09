"""llama.cpp backend: llama-server subprocess plus completion client.

Paths, ports, and seeds are explicit constructor config so runs stay
reproducible; temperature 0 with a fixed seed makes the same rig and
seeds deterministic. Only the Python standard library is used.
Failures raise (the planner counts the fallback); nothing is
swallowed here.
"""

import json
import subprocess
import time
import urllib.request

from models.backend import ModelBackend

LEGAL = ("up", "down", "left", "right", "collect", "wait")

CHARS_PER_TOKEN = 4
RESERVE_TOKENS = 40


def estimate_tokens(text):
    """Stable provider-agnostic estimate: roughly four characters/token.

    Adapted from research-engine/engine/context.py:35.
    """
    return (len(str(text)) + CHARS_PER_TOKEN - 1) // CHARS_PER_TOKEN


def pack(lines, budget):
    """Fit prompt lines into a token budget, keeping the first line.

    Adapted from research-engine/engine/context.py:45. The first line is
    the anchor and is always kept; later lines are dropped from the end
    when the budget is exhausted. Returns ``(kept, omitted, used)``.
    """
    if isinstance(budget, bool) or not isinstance(budget, int) or budget < 1:
        raise ValueError(
            "Why: budget must be a positive int. "
            "Fix: pass max_tokens=120 or another positive int.")
    available = max(budget - RESERVE_TOKENS, 1)
    kept = []
    used = 0
    for index, line in enumerate(lines):
        cost = estimate_tokens(line) + 1
        if index == 0:
            kept.append(line)
            used += cost
            continue
        if used + cost > available:
            break
        kept.append(line)
        used += cost
    omitted = len(lines) - len(kept)
    return kept, omitted, used


def _prompt_lines(observation):
    legal = list(observation.get("legal", LEGAL))
    base = (
        "Grid task %(task)s. You are at [%(x)s, %(y)s] after %(steps)s steps. "
        "Reply with exactly one action word, nothing else. "
        "Legal actions: %(legal)s."
        % {"task": observation.get("task"), "x": observation.get("x"),
           "y": observation.get("y"), "steps": observation.get("steps"),
           "legal": ", ".join(legal)}
    )
    essentials = []
    if observation.get("target") is not None:
        essentials.append("Target: %s." % ([int(v) for v in observation.get("target")],))
    if observation.get("items_positions") is not None:
        essentials.append("Items: %s." % ([[int(v) for v in c] for c in observation.get("items_positions")],))
    if observation.get("obstacles") is not None:
        essentials.append("Obstacles: %s." % ([[int(v) for v in c] for c in observation.get("obstacles")],))
    if "cue" in observation and observation.get("cue") is not None:
        essentials.append("Cue: %s." % (observation.get("cue"),))
    anchor = base
    if essentials:
        anchor += " " + " ".join(essentials)
    lines = [anchor]
    if observation.get("visits") is not None:
        lines.append("Visits: %s." % ([[int(v) for v in e] for e in observation.get("visits")],))
    return lines


def build_prompt(observation, max_tokens=None):
    """Render a compact deterministic action prompt for an observation.

    ``max_tokens=None`` keeps the original single-line prompt exactly.
    With a budget, the first line (task/position/legal) is always kept
    and trailing extras are dropped from the end; the visits line is
    last, so it is the first to go. ``OMITTED:n`` names dropped lines.
    """
    lines = _prompt_lines(observation)
    if max_tokens is None:
        return " ".join(lines)
    kept, omitted, _used = pack(lines, max_tokens)
    prompt = " ".join(kept)
    if omitted:
        prompt += " OMITTED:%d" % omitted
    return prompt


def prompt_stats(observation, max_tokens=None):
    """Return token/omission statistics for one rendered prompt.

    ``within_budget`` reports whether the rendered prompt actually fits the
    requested budget, and ``over_by`` how far it overran. ``pack`` always
    keeps the anchor line, so a budget below the anchor's own cost cannot be
    met; without these fields a caller had no way to tell a met budget from
    an overrun. Both are ``None``/0 when no budget was requested.
    """
    lines = _prompt_lines(observation)
    if max_tokens is None:
        prompt = " ".join(lines)
        return {"tokens": estimate_tokens(prompt), "omitted": 0,
                "used": 0, "lines": len(lines),
                "within_budget": None, "over_by": 0}
    kept, omitted, used = pack(lines, max_tokens)
    prompt = " ".join(kept)
    if omitted:
        prompt += " OMITTED:%d" % omitted
    tokens = estimate_tokens(prompt)
    over_by = max(0, tokens - max_tokens)
    return {"tokens": tokens, "omitted": omitted,
            "used": used, "lines": len(lines),
            "within_budget": over_by == 0, "over_by": over_by}


def parse_action(text):
    """Return the first legal action token in text, else None."""
    if not isinstance(text, str):
        return None
    words = []
    current = ""
    for ch in text.lower():
        if ch.isalpha():
            current += ch
        elif current:
            words.append(current)
            current = ""
    if current:
        words.append(current)
    for word in words:
        if word in LEGAL:
            return word
    return None


class LlamaCppBackend(ModelBackend):
    """Drive a local llama-server for action proposals.

    Server lifecycle is explicit: start_server() launches and waits
    for /health, close() terminates. generate() posts one completion
    and returns the parsed token or None.
    """

    def __init__(self, server_exe, model_path, port=8174, seed=0,
                 timeout=60.0, n_predict=24, prompt_budget=None):
        if prompt_budget is not None:
            if (isinstance(prompt_budget, bool)
                    or not isinstance(prompt_budget, int)
                    or prompt_budget < 1):
                raise ValueError(
                    "Why: prompt_budget must be a positive int or None. "
                    "Fix: pass prompt_budget=120 or None.")
        self.server_exe = server_exe
        self.model_path = model_path
        self.port = port
        self.seed = seed
        self.timeout = timeout
        self.n_predict = n_predict
        self.prompt_budget = prompt_budget
        self._proc = None
        self.last_manifest = None
        self.last_prompt_stats = None

    def base_url(self):
        return "http://127.0.0.1:%d" % self.port

    def start_server(self, wait_seconds=120.0):
        """Launch llama-server and wait until /health reports ok."""
        cmd = [self.server_exe, "-m", self.model_path, "--port",
               str(self.port), "--seed", str(self.seed)]
        self._proc = subprocess.Popen(  # hygiene: allow [popen-wait-timeout] long-lived server with bounded startup poll and bounded terminate-wait-kill in close()
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.time() + wait_seconds
        last = "no response yet"
        while time.time() < deadline:
            if self._proc.poll() is not None:
                raise RuntimeError("llama-server exited during startup")
            try:
                with urllib.request.urlopen(
                        self.base_url() + "/health", timeout=5) as resp:
                    if resp.status == 200:
                        return self.base_url()
                    last = "status %s" % resp.status
            except Exception as exc:
                last = "%s: %s" % (type(exc).__name__, exc)
            time.sleep(1.0)
        self.close()
        raise TimeoutError("llama-server not healthy: %s" % last)

    def generate(self, observation):
        """Post one chat completion; return the parsed token or None.

        The chat endpoint applies the model's own template, which the
        raw completion endpoint skips (an untuned instruct model
        rambles without it). Records self.last_manifest with the
        generation manifest fingerprint for the call.
        """
        prompt = build_prompt(observation, max_tokens=self.prompt_budget)
        self.last_prompt_stats = prompt_stats(observation, self.prompt_budget)
        try:
            from .manifest import manifest_for as _manifest_for
            import os as _os
            _base = _os.path.basename(str(self.model_path))
            self.last_manifest = _manifest_for(
                prompt, observation, model_id=_base, checkpoint=_base,
                sampling={"temperature": 0.0, "seed": self.seed,
                          "n_predict": self.n_predict,
                          "cache_prompt": True})
        except Exception:
            self.last_manifest = None
        payload = json.dumps({
            "messages": [{"role": "user",
                          "content": prompt}],
            "n_predict": self.n_predict,
            "temperature": 0.0,
            "seed": self.seed,
            "cache_prompt": True,
        }).encode("utf-8")
        req = urllib.request.Request(
            self.base_url() + "/v1/chat/completions", data=payload,
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return parse_action(body["choices"][0]["message"]["content"])

    def close(self):
        """Terminate the server process if running, bounded wait."""
        proc, self._proc = self._proc, None
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10.0)
            except subprocess.TimeoutExpired:
                proc.kill()

    def __enter__(self):
        self.start_server()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False
