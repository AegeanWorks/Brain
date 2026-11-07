# Brain

[![Built with AIKit](https://img.shields.io/badge/built%20with-AIKit-6f42c1)](https://github.com/AegeanWorks/AIKit)

Deterministic agent substrate with memory planner self-model and integration telemetry plus ablation harness.

## ⚡ 30-Second Cold-Start Quick Reference

- **Runtime Prerequisites**: Python 3.10+ stdlib only, no third-party packages.
- **Canonical Regression Shield Gate**:
  ```bash
  python -m unittest discover -s tests -t .
  ```
- **Cold-Start Recovery Battery**:
  ```bash
  python -m evals.coldstart --capture
  ```
- **Model-Trust Battery**:
  ```bash
  python -m evals.trust
  ```
- **Telemetry Lock Battery**:
  ```bash
  python -m evals.telemetry_lock
  ```
- **Cycle-Escape Battery**:
  ```bash
  python -m evals.escape
  ```

### 🛠️ AIKit Commands (run from the AIKit folder)
| Role | Command |
|---|---|
| Status, task and gates | `python aikit.py status brain` |
| Phase 4: every gate | `python aikit.py check brain` |
| Repair memory and map, then check | `python aikit.py fix brain` |
| Resume an interrupted task | `python aikit.py resume brain` |

## 📦 What's Inside

```text
brain/
├── .gitignore
├── COMMERCIAL.md
├── CYCLES.md                   <- append-only improvement-cycle ledger
├── LICENSE
├── LICENSES/
├── REUSE.toml
├── README.md
├── inventory.py
├── demo.py
├── agent.py                  <- rule-based perceive-plan-act-observe loop + hub
├── models/                   <- swappable small-model backends (seam + llama.cpp)
├── memory/                   <- SQLite FTS5 store + per-task layout anchors (store.py)
├── planner/                  <- explicit steps + recover (plan.py)
├── self_model/               <- budget/error/confidence counters (model.py)
├── worlds/                   <- deterministic 8x8 fixed-step tasks T1-T3 (grid.py)
├── telemetry/                <- JSONL append-only (log.py) + ablation ops (ablate.py)
├── evals/                    <- estimators, recompute, coldstart/trust/escape batteries
├── tests/                    <- unittest gate, tempdir only
└── .aikit/
```

## 🧊 Cold-Start Recovery Contract

A warm run stores one full initial state per `(task, seed)` in the additive
`layouts` table (first write wins). Only task-complete states are written: a
cold-first run cannot poison the row, and a later complete run replaces an
incomplete one. A cold run whose observations omit goal fields reads that
layout once per episode; the planner probe records `store_reads` plus the
fields supplied by `state`, `memory`, or `persistent`, and the same fields
reach the model-seam observation. Cutting the source with
`Planner.bind_recall_source(None)` restores the store-blind behavior; cutting
the completeness gate restores cold-first poisoning. Property and trace share
one ablation per scenario.

## 🤝 Model-Seam Trust Contract

A legal backend proposal is trusted while fewer than 20 consecutive steps
have passed without reward. Once that stall window is reached, a proposal
that differs from the rule action is rejected (counted in `fallbacks`) and
the backend stays match-only for the rest of the episode. Independently, a
no-op proposal (`wait`, `collect` before a collectable, or a direction blocked
by the boundary/obstacle) is rejected immediately whenever the rule has a
productive action; `noop_guard=False` removes that guard. `trust_window=None`
plus `noop_guard=False` is the raw control. Each step's action record carries
`proposed/rule/steps_since_reward/distrusted/accepted/reason`, and the hub
carries `steps_since_reward`; rule-only runs and good-backend replays keep
their exact actions and zero fallbacks.

## 🔁 Repeated-Position Cycle Escape

For obstacle layouts with two or more blockers, the planner counts how
many times the current cell appears in the full episode history. On the
second visit it takes one deterministic BFS step toward the target
(neighbor order `up/down/left/right`), instead of following the local
viability/pool order into the same loop. The action record's `probe`
gains `cycle_escape` with `position/visits/distance/action`. The gate is
memory-backed: `Planner(...).plan(state, None)` cannot see a repeat and
the old 200-step loop returns; `cycle_escape=False` is the executable
ablation. Single-blocker and open-field paths keep their existing
rules. `python -m evals.escape` shows both recovered three-blocker
layouts, the escape-off and memory-blind controls, and the unchanged
first prompt hash.

## 🧾 Verdict Facts

A logged run is `done` only when it ended before the step budget. A run that
consumes the full budget is `truncated` even though the world's `done` flag is
set by the cap; the verdict reason always carries `steps` and `reward`, so a
capped run cannot read back as a success.

## 🔗 Multi-Writer Telemetry

Each JSONL append holds an advisory lock file from the head read through the
durable write, so concurrent writers form one hash chain instead of linking to
the same stale head. A lock older than 30 seconds is treated as a crashed
writer and broken atomically; a bounded timeout raises instead of writing
unprotected. `python -m evals.telemetry_lock` shows the locked chain and
`--ablate` reproduces the broken pre-fix chain.

## 📜 License

Free for personal use under the Aegean License 1.1 (AL-1.1); see [LICENSE](LICENSE). Any commercial use needs the Aegean Commercial License 1.0 (ACL-1.0); see [COMMERCIAL.md](COMMERCIAL.md).
