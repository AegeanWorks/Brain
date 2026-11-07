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

### ADR-025: Executable negative controls (kill-test discipline)
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Transferred idea from research-engine kill tests (EVID-008 warns on a verified test without a control; EVID-009 errors when a control never fails): trap/range/holdout tests pinned intact optimality, but the failing side lived only in one-off manual cut runs, so a future change could neuter a probe silently.
- **Decision**: Extract _enters_blocked_corridor to module level (pure extract-method, behavior-identical refactor) and add tests/test_negative_control.py: mock.patch it to False (visits-only ordering = pre-cycle-20 semantics, depth kept 4) and pin the reproducibly-failing signatures (479 12 vs intact 10; holdout-500s T3 742 vs 738) with call_count>0 engagement proof. No behavior change; no new deps.
- **Consequences**: 91 tests OK; aikit check 5/5; standing behavior and trace byte-identical (refactor verified by corridor/holdout/trap/exhaustive suites pre-commit); control fails reproducibly with pinned signatures; intact side green.

### ADR-026: Random-policy floor as a verdict control
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Transferred idea from Crucible random-patch controls (a win must beat the best of 3 randoms): blind ablations sever memory but keep lookahead, so nothing quantified how far the shipped planner stands above chance on the pin battery.
- **Decision**: tests/test_random_floor.py plays the 9 pin seeds with 3 seeded uniform-random policies (9001-9003) and requires rule 89 steps / 11.0 reward to beat the best random (1271 steps / 5.0) by pre-registered margins (steps x10, reward +5). No source change; no new deps.
- **Consequences**: 93 tests OK (27 random episodes + determinism check, ~4s); aikit check 5/5; standing behavior and trace byte-identical (no source diff); degraded (memory-blind) planner fails the steps margin (280x10 > 1271), proving the verdict discriminates planner quality, not just code presence.

### ADR-027: Backfill range pins 0-199 (complete the snapshot matrix)
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Lattice snapshot-diffing transfer, second half: audit found four ledger-verified totals with no test pins (T3 0-99 683, T3 100-199 732, T2 0-99 800, T1 100-199 1646), so a drift in the most-exercised ranges would pass all gates.
- **Decision**: tests/test_range_pins_0_199.py asserts the four exact totals (400 episodes, 0.4s). No source change; no new deps.
- **Consequences**: 94 tests OK; aikit check 5/5; standing behavior and trace byte-identical (no source diff); memory-blind cut moves T3 0-99 683 -> 874 (+191, seed-74 truncation), proving the pins catch memory-coupling regressions while 200+ pins carry corridor-cut sensitivity.

### ADR-028: Hash-chained telemetry with named-defect verifier
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Transferred idea from Assay (hash-chained evidence ledger + retrospective review): telemetry records were tamper-silent — a hand-edited log read back without complaint, so evidence integrity was asserted, not checked.
- **Decision**: Every record carries prev (previous digest, GENESIS for a new log, LEGACY-anchored continuation onto old tails) and digest (SHA-256 over canonical JSON without digest); verify_chain(path) returns ok/findings/records/head with first-defect naming (corrupt-line, unchained-record, edited-record, reordered-record, broken-link). Additive keys on schema 2; existing strict/corrupt-line/bin behavior unchanged. No new deps.
- **Consequences**: 100 tests OK (6 new, 0.1s); aikit check 5/5; standing behavior and trace byte-identical (94 carried tests green incl. roundtrip/bins/strictness); real 32-record run verifies clean with head digest; all 5 tamper classes fail loudly with named findings.

### ADR-029: Golden trace hashes for pin seeds (pinned simulation)
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Transferred idea from Keystone --simulate --expect-hash: step counts and rewards pin outcomes, but a behavior-neutral path swap at identical counts would drift silently past all pins.
- **Decision**: tests/test_golden_traces.py pins SHA-256 over canonical action sequences for the 9 pin seeds (computed once on the intact tree); regeneration is deliberately manual (reviewed edit, no auto-update) so goldens can never be rebaselined to green a red tree. No source change; no new deps.
- **Consequences**: 101 tests OK (0.014s); aikit check 5/5; standing behavior and trace byte-identical (no source diff); any path change fails loudly — corridor-cut moves 479 10->12 steps, which necessarily changes its hash (different length list).

### ADR-030: Policy citation in run headers (evidence binding)
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Transferred idea from Assay per-record policy citation + research-engine 3b evidence binding (a run is bound to what produced it): run_task_logged wrote headers with no policy reference (manifest_sha256 always None), so a log could not say which configuration produced it.
- **Decision**: agent.py declares PLANNER_POLICY (name + depth/corridor/visits/recall) with policy_digest() (SHA-256 over canonical declared config — behavior-preserving refactors do not invalidate evidence, any policy change does) and model_label() (rule/stub/model basename); run_task_logged cites all three in write_header (new optional policy/policy_sha256/model fields, additive on schema 2). No new deps.
- **Consequences**: 105 tests OK (4 new, ~1s); aikit check 5/5; standing behavior and trace byte-identical (94 carried behavior tests + fixed-rig syn 0.0541 green); config-variant digest differs (sensitivity); header policy tamper fails verify as edited-record:0 (binding rides the chain).

### ADR-031: Collapse dead lookahead depth to a leaf check
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Prompted by lacon RLM's explicit depth caps: questioned whether Brain's depth-4 chain still carries weight now that corridor avoidance (cycle 20) decides entries distance-independently.
- **Decision**: Replace recursive _has_exit(cell, depth) with the leaf check (free distance-reducing exit or goal); delete the depth parameter. Proven byte-identical action sequences on all 3906 T3 configs at depths 1, 2 and 4, plus T1 39711/39711 optimal and T2 structural.
- **Consequences**: 105 tests OK; aikit check 5/5; standing behavior (466/240/217, all pins incl. 9 goldens) and trace (syn 0.0541 phi 0.0) byte-identical; -3 lines, dead tuning knob removed. Corridor-cut control re-pinned 742 -> 744 (without corridor, depth had fixed 2 more steps of traps) with the background change documented in the test. Revival condition honestly recorded: multi-obstacle layouts or larger grids, where leaf viability may no longer suffice.

### ADR-032: Accurate policy citation after depth collapse
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Cycle 32 collapsed _has_exit to a leaf check but left PLANNER_POLICY advertising lookahead_depth 4, so run headers cited a tuner the code no longer reads.
- **Decision**: Replace the dead lookahead_depth key with viability leaf in PLANNER_POLICY; re-pin the digest-sensitivity probe to the new key; add tests/test_policy_accuracy.py (no dead knob, leaf declared, digest differs from legacy depth-4). No planner logic touched; no new deps.
- **Consequences**: 108 tests OK; aikit check 5/5; standing behavior (466/240/217) and trace (syn 0.0541 phi 0.0) byte-identical; policy_digest 99d01431... -> 18edf1ca...; headers cite the shipped configuration with chain verify ok; legacy depth-4 citation fails the new accuracy gate by construction.

### ADR-033: Hub-carried collect evidence for persistent-hidden forage
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Full-history recall returns the initial forage list forever on persistent-hidden layouts, so after the first collect the stale cell loops the agent to the 200-step cap with 1.0 reward. Planner read hub last_action and discarded it — the hub channel had no load-bearing use.
- **Decision**: Agent.run appends each successful collect cell to hub collected_positions (deduped, deterministic); Planner.plan filters recalled items_positions against that set for both rule geometry and backend obs. Visible states bypass recall, so the filter is a no-op there. No new deps.
- **Consequences**: 111 tests OK; aikit check 5/5; standing behavior (466/240/217) and trace (syn 0.0541 phi 0.0) byte-identical; persistent-hidden T1 200/1.0 -> 16/12/18 with 3.0; hub-blind lesion restores 200/1.0, proving hub-memory coupling.

### ADR-034: Visit-pooled detours for multi-obstacle navigation
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Cycle-32 revival condition: leaf viability was proven only on single-obstacle layouts. Two-blocker probes truncate twice (200/0.0) with viable-first routing oscillating on dead goal steps and visited back-edges.
- **Decision**: In _step_toward, open-field (no obstacles) keeps viable/dead/backup order; obstacle navigation pools viable goal steps with backup detours deduped by least-visited with dead last. No new deps; deterministic.
- **Consequences**: 114 tests OK; aikit check 5/5; standing (466/240/217, T1-100 1581, exhaustive 3906/3906 total 27860, goldens) byte-identical; multi (5,0) 200->9, (7,5) 200->20, (3,6) 13->11 all complete; memory-blind restores 200/0.0 on all three, proving visit coupling. Two multis remain non-optimal (reserved).

### ADR-035: Accurate pooling citation in run headers
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Cycle 35 pooled viable goal steps with backup detours for obstacle navigation but left PLANNER_POLICY on the pre-pool configuration, so run headers cited a planner the code no longer matches.
- **Decision**: Add detour_pooling visits to PLANNER_POLICY; add tests/test_pool_policy.py (pooling declared, digest differs from pre-pool legacy, value-sensitive). No planner logic touched; no new deps.
- **Consequences**: 117 tests OK; aikit check 5/5; standing behavior (466/240/217, multi 9/20/11) and trace (syn 0.0541 phi 0.0) byte-identical; policy_digest 18edf1ca... -> 4245d56e...; headers cite the shipped pooling configuration with chain verify ok; pre-pool citation fails the new accuracy gate by construction.

### ADR-036: Corridor-weighted pooling for multi-blocker detours
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Visits-only pooling loops north of the (4,4)+(5,5) block on target (5,6) (200/0.0 vs BFS 11) and costs +8 on (7,5) (20 vs 12): corridor entry is ignored in the pool, so the early eastward entry wins every visits tie.
- **Decision**: In _step_toward obstacle pooling, two-or-more blockers sort the deduped viable+backup pool by visits then blocked-corridor entry; single blockers stay visits-only (preserves seed-74 blind 200); open-field keeps viable-first. Extend tests/test_multi_obstacle.py to four configs with (7,5) re-pinned 18 and new (5,6) 13. No new deps; deterministic.
- **Consequences**: 117 tests OK; aikit check 5/5; standing (466/240/217, T1-100 1581, exhaustive 3906/3906, goldens) byte-identical; multi (5,6) 200->13, (7,5) 20->18; blind kills (7,5),(3,6),(5,6) with 200/0.0 while (5,0) stays 9/1.0 pool-sufficient (honest exception); digest unchanged (pooling visits + corridor avoidance already declared).

### ADR-037: Multi-obstacle golden paths for pinned traps
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Transferred idea from Keystone pinned simulation hash (standing goldens in cycle 30): multi counts pin outcomes, but a behavior-neutral path swap at identical counts would drift silently.
- **Decision**: tests/test_multi_goldens.py pins SHA-256 over canonical action sequences for the four multi configs (computed once on the intact tree); regeneration is deliberately manual (reviewed edit, no auto-update). No source change; no new deps.
- **Consequences**: 118 tests OK; aikit check 5/5; standing behavior and trace byte-identical (no source diff); any path change fails loudly — pre-pool ordering gives 200/200/13/200 counts, which necessarily changes every affected hash.

### ADR-038: Backfill fifth two-blocker pin for the snapshot matrix
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Lattice snapshot-diffing completion: (5,7) with (5,6),(4,2) verified 14/1.0 deterministic with blind 200/0.0, but no test pinned it — the fifth trap could drift while all gates stay green.
- **Decision**: Extend tests/test_multi_obstacle.py to five configs with (5,7)->14 and tests/test_multi_goldens.py to five hashes (fifth computed once on the intact tree). No source change; no new deps.
- **Consequences**: 118 tests OK; aikit check 5/5; standing behavior and trace byte-identical (no source diff); multi matrix 5/5 counts, 5/5 paths, blind 9/200/200/200/200.

### ADR-039: Declare the pool-corridor gate in run headers
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Cycle 37 gated corridor weighting in the detour pool on two-or-more blockers but left PLANNER_POLICY on pooling-visits only, so run headers cited a planner the code no longer matches.
- **Decision**: Add pool_corridor >=2 to PLANNER_POLICY; add tests/test_pool_corridor_policy.py (gate declared, digest differs from pre-gate legacy, value-sensitive). No planner logic touched; no new deps.
- **Consequences**: 121 tests OK; aikit check 5/5; standing behavior (466/240/217, multi 9/18/11/13/14) and trace (syn 0.0541 phi 0.0) byte-identical; policy_digest 4245d56e... -> ffa19359...; headers cite the shipped >=2 gate with chain verify ok; pre-gate citation fails the new gate by construction. 3-blocker (6,5) 200/0.0 truncation carried as documented routing-track headroom.

### ADR-040: Three-blocker snapshot matrix for the new family
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Transferred idea from Lattice snapshot-diffing completion (two-blocker matrix in cycle 39): five three-obstacle configs verified deterministic with visit-coupled blinds, but no test pinned them. One truncates (6,5) with no safe routing fix (seed-74/T1 pins block it, per cycles 35/37 prototypes).
- **Decision**: tests/test_three_blocker.py pins five counts with rewards plus a blind differential on (6,7); _ForcedThreeWorld hook with no private writes; regeneration manual. No source change; no new deps.
- **Consequences**: 123 tests OK; aikit check 5/5; standing behavior and trace byte-identical (no source diff); 3-blocker family 15/12/10/13/200 pinned with blinds 200/200/10/200/200; any routing change that moves a count fails loudly.

### ADR-041: Three-blocker golden paths for the pinned family
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Transferred idea from Keystone pinned simulation hash (multi paths in cycle 38, counts in cycle 41): three-blocker counts pin outcomes, but a behavior-neutral path swap at identical counts would drift silently.
- **Decision**: tests/test_three_goldens.py pins SHA-256 over canonical action sequences for the five configs (computed once on the intact tree); regeneration is deliberately manual (reviewed edit, no auto-update). No source change; no new deps.
- **Consequences**: 124 tests OK; aikit check 5/5; standing behavior and trace byte-identical (no source diff); any path change fails loudly.

### ADR-042: Complete the killing-blind matrices for both blocker families
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Transferred idea from Lattice negative-control completion: blind tests pinned one killing exemplar per family, so coupling loss on the other killing configs would pass all gates. Pool-sufficient (5,0),(6,0) and truncation-baseline (6,5) are honest exceptions (blind == intact).
- **Decision**: Extend the multi blind test to all four killing configs and the three-blocker blind test to all three killing configs (loops with honest-exception comments). No source change; no new deps.
- **Consequences**: 124 tests OK; aikit check 5/5; standing behavior and trace byte-identical (no source diff); multi kills 4/4 and three kills 3/3 pinned — coupling loss on any of them fails loudly.

### ADR-043: Persistent layout recall for cold-start recovery
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: `git grep -w memory_store` showed the persistent store is written every step but read only through `count()`; `Planner.plan` recalled from the current state and the in-memory episode only. After a restart with hidden goal fields, all four cold-start cases truncated at 200 steps with 0.0 reward, no source probe, and model-seam observations without target/items/cue/obstacles.
- **Decision**: Add an additive `layouts(task, seed, content, ts)` table with first-write-wins `save_layout` and `get_layout` (`CREATE TABLE IF NOT EXISTS`; old readers ignore it, so no format bump). `Agent` persists the reset state once per run, binds `Planner.bind_recall_source` to read it, and `Planner` loads it lazily once per episode only for task-relevant fields. Each plan records a source probe (state/memory/persistent/store_reads/resolved/model_obs_keys) in telemetry action args. `PLANNER_POLICY` cites `recovery_recall: persistent-layout`. `evals/coldstart.py` measures warm/cold/ablation with a capture backend. No new deps.
- **Consequences**: 129 tests OK; aikit check 5/5. Cold-start behavior 0/4 success, 200/200/200/200 steps, 0 reward -> 4/4, 16/8/13/6, 3/1/1/1; transfer gain 0 -> .92/.96/.935/.97; recovery 0 -> 1.0. Ablation (`bind_recall_source(None)`) restores 200/0 with store_reads 0 and no goal keys in model observations, so property and trace die with the cut. Standing pins unchanged (466/240/217, T1 seeds 0-99 1581, fixed syn 0.05411532 phi 0.0, goldens). `policy_digest` ffa19359... -> f53f99a8...; cold syn/phi remain 0 because reward is terminal-sparse, so the claim is dependency/recovery, not a synergy increase. Boundary: the cache is episode-scoped and layouts are first-write-wins, so a corrected layout needs a new (task, seed) or an explicit overwrite path.

### ADR-044: Layout completeness gate and incomplete-row healing
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: Cycle 45 made the layouts table first-write-wins. A cold-first run with an empty store therefore persisted a stripped state (no target/items/cue/obstacles); a later warm run could not replace it, so the next cold run still truncated at 200 steps with 0.0 reward. The poison was measurable four ways: stripped layout keys, 200-step cold2, empty persistent probe, and model observations without goal fields.
- **Decision**: Add `Agent._layout_complete(state)` using the task-field map. `_remember_layout` writes only complete states, and when the current state is complete while the existing row is incomplete or malformed it calls `MemoryStore.save_layout(..., replace=True)` (upsert); an incomplete current state can never overwrite. Add a `cold-first` scenario to `evals/coldstart.py` and three failing-first tests (cold-first no-poison, warm healing, gate-patch ablation). No new deps; no schema change beyond the cycle-45 table.
- **Consequences**: 132 tests OK; aikit check 5/5. Cold-first before: cold1 200/0, layout stripped, warm 16/8/13/6, layout still stripped, cold2 200/0. After: cold1 200/0, layout None, warm unchanged, layout complete, cold2 16/8/13/6 with rewards 3/1/1/1; probe persistent fields and model observations match the cycle-45 recovered runs. Ablation (patch `_layout_complete` True) reproduces the stripped-layout 200/0 path. Warm-cold cycle-45 behavior, standing 466/240/217, fixed syn 0.05411532 phi 0.0, and policy digest f53f99a8... are unchanged. Boundary: a legacy incomplete row heals on the next complete run for the same (task, seed); no manual database edit is needed.

### ADR-045: Bounded trust for legal backend proposals
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: `Planner.plan` returned any legal backend proposal forever. A deterministic backend returning the legal token `wait` truncated all four pin cases at 200 steps with 0.0 reward, while the hub outcome channel (`last_action`, `last_reward`) was written but not load-bearing. A first prototype that reset trust on every reward still burned 20 steps after each collect (T1 76 steps), so the gate needed an episode-scoped match-only state.
- **Decision**: Extract the rule action before the backend decision. The planner reads `steps_since_reward` from the hub (Agent increments per unrewarded step, resets on reward) and trusts a legal proposal until the window (20) is reached. A mismatching proposal at or after the window is rejected, counted in `fallbacks`, and sets `_backend_distrusted`; the backend stays match-only for the rest of the episode. `reset_trust()` runs at episode start. Each plan records `model_decision` (proposed/rule/steps_since_reward/trust_window/distrusted/accepted). `PLANNER_POLICY` cites `backend_trust: stall>=20->match-only`. `evals/trust.py` measures the stalled backend with trust on and `trust_window=None`; the random-floor control explicitly disables the gate to measure raw randomness. No new deps.
- **Consequences**: 137 tests OK; aikit check 5/5. Stalled backend 0/4 success, 200/200/200/200 steps, 0 reward -> 4/4, 36/28/33/26, 3/1/1/1; gain 0 -> .82/.86/.835/.87; recovery 0 -> 1.0; fallbacks 16/8/13/6; identical prompt hashes before/after (6e19bc1d/78c208fb/816fa226/ae3c4f52) with a different acceptance trace. Ablation (`trust_window=None`) restores 200/0 with accepted=true, distrusted=false, fallbacks 0. Rule-only standing pins unchanged (466/240/217, fixed syn 0.05411532 phi 0.0); policy_digest f53f99a8... -> e400adcd.... Boundary: a good backend whose proposal differs from the rule after a 20-step stall is also held match-only; the window is a declared safety threshold, not fitted to a seed.

### ADR-046: Honest verdicts at the step cap
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: `GridWorld.step` sets `done` at the energy/step cap as well as on task completion, so `Agent.run_task_logged` wrote verdict `done` for a 200-step run with 0.0 reward. Our own stalled-backend and cold-start baselines exposed the false success label: 200 steps, 0 reward, verdict `done`, reason `steps=200`.
- **Decision**: Add `Agent._episode_verdict(trace, max_steps)`: `done` only when the trace ended before the budget; a full-budget trace is `truncated`. The reason carries both `steps` and `reward`. `run_task_logged` consumes the helper. Add `tests/test_verdict.py` (success, cap, legacy-predicate ablation). No policy change; no new deps.
- **Consequences**: 140 tests OK; aikit check 5/5. Behavior is unchanged by design (cap 200/0, success 33/1). The trace changes the cap verdict `done` -> `truncated` and the reason `steps=200` -> `steps=200 reward=0.0`; the success reason gains `reward=1.0`; record count stays 402/68 and the hash chain is unchanged. The ablation patches `_episode_verdict` to the legacy predicate and restores `done`. Rule-only standing pins and policy e400adcd... are unchanged. Boundary: a genuine completion exactly at `max_steps` is labeled `truncated` because cap exhaustion is indistinguishable; the positive reward remains visible in the reason.

### ADR-047: Reject legal no-op backend proposals immediately
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: The cycle-47 trust gate only corrected a stalled backend after 20 consecutive unrewarded steps. A backend returning the legal token `wait` therefore cost 20 wasted steps per episode (T1 36, T2 28, T3:15 33, T3:65 26) even though `wait` is a dominated no-op whenever the rule can move or collect. The decision probe also had no machine-readable rejection reason.
- **Decision**: Add `Planner.noop_guard` (default on, independent of `trust_window`). A proposal is rejected as `no-op` when it is `wait` while the rule action is not `wait`, or `collect` while the rule action is not `collect`. The guard does not set `_backend_distrusted`; it runs every step. Add `reason` to `model_decision` (`accepted`, `no-op`, `stall`, `distrusted`, `invalid`). `PLANNER_POLICY` cites `backend_noop_guard: on`. The trust battery adds `--ablate-noop`, `--ablate-trust` and `--ablate` (both guards), and the random-floor control disables both guards. No new deps.
- **Consequences**: 143 tests OK; aikit check 5/5. Stalled backend 36/28/33/26 -> 16/8/13/6 with rewards 3/1/1/1; gain .82/.86/.835/.87 -> .92/.96/.935/.97; fallbacks stay 16/8/13/6; action hashes match the four goldens; prompt hashes are byte-identical (6e19bc1d/78c208fb/816fa226/ae3c4f52). Ablation no-op off (trust on) restores 36/28/33/26; trust off (no-op on) stays 16/8/13/6; both off restores 200/0. Rule-only standing pins unchanged (466/240/217, fixed syn 0.05411532 phi 0.0); policy_digest e400adcd... -> 180ba03d.... Boundary: the guard covers `wait` and premature `collect`; movement no-ops into a wall or obstacle still rely on the 20-step trust window.

### ADR-048: Reject blocked-movement backend proposals as no-ops
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: ADR-047 closed the `wait` and premature-`collect` cases but explicitly left blocked movement on the 20-step trust window. A backend returning `up` at `y=0` (or into an obstacle) is legal but cannot change position; a deterministic blocked-direction backend still measured 36/28/33/26 steps before the rule took over.
- **Decision**: Extend the existing `noop_guard` with `_movement_noop(action)`: a proposed `up/down/left/right` is a no-op when its target is outside the 8x8 board or in the current obstacle set, unless it equals the rule action. The guard remains independent of `trust_window` and reports `reason=no-op`. The trust battery gains a `noop` backend and `--backend noop`; tests cover immediate rejection and the no-guard stall window. No new deps, no policy-key change.
- **Consequences**: 145 tests OK; aikit check 5/5. Blocked-movement backend 36/28/33/26 -> 16/8/13/6 with rewards 3/1/1/1; gain .82/.86/.835/.87 -> .92/.96/.935/.97; fallbacks stay 16/8/13/6; action hashes match the four goldens; prompt hashes are byte-identical (4bd74314/7f1f5088/4f18a4b6/e05d4d08). Ablation `noop_guard=False` restores 36/28/33/26; both guards off restores 200/0. Rule-only standing pins unchanged (466/240/217, fixed syn 0.05411532 phi 0.0); policy_digest stays 180ba03d.... Boundary: a move into a free cell that later stalls still relies on the 20-step trust window; only immediate boundary/obstacle no-ops are caught.

### ADR-049: Serialize telemetry hash-chain appends with an AIKit-style advisory lock
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: AIKit serialises task-ledger and registry read-modify-write cycles with a cross-process `file_lock` (`scripts/disruption_recovery.py`, `idea_catcher/registry.py`). Brain's `Telemetry._write_record` read the head digest and appended without a lock, so two writers could both link to the same stale head. The failing-first test produced `broken-link:1`; the lock-off battery produced `broken-link:1,2` with only 2 of 4 records in the verified chain.
- **Decision**: Adapt the AIKit lock pattern to `telemetry/log.py`: `_append_lock` uses an `O_CREAT|O_EXCL` lock file carrying PID and timestamp, polls to a bounded `lock_timeout`, breaks locks older than `LOCK_STALE_SECONDS` via an atomic rename, and always releases on exit. `_write_record` holds the lock from the head read through line append, fsync and directory fsync; it refreshes a cached head when the on-disk size changed. A failed acquisition raises `TimeoutError` with Why/Fix, which the agent already records as a substrate error. `evals/telemetry_lock.py` measures the locked chain and the lock-off ablation. No new dependencies.
- **Consequences**: 149 tests OK; aikit check 5/5. Two writers x two records: locked run yields a valid 4-record chain; lock-off ablation yields `broken-link:1,2` and a 2-record verified prefix. Single-writer behavior and trace are unchanged (466/240/217, fixed syn 0.05411532 phi 0.0). Boundary: readers are not locked, and a lock is broken after 30s, so a writer paused >30s can lose its exclusion; an append is milliseconds, so this is treated as a crashed-writer recovery path. The AIKit transfer shortlist also includes reachability/round-trip audits, proof/evidence envelopes, the codebase-map digest and test budgets; this cycle implements the concrete trace-integrity gap, not the bookkeeping items.

### ADR-050: Repeated-position BFS escape for multi-obstacle routing loops
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: The documented three-blocker config (target [6,5], obstacles [6,4],[5,5],[3,5]) looped through six cells for 200 steps with 0.0 reward. A 300-config seeded three-blocker scan found two such truncations (the second at target [6,4], obstacles [5,4],[6,0],[6,3]); all other sampled configs were already byte-identical. The local viability/pool order uses only the last four memories for visit counts, so a six-cell loop never sees its own repeat.
- **Decision**: Add a module-level `_bfs_step(pos, goal, obstacles)` (deque BFS, fixed `up/down/left/right` neighbor order) and gate it inside `_rule_action`: when the task has a target, no remaining items, at least two obstacles, and the current cell appears at least twice in the full episode history, take one BFS step toward the goal. Record `probe.cycle_escape` with position/visits/distance/action. Add `Planner(cycle_escape=True)` as the ablation switch and `PLANNER_POLICY["cycle_escape"] = "repeat>=2->bfs"`. Add `evals/escape.py` (intact/ablate/blind modes with a declining backend) and `tests/test_cycle_escape.py`; update the three-blocker pins and goldens. No new dependencies; no schema change.
- **Consequences**: 156 tests OK; aikit check 5/5. Cycle-a 200/0 -> 19 steps/1.0 reward; cycle-b 200/0 -> 18/1.0; gain .905/.91; recovery 1.0; first prompt hashes byte-identical (398a93d3/aa934aba) and the backend model label/seed are unchanged. Ablation `cycle_escape=False` restores the exact baseline action hashes (8baacf99/c1ae3ac7), 200/0, no probe and syn 0.0; the memory-blind cut also restores 200/0 (its prompt omits `visits` by construction). Standing behavior (466/240/217), T1 0-99 1581, holdout 1581/800/738, fixed-rig syn 0.05411532 phi 0.0, trust 16/8/13/6, cold-start 16/8/13/6, exhaustive T3 3906/3906, multi pins 9/18/11/13/14 and three pins 15/12/10/13 are unchanged; only the former (6,5) pin moved 200/0 -> 19/1.0. `policy_digest` 180ba03d... -> ea445074.... Boundary: the trigger is position-based and needs at least two obstacles plus episode memory; a single-blocker or memory-blind run keeps the old local rule, and a target unreachable under the static obstacle map still returns `(None, 0)` and falls back to the local rule.

### ADR-051: Skip backend calls once the trust gate distrusts it
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: `Planner.plan` calls `backend.generate` on every step even after the 20-step stall gate sets `_backend_distrusted`. Match-only acceptance means only a proposal equal to the rule action could be accepted, which returns the same rule action, so every later call is redundant. The stalled-backend battery spent 36/28/33/26 calls on 36/28/33/26-step episodes; 15/7/12/5 of those calls were after distrust. The reason ladder also tested `since >= window` before `distrusted`, so every post-window rejection reported `stall` and the `distrusted` reason was unreachable.
- **Decision**: Add `Planner(skip_after_distrust=True)`. When the flag is on and `_backend_distrusted` is already true, skip `backend.generate`, emit a `model_decision` with `proposed=None`, `distrusted=True`, `accepted=False`, `reason="skipped"`, `skipped=True`, and return the rule action without incrementing `fallbacks`. Reorder the reason ladder so `distrusted` is checked before the stall threshold: `stall` marks only the triggering step, then `distrusted` when calls are kept. Add `PLANNER_POLICY["backend_distrust_skip"] = "on"`, `evals/trust.py --no-skip` plus `skipped_steps`, and tests for the skip, the cost ablation, the reason, the policy key and flag validation. No new dependencies; no schema change.
- **Consequences**: 158 tests OK; aikit check 5/5. Stalled legal backend: steps/rewards/success/action hashes unchanged (36/28/33/26, 3/1/1/1, 90a61333/1736021f/33d9f09c/55e279bf); model calls 36/28/33/26 -> 21/21/21/21; fallbacks 16/8/13/6 -> 1/1/1/1; skipped steps 0 -> 15/7/12/5; `rejected_steps` stays 16/8/13/6; last reason `stall` -> `skipped`. The M/P/S/hub vectors and recomputed syn/phi are byte-identical (syn 0.11612872882479021/0.006591080505772978/0.015843139290281194/0.010002568849882792, phi 0.0), so this is a cost/probe change, not an action change. Ablation `--no-skip` restores 36/28/33/26 calls and 16/8/13/6 fallbacks, with last reason `distrusted` (now reachable) and the same actions. Default no-op-guard runs (16/8/13/6, calls 16/8/13/6), trust-off and both-off controls (200/0, calls 200), rule-only standing (466/240/217), T1 0-99 1581, holdout 1581/800/738, fixed-rig syn 0.05411532 phi 0.0, cold-start 16/8/13/6 and the cycle-54 escape battery are unchanged. `policy_digest` ea445074... -> 8c2c51bc.... Boundary: a distrusted backend's side effects (logging, adaptation) are not invoked after distrust; `skip_after_distrust=False` restores them for measurement. The skipped action is provably identical because match-only acceptance can only return the rule action.

### ADR-052: Bind each model decision to its generation-manifest hash
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: `LlamaCppBackend.generate` computes a manifest over model id, checkpoint label, prompt, observation and sampling, but `Planner.plan` discarded `last_manifest`. The run header carries only the model label, so a checkpoint swap under the same filename is invisible in the trace, and the "same model hash/prompts" claim cannot be audited from a run log. A failing-first probe showed the decision keys without any manifest hash while the backend held one (`5d06a1dc...`).
- **Decision**: Add `Planner(probe_manifest=True)`. After a successful `backend.generate`, copy `last_manifest["sha256"]` into `model_decision.model_manifest_sha256`; on any raise, record `null` rather than a stale value. Skipped decisions record `null` when the probe is on. Add `PLANNER_POLICY["model_manifest_probe"] = "on"`, `evals/manifest_binding.py` (intact/ablate/swap modes with a declining manifest backend), and `tests/test_manifest_binding.py` for per-step hashes, checkpoint swap, probe-off ablation, stale-raise handling, the policy key and flag validation. `probe_manifest=False` removes the key for the ablation. No new dependencies; no schema change.
- **Consequences**: 164 tests OK; aikit check 5/5. Intact and probe-off actions, steps, rewards, M/P/S/hub vectors and recomputed syn/phi are byte-identical (T1 71: 16/3.0, action bafe50ff..., syn 0.03728282024294677, phi 0.0, 36 records; T3 15: 13/1.0, action 63c67660..., syn -0.05791331748493783, phi 0.0, 30 records). Manifest coverage is 1.0 intact and 0.0 probe-off; checkpoint A/B keeps the action trace identical while changing the first manifest hash (T1 cabec7a8... vs 6583aae7...; T3 5ba4e50c... vs 4a410229...). The raising-backend test records `null`, not the stale hash. Standing 466/240/217, T1 0-99 1581, holdout 1581/800/738, fixed-rig syn 0.05411532 phi 0.0, trust 16/8/13/6, escape 19/18 and cold-start 16/8/13/6 are unchanged. `policy_digest` 8c2c51bc... -> 136dec8aaa005c1248bd11b144fa0d3b1d627e468d5bdd083fbbbff4d17caa26. Boundary: the manifest is only as trustworthy as the backend's supplied labels; weights remain outside the repo and only hashes/labels are logged. A backend that does not set `last_manifest` records `null`.

### ADR-053: BFS-distance dead-pool guard for exactly two blockers
- **Date**: 2026-11-07
- **Status**: Accepted
- **Context**: The two-blocker pin (target [7,5], obstacles [6,1],[7,2]) enters the dead goal step [7,1] even though the live backup [6,0] is closer, costing 18 steps vs BFS 12. A plain dead-step exclusion improved it to 16 but regressed a sampled (3,0) config 11 -> 21 because the chosen live backup was farther. The three-blocker goldens must also stay byte-identical, so the guard cannot rewrite the 3-blocker pool.
- **Decision**: In `_step_toward`, when there are exactly two obstacles, compute `_bfs_step` distance from every deduped pool candidate to the goal; if a live candidate exists and the best live distance is <= the best dead distance, drop the dead goal steps before the visits/corridor sort. Record `probe.dead_pool` with position, excluded action/cell, live distance and dead distance. Add `Planner(dead_pool_filter=True)` and `PLANNER_POLICY["dead_pool_filter"] = "2-blockers:live<=dead-bfs"`. Add `evals/dead_pool.py` (intact/ablate modes) and `tests/test_dead_pool.py`; update the (7,5) count/golden and the multi docstring. No new dependencies; no schema change.
- **Consequences**: 170 tests OK; aikit check 5/5. (7,5) 18 -> 16 with 1.0 reward; action hash de1154e1... -> 1c9552d3...; the probe fires once at [7,0], excludes down [7,1], live distance 8 vs dead 10. The other multi pins stay 9/11/13/14 (some emit the probe without an action change) and all three-blocker pins/goldens stay 15/12/10/13/19 with byte-identical paths. Ablation `dead_pool_filter=False` restores 18 steps, the old action hash, no probe and syn -0.002387766; blind (7,5) still truncates 200/0. A 300-config two-blocker scan shows 0 regressions and 0 count changes outside the pinned case. Standing 466/240/217, T1 0-99 1581, holdout 1581/800/738, fixed-rig syn 0.05411532 phi 0.0, trust 16/8/13/6, escape 19/18, cold-start 16/8/13/6 and exhaustive single-obstacle T3 3906/3906 are unchanged. `policy_digest` 136dec8a... -> d097b97b466264471c140abe3f9a1d116d7bdcda3c9e4a798413ddc38b09ba1e. Boundary: the guard uses BFS geometry, not episode memory, so it is a routing improvement rather than an emergence claim; it is restricted to exactly two blockers to preserve the three-blocker goldens.
