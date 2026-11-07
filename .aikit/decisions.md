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

### ADR-006: Persistent outcome accounting with explicit substrate error counters
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Agent.run recorded persistent SelfModel ok=True on every step, so S[0] (errors) was constant zero with zero variance; six `except Exception: pass` blocks hid substrate failures and failed the hygiene gate (4/5).
- **Decision**: Record persistent ok True only when step reward is positive (reward > 0.0); unrewarded steps record ok False, so error_rate is the fraction of unrewarded steps. Each persistent-update failure path increments substrate_errors() by module key instead of bare pass; the loop still never raises from these paths. Test-cleanup swallows carry scoped `hygiene: allow [silent-except]` markers.
- **Consequences**: 43 tests OK; aikit check 5/5; S carries reward-timing variance; phi remains at floor and syn is independent of S (lesion_s delta 0.0), so no emergence claim — verdict stays UNKNOWN.

### ADR-007: Dead-end-entry lookahead with least-visited tie-break in planner
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: T3 seed 15 took 15 steps vs 13 optimal: x-first ordering walked into column x=6 blocked at (6,1) and oscillated (5,0)<->(6,0) before the stuck backstop fired. T1 ordering audit showed nearest-greedy equals optimal on all 30 seeds (no headroom there — dead end).
- **Decision**: _step_toward prefers distance-reducing candidates that keep a free one-step exit toward the goal (goal cell trivially viable), then least-visited cells from planner memory, with stable x-first/fallback order breaking remaining ties. No new deps; deterministic.
- **Consequences**: 46 tests OK; aikit check 5/5; T3 seed 15 15->13, 30-seed totals T1 466 / T2 240 / T3 219->217 with all other seeds byte-identical; blind-memory ablation truncates seed 65 at 200 steps with zero reward (memory coupling proven); seed 65 residual detour 8 vs 6 remains as known 2-ply-trap boundary.

### ADR-008: Two-step exit lookahead in planner viability check
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Cycle 2 left T3 seed 65 (target [3,3], obstacle [3,2]) at 8 steps vs 6 optimal: 1-step lookahead entered (3,0)->(3,1), a cul-de-sac whose only exit is blocked. A 100-seed scan also showed the depth-1 rule plus visits was the only guard on trap seeds.
- **Decision**: _has_exit checks two steps ahead (candidate exit must itself have a free exit or be the goal; depth bounds recursion, branching <= 2). Least-visited tie-break retained: without it seed 74 cycles to the 200-step cap with zero reward.
- **Consequences**: 47 tests OK; aikit check 5/5; T3 seed 65 8->6 (optimal); zero detours across T3 seeds 0-99 (total 683 vs 874 memory-blind, a +191 gap); blind-memory ablation moved to seed 74 (intact 9 vs blind 200/zero-reward).

### ADR-009: Optimal-tour first pick for forage item ordering
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Cycle 2 audited only seeds 0-29 (greedy==optimal throughout) and closed ordering as a dead end. A cycle-4 100-seed audit found 3 greedy traps: seeds 71/74/78 took 18/14/20 steps vs 16/12/18 optimal (+2 each).
- **Decision**: Planner picks the first cell of the shortest Manhattan tour over remaining items (exhaustive permutations, deterministic: cells sorted, first strictly-shortest wins) instead of nearest-first. Removes the now-unused _nearest helper.
- **Consequences**: 49 tests OK; aikit check 5/5; T1 seeds 71/74/78 at optimal (16/12/18), 100-seed T1 total 1587->1581 with all other 97 seeds byte-identical; T2/T3 untouched.

### ADR-010: Remove the inert stuck-override backstop from the planner
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: ADR-004 added a stuck detector (position repeated >=2 in recent memories forces one y-first step). After cycles 2-3, 2-ply lookahead plus least-visited ordering handles all traps; the override fired 238 times in 3064 plan calls without changing any outcome.
- **Decision**: Delete the stuck computation and the y-first override branch in _toward. positions and visit counts stay: visit ordering remains load-bearing (seed-74 ablation). T2 delayed-match wait rule stays: it is task-contract semantics, unreachable today (min target distance 7 > 2) but falsifiable by layout change.
- **Consequences**: 49 tests OK; aikit check 5/5; -6 lines; 100-seed totals per task byte-identical (T1 1581, T2 800, T3 683), all runs complete.

### ADR-011: Quarantine-and-reopen recovery for corrupt store files
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: MemoryStore opened a corrupt file into DatabaseError at first execute and leaked the connection handle (Windows tempdir cleanup then failed with PermissionError). PRINCIPLE-013 requires corrupt -> quarantine for state files.
- **Decision**: Open validates via schema setup plus PRAGMA quick_check; on sqlite3.DatabaseError the failed connection is closed, the file (plus WAL sidecars) is moved to path + ".corrupt" (numbered on collision), and a fresh store opens. recovery_notes() exposes the log, empty on clean opens.
- **Consequences**: 54 tests OK; aikit check 5/5; corrupt fixture recovery 0/1 -> 1/1 with byte-identical quarantine preserved; no behavior change on healthy files.

### ADR-012: Swappable small-model backend seam (llama.cpp first)
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Running a small model against Brain must not fuse the repo to one runtime: llama.cpp now, other providers later. The rule planner stays the default and the measured baseline.
- **Decision**: New models/ package with ModelBackend.generate(observation) interface; Planner accepts an optional backend and falls back to the rule policy (counted in fallbacks) on missing, invalid, or raising proposals. LlamaCppBackend lands separately once the binary and GGUF weights are fetched; providers never enter the repo (user-local cache only).
- **Consequences**: Seam + StubBackend + 3 protocol tests pinned; backend None path byte-identical to the rule tree.

### ADR-013: llama.cpp provider runs SmolLM2-135M-Q8 against the rule baseline
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: User-approved fetch: llama.cpp b12110 win-cpu server plus bartowski SmolLM2-135M-Instruct-Q8_0 GGUF, both in user-local cache outside the repo. Raw /completion skips the chat template so an instruct model rambles; the chat-completions endpoint applies it.
- **Decision**: LlamaCppBackend drives llama-server over /v1/chat/completions (temperature 0, fixed seed, n_predict 24, 60s timeout) with first-legal-token parsing. No weights, binaries, or network clients in the repo.
- **Consequences**: 60 tests OK; aikit check 5/5. Rule-vs-model on identical seeds: task success 5/5 -> 1/5, model contributes nothing measurable (T2 identical via 8/8 fallbacks); valid-but-useless tokens bypass fallback and truncate the rest at 200 steps with 0.0 reward. Determinism repeat identical (variance 0). Negative result kept: no tuning, no prompt search beyond endpoint/template fix.

### ADR-014: Goal-complete model-seam observations and prompts
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Planner.plan built backend obs with only task/x/y/steps/legal and build_prompt rendered only those, so distinct goal states collided to identical obs/prompt and any obs-limited backend had zero steering signal.
- **Decision**: Planner includes target, items_positions, obstacles, and cue copies in obs when present in state; build_prompt appends deterministic Target/Items/Obstacles/Cue lines when those keys are present, leaving minimal-obs prompts byte-identical. No new deps; backend None rule path unchanged.
- **Consequences**: 63 tests OK; aikit check 5/5; rule totals byte-identical (T1 466 / T2 240 / T3 217, trap seeds 16/8/13/6/9); fixed-rig syn 0.1246 phi 0.0 and hub0/m0 kill with p0/s0 no-op unchanged; obs-oracle on 4 steerable seeds 200/0.0 truncated -> 16/8/13/6 optimal with variance 0; minimal-obs ablation restores truncation.
