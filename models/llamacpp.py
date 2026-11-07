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


def build_prompt(observation):
    """Render a compact deterministic action prompt for an observation."""
    legal = list(observation.get("legal", LEGAL))
    base = (
        "Grid task %(task)s. You are at [%(x)s, %(y)s] after %(steps)s steps. "
        "Reply with exactly one action word, nothing else. "
        "Legal actions: %(legal)s."
        % {"task": observation.get("task"), "x": observation.get("x"),
           "y": observation.get("y"), "steps": observation.get("steps"),
           "legal": ", ".join(legal)}
    )
    extras = []
    if observation.get("target") is not None:
        extras.append("Target: %s." % ([int(v) for v in observation.get("target")],))
    if observation.get("items_positions") is not None:
        extras.append("Items: %s." % ([[int(v) for v in c] for c in observation.get("items_positions")],))
    if observation.get("obstacles") is not None:
        extras.append("Obstacles: %s." % ([[int(v) for v in c] for c in observation.get("obstacles")],))
    if "cue" in observation and observation.get("cue") is not None:
        extras.append("Cue: %s." % (observation.get("cue"),))
    if extras:
        return base + " " + " ".join(extras)
    return base


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
                 timeout=60.0, n_predict=24):
        self.server_exe = server_exe
        self.model_path = model_path
        self.port = port
        self.seed = seed
        self.timeout = timeout
        self.n_predict = n_predict
        self._proc = None

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
        rambles without it).
        """
        payload = json.dumps({
            "messages": [{"role": "user",
                          "content": build_prompt(observation)}],
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
