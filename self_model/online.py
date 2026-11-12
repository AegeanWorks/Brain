"""Learn the reward probability from error, without being told the rule.

Rung 1 (``self_model.prediction``) is task-conditional: it encodes the
world's own reward condition, so it is 100% accurate and its error carries
no information. A predictor that is *taught* the rule cannot show learning.

``OnlinePredictor`` is told nothing about reward. It sees a pre-action
feature key â€” ``(task, action, distance bucket)`` â€” and a binary outcome,
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


def _logit(hits, trials):
    """Laplace-smoothed log-odds of one component."""
    import math

    return math.log((hits + 1.0) / (trials - hits + 1.0))


class AdditivePredictor:
    """A predictor that adds per-feature evidence instead of memorising a key.

    ``OnlinePredictor`` learns one probability per complete key, so it needs
    one exposure per joint context. This class is the natural alternative an
    engineer reaches for: sum the evidence each *part* of the key carries.
    ``predict`` takes the same key shape as ``context_feature_key`` â€” the
    tuple ``(task, action, bucket, context)`` â€” decomposes the context into
    one component per value plus a ``(task, action, bucket)`` component, and
    returns ``sigmoid(sum of component log-odds)``.

    It cannot represent an XOR: each component is symmetric over the two
    outcomes, so the summed evidence is the same for both actions and the
    model predicts 0.5. That is the point â€” the interaction has to be in the
    representation, not in the number of features.
    """

    def __init__(self):
        self._hits = {}
        self._trials = {}

    def _components(self, key):
        parts = [key[:3]]
        if len(key) > 3 and isinstance(key[3], tuple):
            for index, value in enumerate(key[3]):
                parts.append((key[1], "f%d" % index, value))
        return parts

    def predict(self, key):
        import math

        total = 0.0
        for component in self._components(key):
            total += _logit(self._hits.get(component, 0),
                            self._trials.get(component, 0))
        return 1.0 / (1.0 + math.exp(-total))

    def observe(self, key, outcome):
        for component in self._components(key):
            self._hits[component] = self._hits.get(component, 0) + (1 if outcome else 0)
            self._trials[component] = self._trials.get(component, 0) + 1
        return self.seen(key)

    def table(self):
        return {key: self.predict(key) for key in sorted(self._trials)}

    def keys(self):
        return sorted(self._trials)

    def seen(self, key):
        return sum(self._trials.get(component, 0)
                   for component in self._components(key))


#: Fixed learning rate and epoch count, so the factored learner is
#: deterministic and cheap enough for the unit tier.
FACTORED_LR = 0.5
FACTORED_EPOCHS = 4


def quadratic_features(context, mode="raw"):
    """Return ``[1, c0, c1, ..., c0*c1, ...]`` for a context tuple.

    ``mode="parity"`` reduces every value to ``value % 2`` before building
    the terms, so the feature map is invariant to the value's magnitude. A
    rule defined on parity then transfers to values the learner never saw;
    ``mode="raw"`` keeps the shipped scale-sensitive map.
    """
    if mode not in ("raw", "parity"):
        raise ValueError(
            "Why: mode must be raw or parity. "
            "Fix: pass mode='raw'.")
    values = [float(value) for value in context]
    if mode == "parity":
        values = [float(int(value) % 2) for value in values]
    features = [1.0] + values
    for first in range(len(values)):
        for second in range(first + 1, len(values)):
            features.append(values[first] * values[second])
    return features


def _sigmoid(value):
    import math

    if value >= 0:
        return 1.0 / (1.0 + math.exp(-value))
    scaled = math.exp(value)
    return scaled / (1.0 + scaled)


class FactoredPredictor:
    """A logistic model on quadratic features of the learned key.

    ``AdditivePredictor`` sums independent evidence, so it cannot fit XOR.
    ``OnlinePredictor`` fits XOR but only for a joint key it has seen. This
    class keeps one weight vector per action over ``[1, context, pairwise
    products]`` and fits it by gradient descent on log loss. A product term
    is what XOR needs: for bits, ``a XOR b == a + b - 2ab``.

    It is told the feature *shape*, not the rule, and learns the weights
    from outcomes. Fitting needs the full joint coverage: with only three of
    the four quadrants the weights are underdetermined and gradient descent
    extrapolates the missing quadrant into the majority class.

    ``feature_mode="parity"`` replaces each context value with its parity
    before the terms are built, so a rule defined on parity transfers to
    value ranges the learner never saw. Keys without a context collapse to
    the bias, so the shipped key shape still works.
    """

    def __init__(self, learning_rate=FACTORED_LR, epochs=FACTORED_EPOCHS,
                 feature_mode="raw"):
        if feature_mode not in ("raw", "parity"):
            raise ValueError(
                "Why: feature_mode must be raw or parity. "
                "Fix: pass feature_mode='raw'.")
        self._lr = float(learning_rate)
        self._epochs = max(1, int(epochs))
        self._mode = feature_mode
        self._weights = {}
        self._counts = {}
        self._pending = []

    def _context(self, key):
        if len(key) < 4 or not isinstance(key[3], tuple):
            return ()
        return tuple(key[3])

    def _features(self, key):
        context = self._context(key)
        return quadratic_features(context, self._mode) if context else [1.0]

    def _weights_for(self, action, width):
        weights = self._weights.get(action)
        if weights is None or len(weights) != width:
            weights = [0.0] * width
            self._weights[action] = weights
        return weights

    def predict(self, key):
        """Probability of reward for this action and context."""
        features = self._features(key)
        weights = self._weights.get(key[1])
        if weights is None or len(weights) != len(features):
            return 0.5
        return _sigmoid(sum(w * f for w, f in zip(weights, features)))

    def observe(self, key, outcome):
        """Record one outcome and refit once a batch has accumulated."""
        self._pending.append((key, 1.0 if outcome else 0.0))
        self._counts[key] = self._counts.get(key, 0) + 1
        if len(self._pending) >= 32:
            self.fit()
        return self._counts[key]

    def fit(self):
        """Refit on the pending batch with deterministic gradient descent."""
        batch = self._pending
        if not batch:
            return 0
        for _epoch in range(self._epochs):
            for key, outcome in batch:
                features = self._features(key)
                weights = self._weights_for(key[1], len(features))
                predicted = _sigmoid(sum(w * f for w, f in zip(weights, features)))
                error = outcome - predicted
                for index, value in enumerate(features):
                    weights[index] += self._lr * error * value
        self._pending = []
        return len(batch)

    def flush(self):
        """Fit any observations still buffered."""
        return self.fit()

    def table(self):
        return {key: self.predict(key) for key in sorted(self._counts)}

    def keys(self):
        return sorted(self._counts)

    def seen(self, key):
        return self._counts.get(key, 0)
