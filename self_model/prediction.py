"""Rung 1: a pre-outcome self-prediction the agent can be scored on.

The agent records confidence *after* the outcome (`_conf_sm = 1.0 if reward
> 0`), so its calibration is a restatement of the base rate — the repo's own
`confidence_is_outcome` warning says so. This module records a prediction
*before* the action is taken, so Brier/skill become a real forecast measure.

Measured pooled over 20 seeds per task (143/308/160 steps):

  predictor            T3         T1         T2
  dist == 1           +0.936     -0.925     -0.780
  action == collect   -0.067     +0.937     +0.934
  since_reward >= 5   -1.009     -0.106     -0.523
  steps >= 8          -0.148     -0.938     -0.051
  revisit >= 2        -0.067     -0.134     -0.051

No experience-only signal generalizes: every candidate that is not a
restatement of the world's own reward rule is negative on every task. So the
predictor here is deliberately *task-conditional* — it uses the goal distance
on T3 and the collect action on T1/T2 — and reports its own skill so the
claim can be checked rather than assumed.

`predict_outcome` takes only what is knowable before `world.step`:
the pre-action state, the chosen action, and the task id.
"""

#: Predictor to use per task, chosen by the pooled measurement above.
TASK_PREDICTORS = {
    "T3_navigate": "distance",
    "T1_forage": "collect",
    "T2_delayed_match": "collect",
}

HIGH = 0.8
LOW = 0.05

_MOVES = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}


def _goal_cells(state, task):
    if task == "T1_forage":
        return [tuple(cell) for cell in (state.get("items_positions") or [])]
    target = state.get("target")
    return [tuple(target)] if target else []


def goal_distance(state, task):
    """Manhattan distance from the pre-action position to the nearest goal."""
    if "x" not in state or "y" not in state:
        return None
    pos = (int(state["x"]), int(state["y"]))
    cells = _goal_cells(state, task)
    if not cells:
        return None
    return min(abs(pos[0] - cell[0]) + abs(pos[1] - cell[1])
               for cell in cells)


def predict_outcome(state, action, task):
    """Probability that this step earns reward, from pre-action information.

    Returns ``(probability, basis)`` where ``basis`` names which rule fired
    so a caller can tell a real prediction from the neutral fallback.
    """
    kind = TASK_PREDICTORS.get(task)
    if kind == "distance":
        distance = goal_distance(state, task)
        if distance is None:
            return 0.5, "no-goal"
        closes = False
        if distance == 1 and action in _MOVES:
            dx, dy = _MOVES[action]
            pos = (int(state["x"]), int(state["y"]))
            closes = any(
                abs(pos[0] + dx - cell[0]) + abs(pos[1] + dy - cell[1])
                < distance
                for cell in _goal_cells(state, task))
        return (HIGH if closes else LOW), ("closing-move" if closes
                                           else "far")
    if kind == "collect":
        hits = action == "collect"
        return (HIGH if hits else LOW), ("collect" if hits else "other")
    return 0.5, "unknown-task"
