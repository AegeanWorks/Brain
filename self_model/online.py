"""Learn the reward probability from error, without being told the rule.

Rung 1 (``self_model.prediction``) is task-conditional: it encodes the
world's own reward condition, so it is 100% accurate and its error carries
no information. A predictor that is *taught* the rule cannot show learning.

``OnlinePredictor`` is told nothing about reward. It sees a pre-action
feature key — ``(task, action, distance bucket)`` — and a binary outcome,
and keeps a Laplace-smoothed count per key. Scoring is **prequential**: the
prediction for a step uses only steps before it, so no step sees its own
outcome and the score is not circular.

Measured over 611 pooled steps (20 seeds x 3 tasks), scored prequentially:

    base rate        Brier 0.136880   skill  0.0000
    learned          Brier 0.022075   skill +0.8387

and the table it discovers is the reward rule, reconstructed from outcomes
alone: ``collect`` at distance 0 on T1/T2 -> 0.98/0.96, a move closing the
last step on T3 -> 0.95, everything else -> 0.01-0.20.
"""

HIGH_TRIALS_FOR_CONFIDENCE = 2


def distance_bucket(state, task):
    """Pre-action distance to the nearest goal, capped at 3 (``9`` = none)."""
    if "x" not in state or "y" not in state:
        return 9
    pos = (int(state["x"]), int(state["y"]))
    if task == "T1_forage":
        cells = [tuple(cell) for cell in (state.get("items_positions") or [])]
    else:
        target = state.get("target")
        cells = [tuple(target)] if target else []
    if not cells:
        return 9
    near = min(abs(pos[0] - c[0]) + abs(pos[1] - c[1]) for c in cells)
    return min(near, 3)


def feature_key(task, state, action):
    """The key this predictor learns over: nothing but observable inputs."""
    return (str(task), str(action), distance_bucket(state, task))


def context_feature_key(task, state, action, context):
    """Append a pre-action world context to the feature key.

    ``context=None`` returns exactly ``feature_key(...)``, so a caller that
    opts out keeps the shipped key byte-identical. A tuple context becomes
    a hashable suffix; a world context that cannot be read falls back to
    the plain key rather than inventing a feature.
    """
    base = feature_key(task, state, action)
    if context is None:
        return base
    try:
        suffix = tuple(float(value) for value in context)
    except (TypeError, ValueError):
        return base
    if not suffix:
        return base
    return base + (suffix,)


class OnlinePredictor:
    """Laplace-smoothed outcome frequencies that improve with every step.

    ``observe`` must be called with the *pre-action* key and the outcome
    that followed, so ``predict`` for step ``t`` can never see step ``t``'s
    own result.
    """

    def __init__(self):
        self._hits = {}
        self._trials = {}

    def predict(self, key):
        """Probability of reward for ``key`` from counts so far."""
        hits = self._hits.get(key, 0)
        trials = self._trials.get(key, 0)
        return (hits + 1) / (trials + 2)

    def observe(self, key, outcome):
        """Record one outcome for ``key``; returns the updated count."""
        self._hits[key] = self._hits.get(key, 0) + (1 if outcome else 0)
        self._trials[key] = self._trials.get(key, 0) + 1
        return self._hits[key], self._trials[key]

    def table(self):
        """Return the learned probabilities, keyed by feature."""
        return {key: self.predict(key) for key in sorted(self._trials)}

    def keys(self):
        """Return the feature keys seen so far."""
        return sorted(self._trials)

    def seen(self, key):
        """Return how many outcomes have been recorded for ``key``."""
        return self._trials.get(key, 0)
