# Brain state machines — verified inventory

An **implicit state machine** is a set of states encoded in JSON fields,
status strings, verdict words or file presence, plus the moves the code
actually allows between them. Brain had no single place to read them.
`state_machines.py` declares 21 of them as data, and
`python state_machines.py --list` prints the registry. This document is
the written inventory: what each machine is, where it lives, and the gap
a reader should know. No runtime path changed when the registry was
added (ADR-098).

Read-only CLI:

```
python state_machines.py --list              # names + purposes
python state_machines.py --json              # full data
python state_machines.py --machine <name>    # states, transitions, gap
python state_machines.py --machine <name> --from <s> --to <t>
python state_machines.py --machine <name> --check-status <s>
python state_machines.py --check             # declared vs live constants
```

## The machines

| # | Machine | States | Source | Known gap |
|---|---------|--------|--------|-----------|
| 1 | `episode-verdict` | running, done, truncated | `agent._episode_verdict`, `run_task_logged`; `telemetry.write_verdict` | `done` is also set at the step cap; only the verdict separates a completion from a truncation, and a trace cut before the verdict leaves a header with no terminal state. |
| 2 | `world-step` | active, task-complete, energy-exhausted, step-exhausted | `worlds/grid.step` | `done` conflates task completion with energy/step exhaustion and carries no reason. |
| 3 | `model-decision` | pending, accepted, invalid, no-op, no-progress, stall, distrusted, skipped, skipped-progress | `agent.Planner.plan` decision block | Reasons are inline literals in an ordered ladder; no constant declares the vocabulary. |
| 4 | `backend-trust` | trusted, stalled, distrusted | `agent.Planner._backend_distrusted`, `trust_window`, `reset_trust` | Episode-scoped and monotonic; a later reward does not restore trust. |
| 5 | `progress-guard` | watching, streak, distrusted | `agent.Planner._progress_streak`, `progress_skip_after` | Any non-progress outcome resets the streak; an alternating backend never accumulates distrust. |
| 6 | `layout-store` | opening, valid, corrupt, quarantined, fresh | `memory/store.MemoryStore` open/recovery | A recovered store is silently empty; `recovery_notes` is in-memory only and `:memory:` cannot be quarantined. |
| 7 | `layout-recall` | unconsulted, disabled, miss, hit | `agent.Planner._persistent_state`, `bind_recall_source` | A raising source is cached as a miss; `store_reads` increments before the call, so a failed read still counts. |
| 8 | `layout-freshness` | absent, incomplete, legacy-complete, current, mismatched | `agent._layout_complete`, `_remember_layout`; `memory/store` layouts | A NULL legacy row is upgraded only when a complete warm run with a fingerprint reaches it. |
| 9 | `telemetry-chain` | absent, valid, legacy-anchored, corrupt, edited, reordered, broken, unchained | `telemetry/log.verify_chain` | Findings are free-form strings; verification keeps scanning after a defect, so several classes can describe one edit. |
| 10 | `telemetry-anchor` | unanchored, anchored, missing, truncated, mismatch | `telemetry/log.write_anchor`, `verify_chain(anchor_path=)` | The sidecar is mutable and must live outside the tampered log's control. |
| 11 | `anchor-journal` | missing, chained, broken-prev, rewound, truncated | `telemetry/log.append_anchor`, `verify_anchor_journal` | Deleting tail anchors leaves a shorter but internally valid journal unless the latest anchor is known externally. |
| 12 | `merkle-batch` | absent, anchored, proof-valid, truncated, root-mismatch | `telemetry/merkle.py` | The root is a separate witness; membership covers the committed batch, not global order. |
| 13 | `merkle-journal` | missing, chained, rollback-refused, truncated-batch, compacted | `telemetry/merkle.py` journal + compaction | Appends are not locked against compaction, so compaction is offline and single-writer. |
| 14 | `claim-status` | proposed, supported, refuted, inconclusive | `claims.CLAIM_STATUSES`, `ClaimLedger.record` | Status is derived from the last verdict, so a later verdict silently overwrites the status a reader saw. |
| 15 | `verdict-event` | supports, refutes, inconclusive | `claims.VERDICT_STATUSES`, `Verdict` | `inconclusive` is both a verdict event and a claim status; the token alone does not name the level. |
| 16 | `claim-store` | absent, valid, mac-error, corrupt, quarantined, backup-loaded, empty | `claims_store.save_ledger`, `load_ledger`, `verify_ledger_file` | A MAC error deliberately does not quarantine while a checksum defect does, so the two failures recover differently. |
| 17 | `calibration-journal` | absent, live, rotated, archived, corrupt, keyed-refused | `calibration_store.append_forecasts`, `rotate_forecast_journal` | An unkeyed rotation over keyed evidence is refused and leaves the live journal unbounded until a keyed caller rotates it. |
| 18 | `resume-decision` | resume, new, ask | `identity.resume_decision`, `prepare_resume` | A missing digest asks under strict/ask but resumes under `any`; the policy, not only the digests, decides. |
| 19 | `resume-policy` | strict, ask, any | `identity.RESUME_POLICIES`, `normalise_policy` | An unknown policy string silently becomes strict; the caller is not told. |
| 20 | `planner-tracker` | pending, ok, failed, drained | `planner/plan.Planner` | `state()['done']` is true when the cursor passes the last step even if that step failed. |
| 21 | `execution-budget` | inactive, active, exhausted | `budget.ExecutionBudget`, `use_budget`, `spend` | `exceeded` names only the first dimension that tripped and cannot be cleared; wall time is checked only on a spend. |

## How the inventory was verified

Every row was read against the cited source, not inferred from names:

- **Transition tables** are checked for internal consistency by
  `tests/test_state_machines.py` (keys equal states, every target is a
  known state) and exercised through the CLI for every declared and one
  disallowed transition per state.
- **Live vocabularies** for `claim-status`, `verdict-event` and
  `resume-policy` are compared with `claims.CLAIM_STATUSES`,
  `claims.VERDICT_STATUSES` and `identity.RESUME_POLICIES`;
  `python state_machines.py --check` reports `ok` for all three.
- **Behavior is unchanged**: the registry is data-only and its tests do
  not import or mutate the agent loop in a way that runs an episode; the
  full 471-test gate and the cold-start battery are unchanged.

## Deliberately out of scope

These are not state machines: the eval batteries' `mode=` strings (a
parameter, not a lifecycle), telemetry `seq` (shared by action/result and
negative for verdicts, so order rides the chain), and the `PLANNER_POLICY`
digest (a configuration hash, not a state).

Derived verification-result vocabularies are also excluded — for example
`verify_snapshot` findings, `verify_episode_header` findings and
`verify_claim_refs` counts. They describe one read-only check's outcome,
not a durable state a later operation transitions from; the durable
stores they inspect (`telemetry-chain`, `telemetry-anchor`,
`claim-store`, `calibration-journal`) are the machines above.
