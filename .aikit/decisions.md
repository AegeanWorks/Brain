# Decisions

Why this project is built the way it is, oldest first. One entry per decision that changes a
contract, a dependency, a data format or the architecture; IDs are consecutive and never reused.

### ADR-001: Stdlib-only SQLite FTS5 memory, no FAISS
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Stage 2 verified neurocore FAISS dep heavy; cheaper alternative required instrument parity.
- **Decision**: Brain v1 uses SQLite WAL+FTS5 only; FAISS adoption gated on recall@k delta >=5%.
- **Consequences**: Zero third-party deps; vector recall deferred.

### ADR-002: JSONL telemetry with hub_zero ablation op
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Stage 2 required instrument-closed measure separated from substrate.
- **Decision**: Telemetry schema 2 JSONL with fsync-before-exec; ablation ops hub_zero/lesion/shuffle in telemetry/ablate.py; recompute in evals/recompute.py never reads self-report scalars.
- **Consequences**: Ablation runs before any claim; verdict stays UNKNOWN until Stage 4.

### ADR-003: Episode buffers plus persistent substrate
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Agent loop needs deterministic per-step hub sharing; persistent store needs cross-run recall.
- **Decision**: agent.py holds in-memory episode buffers with hub binding; memory/store.py, planner/plan.py, self_model/model.py hold persistent counters; integration via hub + telemetry log.
- **Consequences**: No emergence claim in Stage 3; cross-episode persistence wiring verified by unit tests only.

### ADR-004: Planner reads memory and hub for loop avoidance (negative result)
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Stage 4 calibration showed planner ignored memories (`_ = memories`), limiting cross-module coupling by construction.
- **Decision**: Planner.plan reads hub via read_hub and recent positions from memories; stuck repeats switch to y-first step. Deterministic, rule-based, no new deps.
- **Consequences**: Gate stays 38 OK; T1 pooled phi 0.0226 vs null 0.0106, syn 0.0265 vs null 0.0773 — E1' still FAIL; verdict stays UNKNOWN. No threshold moved.

### ADR-005: Agent loop wired to JSONL telemetry with M/P/S/hub vectors
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: G1/G2 controls showed estimator inputs excluded hub and memory-recall was not causally bound to the measure.
- **Decision**: Agent accepts real substrate and per-step M/P/S/hub vectors into telemetry/log.py via run_task_logged; ablate gains hub_zero_rows/lesion_m/p/s on logged rows; recompute falls back to logged vectors; thresholds in evals/tasks.yaml unchanged.
- **Consequences**: 40 tests OK; recompute parity MATCH; short-run phi at floor with zero deltas; verdict stays UNKNOWN pending n>=1000 calibration.
