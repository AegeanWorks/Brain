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

### ADR-015: Visit-complete model-seam observations and prompts
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: After ADR-014 the obs carried goals but not the least-visited tie-break memory, so obs-limited policies still cycled on tie-trap seeds (T3 seed 74: rule 9 vs obs-only 200).
- **Decision**: Planner includes sorted visits [[x, y, count]] in obs when non-empty; build_prompt appends a deterministic Visits line when the key is present, leaving all prior prompts byte-identical. No new deps; backend None rule path unchanged.
- **Consequences**: 66 tests OK; aikit check 5/5; rule totals byte-identical (466/240/217); fixed-rig syn 0.1246 phi 0.0 unchanged; visit-oracle 5/5 optimal (74: 200 -> 9, others unchanged, variance 0); visits-stripped ablation restores 200/0.0 on seed 74 only.

### ADR-016: Episode-memory goal recall for transient state dropout
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Planner read goal keys only from the current state, so transient dropout (target/items stripped at plan-time with memories intact) truncated runs the episode buffer could have saved.
- **Decision**: Planner recalls missing target/items_positions/obstacles/cue from provided episode memories (most-recent-first, deterministic copies) for both rule geometry and backend obs; present keys (including empty lists) never trigger recall. No new deps; no world change.
- **Consequences**: 69 tests OK; aikit check 5/5; standing totals byte-identical (466/240/217); fixed-rig syn 0.1246 phi 0.0 unchanged; hidden-target 200 -> 13 and hidden-items 200 -> 16 with variance 0; memory-blind ablation restores 200/0.0. Boundary: persistent hidden worlds (saved states also hide) need full-history recall plus a new task family — reserved.

### ADR-017: Full-history episode recall for persistent hidden goals
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Goal recall searched the last-5 window Agent passed to Planner, so initial-only goals fell out after step 5 and persistent-hidden runs truncated.
- **Decision**: Agent.run passes full episode history (recall(limit=None)) to Planner; Planner still slices last 4 for visits and searches all provided memories most-recent-first for missing goals. No new deps.
- **Consequences**: 71 tests OK; aikit check 5/5; standing behavior byte-identical (466/240/217, trap 16/8/13/6/9); standing trace syn 0.1246 -> 0.0541 (M[1] now carries full depth vs capped 5; lesions still hold: hub0/m0 kill, p0/s0 no-op, signal still >0.05); persistent-hidden T3-15 200 -> 13 and T3-65 200 -> 6 with variance 0; forced last-5 ablation restores 200/0.0. Boundary: T1 items persistent-hidden needs stale-list handling (initial list goes stale after collects) — reserved.

### ADR-018: Three-step exit lookahead for column-blocking traps
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Depth-2 viability entered blocked columns early on T3 seeds 202/272 (target behind a column obstacle), costing +2 detours each; 200-299 scan found exactly these 2 traps.
- **Decision**: Generalize _has_exit depth 2 -> 3 (one constant; branching still <= 2; deterministic). No new deps; visits ordering unchanged.
- **Consequences**: 74 tests OK; aikit check 5/5; T3 202 9 -> 7 and 272 16 -> 14 (both optimal); T3 200-299 total 722 -> 718 with all other 98 seeds byte-identical; 0-29 totals 466/240/217, 0-99 totals 1581/800/683, and 100-199 fully optimal unchanged; fixed-rig syn 0.0541 phi 0.0 unchanged; depth-3 lookahead alone suffices on these traps (blind == intact, like seeds 15/65); visit-memory coupling still carried by seed-74 blind truncation.

### ADR-019: Four-step exit lookahead for adjacent column blocks
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Depth-3 still entered the column early on T3 seed 307 (target [1,5] directly behind obstacle [1,4]); the free cell (1,3) masked the trap within 3 ply. A 300-399 scan found exactly this 1 trap.
- **Decision**: Generalize _has_exit depth 3 -> 4 (one constant; branching still <= 2; deterministic). No new deps; visits ordering unchanged.
- **Consequences**: 77 tests OK; aikit check 5/5; T3 307 8 -> 6 (optimal); T3 300-399 total 673 -> 671 with all other 99 seeds byte-identical; 400/400 T3 seeds optimal across 0-399; all prior totals unchanged; fixed-rig syn 0.0541 phi 0.0 unchanged; depth-4 lookahead alone suffices here (blind == intact); visit-memory coupling still carried by seed-74 blind truncation.

### ADR-020: Blocked-corridor entry deprioritization (distance-independent)
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Depth-only lookahead needs unbounded depth to see distant column/row blocks (seed 479: target [3,7] behind obstacle [3,6] at distance 6-7); a 400-499 scan found exactly this 1 trap (+2).
- **Decision**: In _step_toward grouping, sort each of viable/dead by (enters_blocked, visits) with stable order: entering the goal's column/row while an obstacle lies strictly between the candidate cell and the goal sorts after staying out; visits still break ties; x-first survives ties; backup (no goal-directed free cell) unchanged. O(1), deterministic, no new deps.
- **Consequences**: 80 tests OK; aikit check 5/5; T3 479 12 -> 10 (optimal); T3 400-499 total 677 -> 675 with all other 99 byte-identical; 500/500 T3 seeds optimal across 0-499; all prior totals unchanged; fixed-rig syn 0.0541 phi 0.0 unchanged; corridor+depth suffices here (blind == intact); visit-memory coupling still carried by seed-74 blind truncation.

### ADR-021: Generation manifest fingerprints for the model seam
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Transferred idea from ModelDuck (generation-manifest fingerprints, benchmark test-hash discipline) and Crucible (frozen versioning): Brain's gates require same-prompts proof across before/after batteries, but prompt identity was textual with no fingerprint.
- **Decision**: New stdlib-only models/manifest.py: canonical JSON (sorted keys, compact separators) SHA-256 over {model_id, checkpoint label, prompt, observation, sampling}; prompt_set_manifest order-independent battery digest. LlamaCppBackend records self.last_manifest per generate() call (None-safe); StubBackend unchanged. Checkpoint is a caller-supplied label (basename/hash recorded outside the repo); no weights in repo.
- **Consequences**: 86 tests OK; aikit check 5/5; standing behavior byte-identical (466/240/217, all pins); standing trace identical (syn 0.0541 phi 0.0); manifest determinism 4x repeat variance 0; prompt/visits sensitivity proven (enriched vs minimal differ); manifest removal breaks the 6-test probe (ablation).

### ADR-022: Frozen probe/holdout seed split (500-599)
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Transferred idea from Crucible (frozen splits, train/holdout separation): probe seeds 0-499 drove every planner fix, but nothing pinned the verified-optimal wider ranges, so a future change could silently move them while all probe tests stay green.
- **Decision**: Freeze seeds 500-599 as holdout with exact totals (T1 1581 / T2 800 / T3 738) in tests/test_holdout_500s.py; probe work continues on 0-499. No source change; no new deps.
- **Consequences**: 87 tests OK; aikit check 5/5; standing behavior and trace byte-identical (no source diff); corridor-cut ablation moves holdout T3 738 -> 742 (+4 across 11 blocked-corridor layouts incl. 560, a 307-twin) and kills 479/400-499 pins, proving the holdout is load-bearing for shipped integrations.

### ADR-023: Triple-run repro gate for standing pins
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Transferred idea from ModelDuck determinism lockdown (IDEA-1627 batch-1 + triple-run) and its --deterministic repro mode: Brain recorded variance-0 notes ad hoc per cycle, but nothing gated replay determinism, so future nondeterminism (ordering, clock, RNG) could hide.
- **Decision**: tests/test_repro.py replays all 9 pin seeds 3x and asserts byte-identical step counts, rewards, and SHA-256 over canonical action sequences. No source change; no new deps.
- **Consequences**: 88 tests OK; aikit check 5/5; standing behavior and trace byte-identical (no source diff); single-action perturbation flips the fingerprint (sensitivity proven); decision paths verified RNG/clock/set-iteration free by grep; routing-cut ablation N/A by design (gate checks variance, value pins live in trap/range tests).

### ADR-024: Exhaustive T3 config coverage (evidence matrix)
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Transferred idea from Lattice (evidence matrix + coverage gaps): T3 layouts are exactly one target plus one obstacle on 63 free cells (3906 ordered pairs), but pins only sampled seeds 0-999, so most configs were unverified. T1 39711/39711 and T2 2/2 verified by one-off audit scans.
- **Decision**: tests/test_exhaustive_t3.py enumerates all 3906 (target, obstacle) pairs through a _ForcedLayoutWorld subclass hook (no cross-module private writes; constructor/reset paths untouched) and asserts per-config BFS-optimality plus grand total 27860. T1 exhaustive (39711 configs, all optimal) recorded as audit evidence; live gate keeps 100-seed + holdout pins (40s+ gate cost refused). No new deps.
- **Consequences**: 89 tests OK (1.3s); aikit check 5/5 after subclass-hook rewrite (direct private writes refused by guidelines gate); standing behavior and trace byte-identical (no source diff); corridor-cut ablation: 21 non-optimal configs, total 27902 vs 27860 (+42) — the battery catches 21 traps where seed sampling caught a handful.
