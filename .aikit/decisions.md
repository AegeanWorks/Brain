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
