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
- **Manifest-Binding Battery**:
  ```bash
  python -m evals.manifest_binding
  ```
- **Dead-Pool Guard Battery**:
  ```bash
  python -m evals.dead_pool
  ```
- **Chain-Anchor Battery**:
  ```bash
  python -m evals.chain_anchor
  ```
- **Anchor-Journal Battery**:
  ```bash
  python -m evals.anchor_journal
  ```
- **Keyed Telemetry Battery**:
  ```bash
  python -m evals.telemetry_mac
  ```
- **Prompt-Budget Battery**:
  ```bash
  python -m evals.prompt_budget
  ```
- **Merkle-Anchor Battery**:
  ```bash
  python -m evals.merkle_anchor
  ```
- **Execution-Budget Battery**:
  ```bash
  python -m evals.execution_budget
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
├── evals/                    <- estimators, recompute, coldstart/trust/escape/manifest/dead-pool/chain-anchor/anchor-journal/keyed-telemetry/prompt-budget/merkle-anchor/execution-budget batteries
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
the backend stays match-only for the rest of the episode. Match-only is
also call-free: the planner stops calling the backend because only the
rule action can be accepted. Independently, a no-op proposal (`wait`,
`collect` before a collectable, or a direction blocked by the
boundary/obstacle) is rejected immediately whenever the rule has a
productive action; `noop_guard=False` removes that guard.
`skip_after_distrust=False` (battery `--no-skip`) restores the redundant
calls for the cost ablation. `trust_window=None` plus `noop_guard=False`
is the raw control. Each step's action record carries
`proposed/rule/steps_since_reward/distrusted/accepted/reason/skipped`;
`reason` is `stall` only on the triggering step, then `distrusted` (call
kept) or `skipped` (call omitted). Rule-only runs and good-backend
replays keep their exact actions and zero fallbacks.

## 🔗 Model-Manifest Binding

A backend that exposes `last_manifest` (model id, checkpoint label,
prompt, observation, sampling) has its manifest SHA-256 copied into
every `model_decision` as `model_manifest_sha256`. The trace therefore
binds each action to the exact generation input, and a same-named
checkpoint swap changes the hash while the action trace stays
identical. A raising call records `null` instead of leaking a stale
manifest. `probe_manifest=False` removes the readout as the executable
ablation. Weights never enter the repo: the manifest carries labels and
hashes only. `python -m evals.manifest_binding` shows intact (coverage
1.0), probe-off (coverage 0.0) and checkpoint A/B (different hashes,
same actions).

## 🧭 Two-Blocker Dead-Pool Guard

For exactly two blockers, the planner compares BFS distance to the
target for the live and dead goal candidates before ordering the pool.
When the best live candidate is at least as close as the best dead one,
dead goal steps are dropped; the action record's `probe` gains
`dead_pool` with `position/excluded/live_distance/dead_distance`.
`dead_pool_filter=False` restores the old pool ordering for the
ablation. Three-blocker and single-blocker paths keep their existing
ordering, so their golden paths stay byte-identical. `python -m
evals.dead_pool` shows the `(7,5)` recovery (18 -> 16) and the ablation.

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

## 🧷 Terminal Telemetry Anchor

A run can write a separate `.anchor` sidecar with the final head digest
and record count via `Telemetry.write_anchor()`. Anchored verification
compares both: a shorter log reports
`truncated-tail:<count><<anchor_count>`, a different head/count reports
`anchor-mismatch`, and a missing witness reports `missing-anchor`.
Without the anchor, a truncated prefix remains internally valid; the
anchor is a separate witness and must be kept outside the tampered
log's control. `python -m evals.chain_anchor` shows intact (pass),
truncated (detected) and anchor-off (the old exposure). The sidecar
contains hashes and counts only and is never committed.

`Telemetry.write_anchor_journal()` appends the same head/count to a
`.anchors` JSONL journal where each anchor's `prev` links to the
previous anchor hash. `verify_anchor_journal()` checks every schema,
hash and prev link; `verify_chain(path, journal_path=...)` compares the
log with the latest anchor. A deleted middle anchor, a rewound seq or a
truncated log is named; deleting tail anchors still yields a shorter
valid journal unless the latest anchor is known externally. `python -m
evals.anchor_journal` shows the intact and truncated cases. The journal
is a separate, non-committed witness.

## 🔐 Keyed Telemetry (HMAC)

`Telemetry(path, hmac_key=bytes)` adds a per-record HMAC-SHA256 `mac`.
The digest excludes `mac`; the MAC covers the canonical record including
its digest, so a payload edit that recomputes the digest still fails the
MAC. `verify_chain(path, hmac_key=...)` reports `missing-mac:<index>` or
`bad-mac:<index>`. Without a key, records and bytes are unchanged; a
keyed verifier rejects an unkeyed log, and an unkeyed verifier cannot
check the MAC. Keys come from a secret store or environment, never from
the repository. `python -m evals.telemetry_mac` shows correct key,
wrong key, missing MAC, recomputed-digest tamper and unkeyed parity.

## 🎚️ Prompt Token Budget

`build_prompt(observation, max_tokens=None)` uses the research-engine
`estimate_tokens`/`pack` helper: roughly four characters per token, the
anchor line always kept, and trailing lines dropped from the end. The
anchor carries the task, position, legal actions, target, items,
obstacles and cue; the visits line is last, so it is dropped first and
`OMITTED:n` names the omission. `max_tokens=None` keeps the original
single-line prompt byte-identical. `prompt_stats` returns
`tokens/omitted/lines`, and `LlamaCppBackend(prompt_budget=...)` applies
the budget and records `last_prompt_stats`; the manifest binds the
capped prompt. `python -m evals.prompt_budget` shows uncapped 63 /
budgeted 52 tokens with 13 omitted visit lines on T3:15 while the rule
actions, steps and reward stay identical.

## 🌿 Merkle Batch Anchors

`Telemetry.write_merkle_anchor(batch_size=64)` commits the last N record
digests to a separate `.merkle` sidecar with `start/end/count/root`.
`verify_merkle_anchor` checks the batch range and root;
`merkle_proof_for_record` returns a detached O(log n) inclusion proof
and `verify_merkle_proof` validates it. Leaf and node hashes are
domain-separated, an odd node is promoted rather than duplicated, and
an empty tree has a defined root. The anchor is a separate witness for
batch membership; run `verify_chain` separately for order/authorship.
`python -m evals.merkle_anchor` shows the intact 8-record batch
(12–20), a 3-sibling proof for record 15, and truncation/tamper
findings.

## 🧮 Execution Budgets

`budget_from_limits({...})` builds an `ExecutionBudget` with
`max_steps`, `max_llm_calls`, `max_tokens` and `max_seconds`.
`Agent.run(..., budget=...)` installs it through a context variable;
the loop spends one step before each action, the planner spends one
LLM call before each backend call and prompt tokens after it, and the
budget checks wall time on every spend. A tight limit raises
`BudgetExceeded(kind, limit, used)` naming the dimension, limit and
attempted usage; a generous budget leaves actions byte-identical, and
`budget=None` is a no-op. `python -m evals.execution_budget` shows the
generous 13-step/1.0 run and the step/LLM/token/time caps.

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
