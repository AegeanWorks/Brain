# Brain state-machine proposals

Proposals to turn the implicit lifecycles in
`.aikit/state_machines.md` into explicit, verified data without changing
behavior. Each is scored for user experience (UX), developer experience
(DX) and agent/AI experience (AX), and carries the verification that
decided it. Only proposals that passed are implemented.

| ID | Proposal | UX | DX | AX | Risk | Verdict |
|----|----------|----|----|----|------|---------|
| P1 | Declare all 21 machines in `state_machines.py` with a read-only CLI | Med | High | High | None | **PASS — implemented** |
| P2 | `--check` compares declared states with live product constants | Low | Med | High | None | **PASS — implemented** |
| P3 | Replace `model-decision` reason literals with named constants | Low | Med | High | Low | Deferred |
| P4 | Make the world `done` flag carry a reason | Med | High | High | High | Rejected |
| P5 | Replace telemetry finding strings with structured codes | Low | Med | Med | High | Rejected |
| P6 | Expose `planner-tracker.state()['done']` as `all_ok` | Low | Med | Med | Low | Deferred |

## P1 — explicit registry and read-only CLI (PASS, implemented)

- **Change**: `state_machines.py` declares 21 `Machine` records (name,
  purpose, states, transitions, source, gap). Modes: `--list`, `--json`,
  `--machine`, `--from/--to`, `--check-status`. Exit 0 success, 1 a
  refused transition/unknown status, 2 misuse; `--help` exits 0 and
  writes nothing.
- **Why it elevates**: a developer can see a lifecycle without reading
  four modules (DX); an agent can query states and check a transition
  before acting instead of guessing from strings (AX); a user reading
  docs sees the same names the trace uses (UX).
- **Verification**: `tests/test_state_machines.py` six tests — internal
  consistency, every machine renders and every state is known, every
  declared transition is allowed and one disallowed transition per state
  is refused, JSON/list shape, misuse exit 2, live-vocabulary match.
- **Ablation**: removing the module makes the test file unimportable and
  the CLI absent; no product path references it, so behavior is
  identical with or without it.

## P2 — live-vocabulary drift check (PASS, implemented)

- **Change**: `--check` lazily imports `claims` and `identity` and
  compares `claim-status`/`verdict-event`/`resume-policy` states with
  `CLAIM_STATUSES`, `VERDICT_STATUSES` and `RESUME_POLICIES`.
- **Why it elevates**: the registry cannot silently drift from the code
  it documents; an agent can run one command to detect a mismatch (AX),
  and a contributor gets a precise failure instead of stale docs (DX).
- **Verification**: `python state_machines.py --check` prints three `ok`
  rows and exits 0; the same call is asserted in the test suite.

## P3 — reason constants for `model-decision` (deferred)

- **Idea**: add `DECISION_REASONS` to `agent.py` and use the constants in
  the reason ladder so the registry can `--check` it.
- **Why deferred**: it touches the hot planning path for no behavioral
  gain, there is no failing eval today, and the risk/benefit does not
  justify editing shipped decision code in a documentation cycle. It is
  the natural next increment once a behavior change needs those reasons.

## P4 — world `done` reason (rejected)

- **Idea**: return `(state, reward, done, reason)` or add a `done_reason`
  key so the world names completion vs cap.
- **Why rejected**: it changes the state dict schema and every golden
  action/state pin, and `_episode_verdict` already separates the two for
  logged runs. The gap is recorded, not silently rewritten.

## P5 — structured telemetry findings (rejected)

- **Idea**: replace `edited-record:3` strings with `{code, detail}`.
- **Why rejected**: findings are compared verbatim in many tests and
  documented in the README; changing them would break the evidence pins
  for no measured gain. The finding vocabulary is stable enough to
  document in the registry instead.

## P6 — `planner-tracker` done vs all-ok (deferred)

- **Idea**: add `all_ok` to `state()` so `done` is not mistaken for
  success.
- **Why deferred**: the tracker is unit-only in production today; adding
  a field is safe but has no consumer. Recorded as the gap in the
  registry and left for the cycle that wires the tracker into a loop.

## Verification summary

- `python -m unittest tests.test_state_machines -v` -> 6 OK.
- `python state_machines.py --list` -> 21 machines.
- `python state_machines.py --check` -> 3/3 `ok`, exit 0.
- `python -m unittest discover -s tests -t .` -> 471 OK.
- `python aikit.py check brain` -> 5/5 gates.
- No benchmark seed, step count, reward, trace, `policy_digest` or
  evidence pin moved.
