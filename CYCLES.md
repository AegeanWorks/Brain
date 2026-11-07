# Brain improvement cycles

Append-only record. One entry per cycle: baseline, change, after-numbers with
variance, ablation result, gate results, exact commands. No sentience language:
only integration scores, cross-module dependencies, and ablation differentials.

## Cycle 1 — persistent outcome accounting + explicit substrate error counters

- **Baseline** (same rig both runs: wiring path with MemoryStore + tracker +
  persistent SelfModel + file log, seeds 0-9, max_steps 200):
  - canonical gate: 40 tests OK
  - aikit check: 4/5 (hygiene FAIL, 8 silent-except: 6 agent.py, 2 test_wiring.py)
  - tasks: T1 10/10 succ, avg_steps 15.5; T2 10/10, 8.0; T3 10/10, 7.0
  - persistent SM: steps 155/80/70, errors 0/0/0, error_rate 0.0/0.0/0.0
  - recompute: phi 0.0/0.0/0.0; syn 0.1167/0.1000/0.1229
  - lesion phi deltas: hub0/m0/p0/s0 all 0.0 (floor)
- **Gap**: persistent ok always True forced S[0]=0 constant (zero variance);
  silent passes hid substrate health and blocked the gate.
- **Target delta**: errors = non-reward steps (>0), error_rate 0.0 -> ~0.8,
  hygiene 8 -> 0 findings, gates 5/5, harness +3 tests.
- **Falsifier**: errors still 0, hygiene still FAIL, or unittest red after the
  change; emergence falsifier: phi/syn lesion_s delta stays 0.
- **Change** (agent.py only + 2 marker comments in tests/test_wiring.py +
  new tests/test_substrate_errors.py): ok = (reward > 0.0) in persistent
  record; six silent passes replaced by substrate_errors() counters
  (bind/memory_store/planner_tracker/self_model/telemetry_log/verdict);
  substrate_errors() accessor; Agent docstring documents the accounting.
- **After** (identical battery, same seeds):
  - tasks identical: T1 avg_steps 15.5, T2 8.0, T3 7.0; succ 10/10 x3;
    per-seed default-path variance T1 mean 15.5 stdev 2.693 (min 11 max 22),
    T2 mean 8.0 stdev 0.0, T3 mean 7.0 stdev 4.0 (min 2 max 13)
  - persistent SM: errors 125/70/60, error_rate 0.806/0.875/0.857;
    steps/budget/mean_conf unchanged
  - counters on clean runs: all six keys 0 across 305 steps (no hidden
    failures); faulty-store injection counted 10/10 with run continuing
  - recompute: phi 0.0/0.0/0.0 (unchanged); syn 0.1167/0.1000/0.1229
    (unchanged to 4 decimals)
- **Ablation** (same logs, intact vs lesioned):
  - hub0: syn -> 0.0 on all tasks (hub carries signal)
  - m0: syn -> 0.0 on all tasks (M carries signal)
  - p0: syn unchanged (P carries nothing)
  - s0: syn unchanged, phi unchanged 0.0 (S carries nothing for these
    estimators) — emergence falsifier triggered: no integration claim.
- **Verdict**: visibility win (measured error signal + clean counters +
  green gates), integration negative. No emergent claim. Verdict UNKNOWN.
- **Gates**: unittest 43/43 OK; aikit check 5/5 PASS (test, hygiene,
  guidelines, secrets, compat).
- **Commands run**:
  - `python -m unittest discover -s tests -t .` -> 40 OK (before), 43 OK (after)
  - `python aikit.py check brain` -> 4/5 FAIL hygiene/8 (before), 5/5 PASS (after)
  - wiring battery scripts (before/after, 10 seeds x3 tasks) + per-seed
    variance probe + faulty-store injection test
- **Pinned regression baselines for cycle 2**: unittest 43 OK; aikit 5/5;
  wiring errors T1=125 T2=70 T3=60 (10 seeds); error_rate 0.806/0.875/0.857;
  phi 0.0 x3; syn 0.1167/0.1000/0.1229; lesion_s syn delta 0.0 x3;
  task succ 30/30, avg_steps 15.5/8.0/7.0.

## Cycle 2 — dead-end-entry lookahead with least-visited tie-break

- **Baseline** (cycle 1 pins): 43 tests OK; aikit 5/5; 30-seed step totals
  T1=466 (mean 15.533), T2=240 (mean 8.0, stdev 0.0), T3=219 (mean 7.3).
- **Gap**: T3 seed 15 (target [6,7], obstacle [6,1]) took 15 steps vs
  BFS-optimal 13: x-first ordering entered column x=6, found (6,1) blocked,
  and oscillated (5,0)<->(6,0) before the stuck backstop fired (+2 steps).
  T1 audit: greedy path == optimal TSP path on all 30 seeds and
  actual == greedy+3 everywhere — ordering headroom zero (dead end, one line).
- **Target delta**: T3 seed 15 15->13; all other 89 runs byte-identical
  (T1=466, T2=240, T3 total 219->217).
- **Falsifier**: seed 15 stays 15, or any other seed's step count increases.
- **Change** (agent.py only: _step_toward + 4-line visits build in
  Planner.plan; tests/test_trap_escape.py new): one-step lookahead prefers
  distance-reducing candidates with a free exit toward the goal (goal cell
  trivially viable), then least-visited cells from planner memory; stable
  x-first/fallback order breaks ties. Deterministic, stdlib only.
- **After** (identical battery, same seeds):
  - T3 seed 15: 15 -> 13 (optimal, matches BFS).
  - 30-seed totals: T1=466, T2=240, T3=217 — every non-target seed identical.
  - 100-seed T3 scan: one residual detour remains, seed 65 (8 vs 6, a
    2-ply cul-de-sac entry the 1-step rule cannot see) — recorded boundary.
- **Ablation** (integration cut: BlindPlanner severs memory, same rules):
  - intact seed 65 completes in 8 steps with reward 1.0;
  - blind seed 65 cycles to the 200-step cap with zero reward.
  - Gain dies with the cut, returns with the restore: the visit-count
    memory input is load-bearing (it also guards lookahead-induced cycles
    on seeds 65/74, which truncate at 200 without it).
  - Mechanism note, honestly recorded: on seed 15 lookahead alone suffices
    (blind still scores 13); visits carry the differential on trap seeds.
- **Verdict**: efficiency win with proven memory coupling; no emergence
  claim. Verdict UNKNOWN.
- **Gates**: unittest 46/46 OK; aikit check 5/5 PASS (README tree updated
  for CYCLES.md after a guidelines FAIL on the first check run).
- **Commands run**:
  - `python -m unittest tests.test_trap_escape -v` -> 2 FAIL (15 vs 13,
    219 vs 217) before; 3 OK after (incl. ablation).
  - `python -m unittest discover -s tests -t .` -> 46 OK.
  - `python aikit.py check brain` -> 4/5 (guidelines: README tree) then
    5/5 after README fix.
  - audit probes: T1 greedy-vs-optimal per seed, T3 actual-vs-BFS per seed,
    repeat-count probe, 100-seed detour scan, no-visits comparison probe.
- **Pinned regression baselines for cycle 3**: unittest 46 OK; aikit 5/5;
  step totals T1=466 T2=240 T3=217 (30 seeds); T3 seed 15 = 13;
  T3 seed 65 = 8 intact / 200 blind; wiring SM errors T1=125 T2=70 T3=60;
  phi 0.0 x3; syn 0.1167/0.1000/0.1229.

## Cycle 3 — two-step exit lookahead

- **Baseline** (cycle 2 pins): 46 tests OK; aikit 5/5; T3 seed 65 = 8
  (BFS-optimal 6); T3 30-seed total 217.
- **Gap**: T3 seed 65 (target [3,3], obstacle [3,2]): 1-step lookahead
  routed (2,0)->(3,0)->(3,1), a cul-de-sac whose only distance-reducing
  exit (3,2) is blocked, costing +2 steps (8 vs 6). A 2-ply trap the
  depth-1 rule cannot see.
- **Target delta**: T3 seed 65 8->6 (optimal); 30-seed totals unchanged
  (seed 65 is outside the 0-29 pin range); no other seed changes.
- **Falsifier**: seed 65 stays 8, or any 0-29 seed changes steps.
- **Change** (agent.py only: _has_exit generalized to depth 2;
  tests/test_trap_escape.py: new seed-65 pin, ablation moved to seed 74):
  a candidate is viable when it has a free exit that itself still has a
  free exit or is the goal. Depth bounds recursion; branching <= 2.
  Deterministic, stdlib only.
- **After** (identical battery, same seeds):
  - T3 seed 65: 8 -> 6 (optimal, matches BFS).
  - 30-seed totals: T1=466, T2=240, T3=217 — all unchanged.
  - 100-seed T3 scan (seeds 0-99): zero detours vs BFS (total 683);
    memory-blind same scan: 1 truncation (seed 74, 200 vs 9) totaling
    874 — a +191-step memory-coupling gap.
- **Ablation** (integration cut: BlindPlanner severs memory, same rules):
  - intact seed 74 completes in 9 steps with reward 1.0;
  - blind seed 74 cycles to the 200-step cap with zero reward.
  - Gain dies with the cut, returns with the restore. Mechanism note,
    honestly recorded: on seeds 15/65 the 2-ply lookahead alone suffices
    (blind scores 13/6 there); the visit-count memory input carries the
    differential on tie-trap seeds (74), where lookahead-only cycling
    would otherwise run to cap.
- **Verdict**: efficiency win (seed 65 optimal, 100-seed T3 clean) with
  proven memory coupling; no emergence claim. Verdict UNKNOWN.
- **Gates**: unittest 47/47 OK; aikit check 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_trap_escape -v` -> 2 FAIL (8 vs 6,
    217 vs 215-pin error) before; corrected pin (seed 65 outside 0-29
    range: T3 stays 217) then 4 OK after.
  - `python -m unittest discover -s tests -t .` -> 47 OK.
  - `python aikit.py check brain` -> 5/5.
  - probes: depth-2 intact-vs-blind, 100-seed detour scans intact and
    memory-blind.
- **Pinned regression baselines for cycle 4**: unittest 47 OK; aikit 5/5;
  step totals T1=466 T2=240 T3=217 (30 seeds); T3 seed 15 = 13;
  T3 seed 65 = 6; T3 seed 74 = 9 intact / 200 blind zero-reward;
  T3 seeds 0-99 zero detours (total 683); wiring SM errors T1=125 T2=70
  T3=60; phi 0.0 x3; syn 0.1167/0.1000/0.1229.

## Cycle 4 — optimal-tour first pick for forage ordering

- **Baseline**: 47 tests OK; aikit 5/5; T1 100-seed total 1587 with
  seeds 71/74/78 at 18/14/20 vs 16/12/18 optimal (+2 each).
- **Gap**: nearest-greedy item choice is not the optimal-tour first pick
  on clustered 3-item layouts. Cycle 2's dead-end verdict covered only
  seeds 0-29; the 100-seed audit (new measurement this cycle) found the
  3 greedy traps. Transfer headroom verified absent (repeat runs
  deterministic-identical, gain 0.0); T2 structurally optimal (8 steps,
  all seeds); routing headroom elsewhere exhausted.
- **Target delta**: seeds 71->16, 74->12, 78->18; 100-seed total
  1587->1581; all other 97 seeds byte-identical.
- **Falsifier**: any of the 3 stays, or any other seed changes steps.
- **Change** (agent.py only: _first_of_best_tour replaces _nearest;
  tests/test_tour_order.py new): shortest-Manhattan-tour first cell over
  remaining items; exhaustive permutations in deterministic order (cells
  sorted, first strictly-shortest wins). stdlib itertools only.
- **After** (identical battery, same seeds):
  - T1 seeds 71/74/78: 18/14/20 -> 16/12/18 (all optimal, match BFS tour).
  - T1 100-seed total: 1587 -> 1581 exactly (-6 = the 3 fixed seeds;
    proves no other seed changed).
  - 30-seed totals guard (existing test): T1=466, T2=240, T3=217 unchanged.
- **Ablation**: ordering is not a memory-integration point, so no
  sever-the-coupling ablation applies; the cut evidence is the
  pre-change baseline on identical rig/seeds (18/14/20 with _nearest,
  restored by revert). Gain dies with the revert by construction
  (verified: the failing-first pins failed on the pre-change tree).
- **Verdict**: efficiency win (-6 steps/100 seeds, all optimal now);
  no emergence claim. Verdict UNKNOWN.
- **Gates**: unittest 49/49 OK; aikit check 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_tour_order -v` -> 2 FAIL (18 vs 16,
    1587 vs 1581) before; 2 OK after.
  - `python -m unittest discover -s tests -t .` -> 49 OK.
  - `python aikit.py check brain` -> 5/5.
  - probes: T1 0-99 optimality baseline, T1 0-99 total, transfer
    repeat-runs (gain 0.0 on 4 samples), T3 100-seed scan (carried).
- **Pinned regression baselines for cycle 5**: unittest 49 OK; aikit 5/5;
  step totals T1=466 T2=240 T3=217 (30 seeds); T1 100-seed total 1581;
  T1 seeds 71/74/78 = 16/12/18; T3 seed 15 = 13; T3 seed 65 = 6;
  T3 seed 74 = 9 intact / 200 blind zero-reward; wiring SM errors
  T1=125 T2=70 T3=60; phi 0.0 x3; syn 0.1167/0.1000/0.1229.

## Cycle 5 — remove the inert stuck-override backstop

- **Baseline**: 49 tests OK; aikit 5/5; 100-seed totals T1=1581, T2=800,
  T3=683 (measured this cycle). Calibration audit: persistent mean_conf
  0.56-0.60 vs true reward rates 0.13-0.19 (error ~0.42) — but mean_conf
  is consumed by nothing (snapshot display only), so recalibrating it
  would be number churn with no downstream effect (rejected, one line).
- **Gap**: ADR-004's stuck override (position repeated >=2 forces one
  y-first step) fired 238 times in 3064 plan calls yet a disabled-stuck
  probe returned byte-identical 100-seed totals (1581/800/683, all
  complete): the firings land on collect dwells and routing states where
  _toward agrees anyway. Dead code with proof.
- **Target delta**: -6 lines, zero behavior change on all 300 runs;
  all 49 tests and all pins stay green.
- **Falsifier**: any test red, or any 100-seed total differing post-removal.
- **Change** (agent.py only, 6 lines deleted): removed the stuck flag
  computation and the y-first override branch in _toward. positions and
  visit counts stay (visit ordering remains load-bearing per the seed-74
  ablation). T2 wait rule stays (task-contract semantics).
- **After** (identical battery, same seeds):
  - 100-seed totals: T1=1581, T2=800, T3=683 — byte-identical, all
    complete with reward.
  - unittest 49/49 OK (includes tour/trap pins, substrate-error tests).
- **Ablation**: not an integration claim; the cut evidence is the
  disabled-stuck probe on the pre-removal tree (identical totals), i.e.
  the branch's presence never moved a number. Removal proof: full suite
  plus 300-run totals green after.
- **Verdict**: simplification win with complete behavior-identity proof;
  no emergence claim. Verdict UNKNOWN.
- **Gates**: unittest 49/49 OK; aikit check 5/5 PASS.
- **Commands run**:
  - disabled-stuck probe (temporary flag): 1581/800/683 identical.
  - `python -m unittest discover -s tests -t .` -> 49 OK (after removal).
  - `python aikit.py check brain` -> 5/5.
  - post-removal 100-seed re-run: 1581/800/683 identical.
- **Pinned regression baselines for cycle 6**: unittest 49 OK; aikit 5/5;
  step totals T1=466 T2=240 T3=217 (30 seeds); T1 100-seed total 1581;
  T3 100-seed total 683; T2 100-seed total 800; trap/tour pins carried;
  wiring SM errors T1=125 T2=70 T3=60; phi 0.0 x3;
  syn 0.1167/0.1000/0.1229.

## Cycle 6 — extended audit seeds 100-199: zero verified improvements (STOP)

- **Baseline**: cycle-5 pins carried (49 OK, 5/5, all totals).
- **Measure**: optimality scan, seeds 100-199, identical rig:
  - T1 vs optimal-tour+3: 100/100 optimal, zero non-optimal.
  - T3 vs BFS-optimal: 100/100 optimal, zero detours.
  - T2: 100/100 at 8 steps (structural optimum).
  - Combined with cycles 2-4: 200/200 seeds optimal on T1/T3.
- **Find**: remaining gap candidates reviewed, none qualifies:
  - transfer gain: repeat runs deterministic-identical (gain 0.0, no
    headroom) — dead.
  - self-model mean_conf miscalibration (~0.42): consumed by nothing;
    recalibrating moves no downstream number — rejected as churn.
  - planner-tracker blind advancement / M[1] saturation: redefining
    either moves estimator inputs without a falsifiable task gain —
    rejected as metric churn.
  - hub reads: planner reads hub last_action and discards it; no failing
    behavior exists for hub-driven decisions to fix — dead.
  - phi floor / S,P syn-independence: honest estimator floors on
    step-collinear vectors; lifting them by estimator edits would be
    gaming, not measurement — refused.
  - dead branches: stuck removed in cycle 5; T2 wait rule kept as
    task-contract semantics (unreachable at min distance 7, falsifiable
    by layout change).
- **Verdict**: full cycle, zero verified improvements. Stop condition met.
  No code change; no ADR (no decision taken). Verdict UNKNOWN stands.
- **Gates**: unittest 49/49 OK; aikit check 5/5 PASS (re-verified on the
  committed tree before recording).
- **Commands run**:
  - 100-199 optimality scan (T1 tour / T3 BFS / T2 == 8): all clean.
  - `python -m unittest discover -s tests -t .` -> 49 OK.
  - `python aikit.py check brain` -> 5/5.
- **Final pins**: unittest 49 OK; aikit 5/5; T1 100-seed 1581;
  T2 100-seed 800; T3 100-seed 683 (0-99) with 100-199 fully optimal;
  trap/tour/ablation pins carried; phi 0.0 x3; syn 0.1167/0.1000/0.1229.

## Cycle 7 — measurement-integrity audit and lesion-differential pins

- **Baseline**: 49 tests OK; aikit 5/5; no committed test pins the
  lesion-differential structure (hub/M lesions kill syn; P/S change
  nothing) — verified only in throwaway probes.
- **Gap**: two unexamined risks: (a) an estimator bug would silently
  invalidate every reported number; (b) the integration structure has
  no regression guard — a future change could sever hub/M coupling
  with the suite staying green.
- **Target delta**: estimators match analytic references within stated
  tolerances; 3 new committed tests pin intact/lesioned syn/phi on a
  fixed rig (49 -> 52 tests).
- **Falsifier**: any estimator deviating from its reference, or any pin
  failing on the current tree for a reason other than the intended
  structural assertion.
- **Change** (tests/test_integration_differentials.py only, new file):
  fixed rig (T1 seed 7, 30-step wiring run = 15 steps) asserting signal
  presence (syn 0.1246 > 0.05), phi floor (0.0), hub/M lesion kills
  (syn 0.0 exactly), P/S lesion no-ops (bit-identical to intact).
  No production-code change: estimators verified, not modified.
- **Estimator verification** (probe, N=4000 Gaussian unless noted):
  - MI identical series == marginal entropy (1.6131 == 1.6131).
  - MI independent pair 0.0075 (finite-sample bias, ~0).
  - phi lagged-copy construction 0.5001 == theoretical 1-(1/2)
    (one of two channels coupled); white noise 0.0002 (~0).
  - synergy XOR target 0.6931 == ln 2 exactly; independent target 0.0.
  - gbi(0.2,0.6)=0.5, transfer_gain(10,6)=0.4, recovery(2,10)=0.8 exact.
  - logistic_k perfect step: r2 0.995. permutation_null: constant
    passthrough; uniform-95th 0.9498 (~0.95).
  - Verdict: no deviations; references and implementation agree.
- **After**: 52/52 tests OK; pins green on first run (values measured on
  the fixed rig, then pinned). Sensitivity: the kill assertions fail
  against unlesioned rows by construction (0.1246 vs 0.0); the no-op
  assertions fail if any P/S variance ever enters syn.
- **Ablation**: not a substrate claim; the lesion ops themselves are the
  cuts, now pinned: hub_zero/m0 kill syn to 0.0 while p0/s0 preserve it
  bit-identically — the same differentials the ledger previously
  reported from probes, now regress-proof.
- **Verdict**: harness win (3 pins guarding integration structure) plus
  estimator verification with zero deviations; no emergence claim.
  Verdict UNKNOWN.
- **Gates**: unittest 52/52 OK; aikit check 5/5 PASS (new file clean:
  no opens, no swallows, tempdir + finally).
- **Commands run**:
  - estimator sanity probe (9 analytic checks): all match.
  - lesion pin-measurement probe (fixed rig): structure confirmed.
  - `python -m unittest tests.test_integration_differentials -v` -> 3 OK.
  - `python -m unittest discover -s tests -t .` -> 52 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 8**: unittest 52 OK; aikit 5/5;
  all cycle-6 pins carried; fixed-rig (T1 seed7) syn 0.1246 phi 0.0;
  hub0/m0 syn 0.0; p0/s0 syn bit-identical to intact.

## Cycle 8 — substrate-contract audit: zero verified improvements (STOP)

- **Baseline**: 52 tests OK; aikit 5/5; all prior pins carried.
- **Measure**: reviewed the remaining unaudited contracts — MemoryStore
  recall (FTS5 + LIKE fallback, ordering, limits), telemetry edge paths,
  inventory/demo peripherals — against existing tests (test_memory,
  test_telemetry) and the consumer graph.
- **Find**: no qualifying gap.
  - Recall-quality improvements (e.g. syntax-char sanitization) would
    move a unit number on a path with no in-repo consumer: the planner
    never recalls the store, and routing is optimal on 200/200 seeds
    without it — optimizing an unused path moves no system number
    (dead, one line).
  - Cross-episode store recall wired into planning is the reserved
    lever for a future task family that defeats reactive planning;
    on today's tasks it has zero headroom by measurement (dead).
  - Calibration, P/M redefinition, hub reads, phi floor: rejections
    from cycle 6 stand; nothing changed under them.
  - No estimator, gate, or contract deviation found.
  - NOTE (corrected by cycle 9): this audit covered recall paths but
    not the store open path; corruption recovery was unprobed and
    turned out to be a real gap — see cycle 9.
- **Verdict**: full cycle, zero verified improvements. Stop condition
  met. No code change; no ADR (no decision taken). Verdict UNKNOWN.
- **Gates re-verified on the committed tree**: unittest 52/52 OK;
  aikit check 5/5 PASS.
- **Commands run**:
  - contract review reads (test_memory.py, inventory.py) + consumer
    grep for mean_conf/recall call sites: no downstream consumers.
  - `python -m unittest discover -s tests -t .` -> 52 OK.
  - `python aikit.py check brain` -> 5/5.

## Cycle 9 — corrupt-store quarantine-and-reopen recovery

- **Baseline**: 52 tests OK; aikit 5/5. Corrupt-file fixture (garbage
  bytes): open raises sqlite3.DatabaseError ("file is not a database"),
  recovery 0/1 — plus the failed connection leaks its handle so
  Windows tempdir cleanup fails with PermissionError.
- **Gap**: MemoryStore has no corrupt-quarantine path (PRINCIPLE-013
  requires corrupt -> quarantine for state files). Target: corrupt
  fixture recovers 1/1 with byte-identical quarantine preserved and a
  functional store; healthy files byte-identical behavior.
- **Falsifier**: any existing test red, quarantine bytes differing, or
  recovered store non-functional.
- **Change** (memory/store.py: factored _connect_validated with
  quick_check + _quarantine_corrupt moving file and WAL sidecars,
  recovery_notes() accessor; tests/test_store_recovery.py new):
  open validates, closes the failed connection, quarantines, reopens
  fresh. No new deps; deterministic names (.corrupt, numbered).
- **After**: corrupt fixture opens with count 0, save/recall works,
  quarantine bytes identical, notes record the move; tempdir cleanup
  succeeds (leak gone). Healthy reopen: count preserved, no quarantine
  file, notes empty.
- **Ablation**: not an emergence claim; cut evidence is the pre-change
  tree raising DatabaseError on the identical fixture (measured).
- **Verdict**: robustness win (recovery 0/1 -> 1/1 + leak fixed);
  no emergence claim. Verdict UNKNOWN.
- **Gates**: unittest 54/54 OK; aikit check 5/5 PASS.
- **Commands run**:
  - corrupt-before probe: DatabaseError + PermissionError cascade.
  - `python -m unittest tests.test_store_recovery -v` -> 2 ERROR
    (DatabaseError; missing accessor) before; 2 OK after.
  - `python -m unittest discover -s tests -t .` -> 54 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 10**: unittest 54 OK; aikit
  5/5; all cycle-7 pins carried; corrupt fixture recovers 1/1;
  healthy reopen unchanged.

## Cycle 10 — corrupt-line log behavior: strictness stands (STOP)

- **Baseline**: 54 tests OK; aikit 5/5.
- **Measure**: appended a corrupt line to a 32-record T1 log and read
  it back through every consumer: read_all raises JSONDecodeError,
  bins raises (it reads via read_all), recompute skips the line and
  returns identical numbers (syn 0.1246, n_records 32).
- **Find**: no qualifying gap. The split is the correct contract, not
  a bug: the evidence reader (read_all/bins) fails loud on corruption
  so damaged evidence can never pass silently, while the measurement
  path (recompute) tolerates line damage without moving a number.
  Making read_all skip corrupt lines would trade loud failure for
  silent evidence loss — the opposite of what an eval-evidence log
  must do (dead end with rationale, one line).
- **Verdict**: full cycle, zero verified improvements. Stop condition
  met. No code change; no ADR (no decision taken). Verdict UNKNOWN.
- **Gates re-verified on the committed tree**: unittest 54/54 OK;
  aikit check 5/5 PASS.
- **Commands run**:
  - corrupt-line probe (read_all/bins/recompute): strict/strict/
    tolerant-identical.
  - `python -m unittest discover -s tests -t .` -> 54 OK.
  - `python aikit.py check brain` -> 5/5.
- **Final pins**: unittest 54 OK; aikit 5/5; all cycle-9 pins carried.

## Cycle 11 — swappable model-backend seam + stub protocol pins

- **Baseline**: 54 tests OK; aikit 5/5; Planner has no backend hook
  (new seam tests fail on this tree with TypeError).
- **Gap**: a small model cannot be measured against Brain without a
  runtime-agnostic seam; building the llama.cpp wiring first would
  fuse the repo to one provider.
- **Target delta**: ModelBackend interface + StubBackend + planner
  fallback hook with 3 green protocol tests (54 -> 57); backend-None
  path byte-identical to the rule tree.
- **Falsifier**: any existing test red, or replay/fallback counts off.
- **Change** (models/__init__.py + models/backend.py new; agent.py
  Planner accepts backend, validates tokens against the legal set,
  counts fallbacks; tests/test_model_backend.py new; README tree;
  ADR-012): interface + stub + hook only. No provider, no weights,
  no network.
- **After**: stub replays the rule trace exactly (13/13, 0 fallbacks);
  invalid-token and raising backends fall back 1:1 to the rule trace;
  full suite 57/57.
  Failing-first proof: the 3 tests error on the pre-seam tree
  (TypeError, verified via stash) and pass with the seam.
- **Ablation**: not an emergence claim; the sever-the-backend case is
  the fallback tests themselves (backend cut -> rule carries 100%).
- **Verdict**: seam win with protocol pins; real model delta reserved
  for cycle 12. Verdict UNKNOWN.
- **Gates**: unittest 57/57 OK; aikit check 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_model_backend -v` -> 3 errors
    pre-seam (stash), 3 OK post-seam.
  - `python -m unittest discover -s tests -t .` -> 57 OK.
  - `python aikit.py check brain` -> 5/5.
  - background fetches started (approved): llama.cpp win-cpu zip +
    SmolLM2 Q8 GGUF to user-local cache (outside repo).
- **Pinned regression baselines for cycle 12**: unittest 57 OK; aikit
  5/5; stub replay 13/13 zero-fallback; invalid/raise fallback == steps.

## Cycle 12 — small model before/after: SmolLM2-135M-Q8 vs rule baseline

- **Baseline** (rule planner, pinned): T1-71 16 steps/3.0 reward;
  T2-3 8/1.0; T3-15 13/1.0; T3-65 6/1.0; T3-74 9/1.0. Same rig, same
  seeds, max_steps 200 for the after runs.
- **Gap**: the user asked for a small model run with before/after
  measurement. Approved fetch: llama-server b12110 win-cpu +
  bartowski SmolLM2-135M-Instruct-Q8_0 GGUF (user-local cache, never
  in repo). Raw /completion skips the chat template so the instruct
  model rambles; /v1/chat/completions applies it (locked config:
  temp 0, seed 0, n_predict 24, 60s timeout, port 8174/8175).
- **Target delta**: measure steps/success/reward/fallbacks with the
  model in the loop on 5 trap seeds; determinism repeat on one seed.
- **Falsifier**: any rule pin moves, or model-run numbers irreproducible.
- **Change** (models/llamacpp.py + tests/test_llamacpp.py new; README
  models line; ADR-013): chat-endpoint backend with first-legal-token
  parsing; 3 protocol tests (prompt determinism/content, first-token
  wins, garbage rejected). Failing-first: tests error pre-implem
  (ModuleNotFound), green after.
- **After** (model in loop, temperature 0, fixed seed):
  - T1-71: 200 steps (cap) / 0.0 reward / 13 fallbacks (rule: 16/3.0).
  - T2-3: 8 / 1.0 / 8 fallbacks — identical to rule, model
    contributed zero valid tokens.
  - T3-15: 200 / 0.0 / 1 fallback (rule: 13/1.0).
  - T3-65: 200 / 0.0 / 1 fallback (rule: 6/1.0).
  - T3-74: 200 / 0.0 / 5 fallbacks (rule: 9/1.0).
  - Task success 5/5 -> 1/5; repeat of T3-15 byte-identical
    (variance 0). ~0.12s per call; 21-26s per 200-step run.
- **Ablation**: sever the backend (None) and every rule pin restores
  (tour/trap/total suites green); T2 shows the cut directly —
  fallbacks == steps, so model-present and model-absent are the same
  run. Valid-but-useless model tokens (collect-spam, wait-stands,
  list-echo "up") bypass fallback and cause the truncations.
- **Verdict**: negative result with mechanism: untuned 135M instruct
  emits echo/ramble whose first legal token is state-independent, so
  it cannot steer. No tuning or prompt search performed — recorded
  boundary, not a model verdict. No emergent claim. Verdict UNKNOWN.
- **Gates**: unittest 60/60 OK; aikit check 5/5 PASS (one hygiene
  finding on the way: popen-wait-timeout at the server Popen — fixed
  with a bounded terminate-wait(10)-kill in close() plus a scoped
  allow marker documenting the long-lived-server rationale).
- **Commands run**:
  - background fetches (approved): llama.cpp zip 23.56MB +
    GGUF 138.1MB to user-local cache; extracted, llama-server.exe up
    in 1.6s.
  - raw-output probes (/completion ramble; chat template echo/ramble).
  - `python -m unittest tests.test_llamacpp -v` -> ModuleNotFound
    pre-implem, 3 OK post.
  - rule-vs-model battery (5 seeds) + determinism repeat.
  - `python -m unittest discover -s tests -t .` -> 60 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 13**: unittest 60 OK; aikit
  5/5; model battery numbers above; rule pins unchanged; parse/build
  protocol pinned.

## Cycle 13 — few-shot prompt attempt: negative, model line paused (STOP)

- **Baseline**: cycle-12 model numbers (1/5 success, 4 truncations at
  200/0.0; T2 identical via 8/8 fallbacks).
- **Gap**: zero-shot outputs echo lists and ramble; first-legal-token
  parsing latches onto state-independent words. One bounded fix
  attempted: 2-shot state->action examples in the prompt.
- **Probe**: few-shot output echoes the prompt tail with no action
  token in 24 tokens (parse None -> fallback). Worse parsability,
  zero state-response. No full battery warranted.
- **Verdict**: full cycle, zero verified improvements. Prompt line
  closed; remaining lever is fine-tuning on rule traces (needs
  training-dep approval — TRl/torch training stack not installed —
  and a user call). No code change; no ADR. Verdict UNKNOWN.
- **Gates re-verified on the committed tree**: unittest 60/60 OK;
  aikit check 5/5 PASS.
- **Commands run**:
  - few-shot single-probe (2-shot, T3 state): echo, no action token.
  - `python -m unittest discover -s tests -t .` -> 60 OK.
  - `python aikit.py check brain` -> 5/5.
- **Final pins**: unittest 60 OK; aikit 5/5; all cycle-12 pins carried.

## Cycle 14 — goal-complete model-seam observations and prompts

- **Baseline** (same rig both runs, seeds 0-29 + trap seeds 71/15/65/74):
  - canonical gate: 60 tests OK; aikit check 5/5 PASS.
  - code behavior (backend None): T1-71 16/3.0; T2-3 8/1.0; T3-15 13/1.0;
    T3-65 6/1.0; T3-74 9/1.0; 30-seed totals T1 466 / T2 240 / T3 217.
  - trace internals (fixed rig T1 seed7, 30-step wiring run = 15 steps):
    syn 0.1246, syn_n 0.2489, phi 0.0, n_records 32; hub0/m0 lesion syn
    -> 0.0 exactly; p0/s0 lesion bit-identical to intact.
  - model-seam internals: obs keys {task,x,y,steps,legal} only, no
    target/items_positions/obstacles/cue; build_prompt renders only
    [x,y] + legal with zero goal tokens; collision probe: T3 states
    (target [6,7]/ob [[6,1]]) vs (target [0,0]/ob [[1,1]]) at same
    [5,0]/step 7 produce byte-identical obs and prompt; obs-oracle
    (policy limited to obs channel) truncates 4/4 steerable seeds at
    200 steps with 0.0 reward.
  - model versioning: SmolLM2-135M Q4_K_M present in user-local
    scratch/llm-probe/models (outside repo, hash not pinned in repo);
    live-model battery from cycle 12 (Q8_0, 1/5 success) carried as
    prior; this cycle uses deterministic obs-oracle as the
    seam-integration probe, no live-server run.
- **Gap**: Planner.plan obs omits all goal state and build_prompt
  renders none, so the model integration point carries zero steering
  signal by construction. Targeted audit (grep generate/build_prompt):
  only agent.py constructs obs and only llamacpp.py renders it.
- **Target delta**: obs carries target/items_positions/obstacles/cue;
  prompt mentions them; obs-oracle 200/0.0 x4 -> 16/8/13/6 optimal;
  rule totals and trace numbers byte-identical.
- **Falsifier**: any rule total moves, any trace number moves, or
  oracle still truncates after the change; emergence falsifier:
  minimal-obs ablation must restore truncation or the gain is not
  seam-carried.
- **Change** (agent.py Planner.plan obs build + models/llamacpp.py
  build_prompt only; tests/test_obs_coverage.py new): obs adds target,
  items_positions, obstacles, cue copies when present; prompt appends
  deterministic Target/Items/Obstacles/Cue lines when those keys are
  present, minimal-obs prompts byte-identical. No new deps.
- **After** (identical battery, same seeds):
  - code behavior identical: T1-71 16, T2-3 8, T3-15 13, T3-65 6,
    T3-74 9; 30-seed totals 466/240/217 byte-identical; all runs
    complete with reward.
  - trace identical: fixed-rig syn 0.12455861, syn_n 0.24891688,
    phi 0.0, n_records 32; lesion differentials unchanged
    (hub0/m0 -> 0.0, p0/s0 bit-identical).
  - model-seam fixed: obs carries goal copies; prompt contains
    "[6, 7]" and "[6, 1]" on T3 rig and item coords on T1 rig;
    collision pair now distinct obs and distinct prompts.
  - obs-oracle: T1-71 200 -> 16, T2-3 200 -> 8, T3-15 200 -> 13,
    T3-65 200 -> 6, all done with full reward; 3x repeat on
    T1-71/T3-15 byte-identical (variance 0).
- **Ablation** (integration cut: MinimalStrip removes enriched keys
  before the oracle, same geometry):
  - intact enriched obs: 16/8/13/6 with full reward.
  - stripped minimal obs: 200/200/200/200 with 0.0 reward on all 4.
  - Gain dies with the cut, returns with the restore: the enriched
    obs channel is load-bearing for obs-limited steering.
  - Rule-path control: backend None totals unchanged, so the change
    adds signal without altering the rule policy.
- **Verdict**: seam win with proven obs-integration coupling; no
  emergent claim. Live-model steering still reserved (needs
  fine-tuning per cycle 13). Verdict UNKNOWN.
- **Gates**: unittest 63/63 OK (60 carried + 3 new); aikit check 5/5
  PASS (test, hygiene, guidelines, secrets, compat).
- **Commands run**:
  - `python -m unittest tests.test_obs_coverage -v` -> 3 FAIL before,
    3 OK after.
  - `python -m unittest discover -s tests -t .` -> 60 OK before,
    63 OK after.
  - `python aikit.py check brain` -> 5/5 before and after.
  - rule 5-seed + 30-seed totals probes before/after (identical).
  - fixed-rig recompute probe before/after (syn 0.1246 phi 0.0 both).
  - obs collision probe before (identical) / after (distinct).
  - oracle battery + 3x determinism repeat + MinimalStrip ablation.
- **Pinned regression baselines for cycle 15**: unittest 63 OK; aikit
  5/5; rule totals T1 466 T2 240 T3 217 (30 seeds); trap seeds
  16/8/13/6/9; fixed-rig syn 0.12455861 phi 0.0 n_records 32;
  hub0/m0 syn 0.0 p0/s0 bit-identical; obs-oracle T1-71 16 T2-3 8
  T3-15 13 T3-65 6; minimal-obs ablation 200/0.0 x4.

## Cycle 15 — visit-complete model-seam observations and prompts

- **Baseline** (same rig both runs, cycle-14 pins re-verified):
  - canonical gate: 63 tests OK; aikit check 5/5 PASS.
  - code behavior (backend None): T1-71 16/3.0; T2-3 8/1.0; T3-15
    13/1.0; T3-65 6/1.0; T3-74 9/1.0; 30-seed totals 466/240/217;
    T1-100 total 1581.
  - trace internals (fixed rig T1 seed7): syn 0.12455861 syn_n
    0.24891688 phi 0.0 n_records 32; hub0/m0 -> 0.0; p0/s0 identical.
  - model-seam internals: obs carries goal (target/items/obstacles/
    cue) but no visits; prompt carries Target/Items/Obstacles/Cue
    but no Visits; visit-oracle (obs-limited + visits) truncates
    T3-74 at 200/0.0 vs rule 9/1.0; other 4 oracle seeds optimal
    (16/8/13/6).
  - dead ends, one line each: mean_conf recalibration consumed by
    nothing (churn); hub last_action wiring has no failing behavior
    (dead); persistent recall into planner zero headroom on current
    tasks (reserved); phi floor / P/S independence lifting would be
    gaming (refused); live-model fine-tuning needs torch/TRL stack +
    approval (blocked); T2 wait rule kept as contract semantics.
- **Gap**: Planner computes visits from recent episode memory for
  tie-breaks but omits it from backend obs, so obs-limited policies
  cycle on tie-trap seeds.
- **Target delta**: obs adds sorted visits; prompt renders Visits;
  visit-oracle T3-74 200 -> 9 with other 4 unchanged; rule totals
  and trace byte-identical.
- **Falsifier**: any rule total moves, any trace number moves, or
  T3-74 stays 200; emergence falsifier: visits-stripped ablation
  must restore 200/0.0 on 74 only.
- **Change** (agent.py obs build + models/llamacpp.py build_prompt
  only; tests/test_obs_visits.py new): obs["visits"] = sorted
  [[x, y, count]] when non-empty; prompt appends "Visits: [...]."
  when present, prior prompts byte-identical. No new deps.
- **After** (identical battery, same seeds):
  - code behavior identical: 16/8/13/6/9; totals 466/240/217;
    T1-100 1581; all complete with reward.
  - trace identical: syn 0.12455861 syn_n 0.24891688 phi 0.0
    n_records 32; lesions unchanged.
  - model-seam fixed: obs carries visits {(5,0):2, (4,0):1} on probe
    rig; prompt contains "Visits" and "[5, 0]".
  - visit-oracle: T3-74 200 -> 9, T3-15 13, T3-65 6, T1-71 16,
    T2-3 8, all done with full reward; 3x repeat on 74 byte-identical
    (variance 0).
- **Ablation** (visits-stripped MinimalStrip, same geometry):
  - intact: 9/13/6/16/8 with full reward.
  - stripped: T3-74 200/0.0, other 4 unchanged (13/6/16/8).
  - Gain dies with the cut on the tie-trap only, returns with the
    restore: visits channel load-bearing where lookahead alone
    cycles. Rule None control unchanged.
- **Verdict**: seam win with proven visits-integration coupling; no
  emergent claim. Live-model steering still reserved. Verdict UNKNOWN.
- **Gates**: unittest 66/66 OK (63 carried + 3 new); aikit check 5/5
  PASS.
- **Commands run**:
  - `python -m unittest tests.test_obs_visits -v` -> 3 FAIL before,
    3 OK after.
  - `python -m unittest tests.test_obs_coverage -v` -> 3 OK after.
  - `python -m unittest tests.test_llamacpp -v` -> 3 OK after.
  - `python -m unittest discover -s tests -t .` -> 63 OK before,
    66 OK after.
  - `python aikit.py check brain` -> 5/5 before and after.
  - rule 5-seed + 30-seed + T1-100 probes before/after (identical).
  - fixed-rig recompute before/after (identical).
  - visit-oracle 5-seed + 3x repeat + visits-stripped ablation.
- **Pinned regression baselines for cycle 16**: unittest 66 OK; aikit
  5/5; rule totals 466/240/217; T1-100 1581; trap 16/8/13/6/9;
  fixed-rig syn 0.12455861 phi 0.0 n_records 32; hub0/m0 0.0 p0/s0
  identical; visit-oracle 16/8/13/6/9; visits-stripped ablation
  200/0.0 on 74 only.

## Cycle 16 — episode-memory goal recall for transient dropout

- **Baseline** (same rig/seeds, cycle-15 pins re-verified):
  - canonical: 66 OK; aikit 5/5 PASS.
  - code behavior: T1-71 16/3.0; T2-3 8/1.0; T3-15 13/1.0; T3-65
    6/1.0; T3-74 9/1.0; 30-seed 466/240/217.
  - trace: fixed-rig syn 0.12455861 syn_n 0.24891688 phi 0.0
    n_records 32; hub0/m0 0.0; p0/s0 identical.
  - seam: visit-oracle 5/5 (16/8/13/6/9); goal-oracle 4/4.
  - hidden-dropout probe (new this cycle, plan-time strip with
    memories intact): T3-15 target-stripped 200/0.0 vs intact
    13/1.0; T1-71 items-stripped 200/0.0 vs 16/3.0.
  - dead ends: mean_conf churn; hub no failing behavior; persistent
    recall zero headroom (reserved); phi/P/S gaming refused; live
    fine-tuning blocked; T2 wait kept; energy never binds.
- **Gap**: Planner reads goal keys only from current state; episode
  memory holds ground truth but is ignored for goals (positions
  only for visits).
- **Target delta**: recall missing target/items/obstacles/cue from
  memories; hidden 200 -> 13/16 with standing identical.
- **Falsifier**: standing totals move, any trace number moves, or
  hidden stays 200; emergence falsifier: memory-blind ablation must
  restore 200/0.0.
- **Change** (agent.py Planner.plan only; tests/test_hidden_goal.py
  new): _recall searches provided memories most-recent-first for
  missing keys (absent or None only; empty lists stay); recalled
  values drive rule geometry and backend obs. No world change; no
  new deps.
- **After** (identical battery, same seeds):
  - code identical: 16/8/13/6/9; 466/240/217.
  - trace identical: syn 0.12455861 phi 0.0 n32; lesions unchanged.
  - seam carried: prior oracles unchanged (visit 5/5, goal 4/4).
  - hidden fixed: T3-15 200 -> 13/1.0; T1-71 200 -> 16/3.0; 3x
    repeats byte-identical (variance 0).
- **Ablation** (memory-blind: empty memories with same strip):
  - intact: 13/1.0 with full memories.
  - blind: 200/0.0 with no memories.
  - Gain dies with the cut, returns with the restore: episode
    memory channel load-bearing. Standing None control unchanged.
  - Boundary honestly recorded: probe keeps saved memories full
    (transient dropout); persistent hidden worlds need full-history
    recall plus a new task family — reserved, not claimed.
- **Verdict**: robustness win with proven memory coupling; no
  emergent claim. Verdict UNKNOWN.
- **Gates**: unittest 69/69 OK (66 carried + 3 new); aikit 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_hidden_goal -v` -> 3 FAIL (200/
    0.0) before, 3 OK after.
  - `python -m unittest discover -s tests -t .` -> 66 OK before,
    69 OK after.
  - `python aikit.py check brain` -> 5/5 before and after.
  - standing 5-seed + 30-seed probes before/after (identical).
  - fixed-rig recompute before/after (identical).
  - hidden 2-seed + 3x determinism + memory-blind ablation.
- **Pinned regression baselines for cycle 17**: unittest 69 OK; aikit
  5/5; standing 466/240/217 trap 16/8/13/6/9; fixed-rig syn
  0.12455861 phi 0.0 n32; hub0/m0 0.0 p0/s0 identical; visit-oracle
  5/5; hidden-target 13 hidden-items 16; blind ablation 200/0.0.

## Cycle 17 — full-history episode recall for persistent hidden goals
- **Baseline** (cycle-16 pins re-verified):
  - canonical: 69 OK; aikit 5/5.
  - code: T1-71 16, T2-3 8, T3-15 13, T3-65 6, T3-74 9; 30-seed
    466/240/217.
  - trace: fixed-rig syn 0.12455861 syn_n 0.24891688 phi 0.0 n32;
    hub0/m0 0.0; p0/s0 identical.
  - seam: visit-oracle 5/5; hidden-transient 13/16.
  - persistent-hidden probe (new, HiddenWorld omits target after
    initial state): T3-15 200/0.0 vs intact 13/1.0; T3-65 200/0.0
    vs 6/1.0 with last-5 window.
  - dead ends: mean_conf churn; hub no failing behavior; persistent
    store recall zero headroom (reserved); phi/P/S gaming refused;
    live fine-tuning blocked; T2 wait kept; energy never binds; T1
    items persistent-hidden needs stale-list handling (reserved).
- **Gap**: Agent passes last-5 to Planner; initial-only goals fall
  out after step 5.
- **Target delta**: pass full history; persistent-hidden 200 ->
  13/6 with standing identical; standing trace moves (M[1] depth)
  with hidden gain on same channel.
- **Falsifier**: standing behavior moves, or persistent-hidden stays
  200; emergence falsifier: forced last-5 must restore 200.
- **Change** (agent.py one line; tests/test_recall_depth.py new):
  recall(limit=None) to Planner; visits still last 4; _recall
  searches all. No new deps.
- **After**:
  - code identical: 16/8/13/6/9; 466/240/217.
  - trace: fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0 n32
    (M[1] full depth vs capped; lesions still hold, signal >0.05);
    standing behavior identical so trace move is depth-reporting
    tied to hidden gain, not churn.
  - seam carried: visit 5/5, hidden-transient 13/16 unchanged.
  - persistent-hidden fixed: T3-15 200 -> 13/1.0; T3-65 200 ->
    6/1.0; 3x repeats variance 0.
- **Ablation** (forced last-5 window, same HiddenWorld):
  - intact full: 13/1.0.
  - cut last-5: 200/0.0.
  - Gain dies with the cut, returns with the restore: recall depth
    load-bearing. Standing None control unchanged.
  - Boundary: T1 items persistent-hidden reserved (stale initial
    list after collects).
- **Verdict**: depth win with proven recall-depth coupling; no
  emergent claim. Verdict UNKNOWN.
- **Gates**: unittest 71/71 OK (69 carried + 2 new); aikit 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_recall_depth -v` -> 2 FAIL
    (200/0.0) before, 2 OK after.
  - `python -m unittest discover -s tests -t .` -> 69 OK before,
    71 OK after.
  - `python aikit.py check brain` -> 5/5 before and after.
  - standing 5-seed + 30-seed identical.
  - fixed-rig recompute 0.1246 -> 0.0541 (depth-reporting).
  - persistent-hidden 2-seed + 3x repeats + forced-5 ablation.
- **Pinned regression baselines for cycle 18**: unittest 71 OK; aikit
  5/5; standing 466/240/217 trap 16/8/13/6/9; fixed-rig syn
  0.05411532 syn_n 0.10814360 phi 0.0 n32; hub0/m0 0.0 p0/s0
  identical; visit-oracle 5/5; hidden-transient 13/16;
  persistent-hidden 13/6; forced-5 ablation 200/0.0.

## Cycle 18 — three-step exit lookahead for column-blocking traps
- **Baseline** (cycle-17 pins re-verified):
  - canonical: 71 OK; aikit 5/5.
  - code: T1-71 16, T2-3 8, T3-15 13, T3-65 6, T3-74 9; 30-seed
    466/240/217; 0-99 totals 1581/800/683.
  - trace: fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0 n32;
    hub0/m0 0.0; p0/s0 identical.
  - seam: visit-oracle 5/5; hidden-transient 13/16;
    persistent-hidden 13/6.
  - headroom scan (new, seeds 200-299): T1 0 non-optimal; T2 0;
    T3 2 traps: 202 9 vs 7, 272 16 vs 14 (both +2 column-entry
    detours); current T3 200-299 total 722.
  - dead ends: T1/T2 200-299 clean; mean_conf churn; hub no
    behavior; persistent store zero headroom (reserved); phi/P/S
    gaming refused; live fine-tuning blocked; T2 wait kept; energy
    never binds; T1 items persistent-hidden stale-list reserved.
- **Gap**: depth-2 viability enters blocked columns early.
- **Target delta**: depth 3; 202 9->7, 272 16->14, 200-299 total
  722->718, all other seeds identical.
- **Falsifier**: traps stay, or any 0-29/0-99/100-199 seed moves.
- **Change** (agent.py one constant; tests/test_column_traps.py
  new): _has_exit depth 2->3; visits ordering unchanged. No new
  deps.
- **After**:
  - code: 202 9->7/1.0, 272 16->14/1.0; 30-seed 466/240/217;
    0-99 1581/800/683; 100-199 fully optimal; 200-299 722->718
    with other 98 byte-identical; 3x repeats variance 0.
  - trace: fixed-rig syn 0.05411532 phi 0.0 n32 unchanged; trap
    traces carry behavior delta (steps 9->7/16->14, S errors -2
    each, M counts -2 each).
  - seam carried: visit/hidden/persistent oracles unchanged;
    depth-3 lookahead alone suffices on these traps (blind ==
    intact, like seeds 15/65); visit coupling still pinned by
    seed-74 blind 200.
- **Ablation** (depth revert 3->2 restores 9/16/722; memory-blind
  still truncates seed 74 per carried suite):
  - intact depth-3: 7/14 optimal.
  - depth-2 cut: 9/16 detours (pre-change baseline).
  - column-trap blind: 7/14 (lookahead suffices honestly
    recorded); seed-74 blind: 200/0.0 (visits load-bearing where
    lookahead cycles).
- **Verdict**: efficiency win (-4 steps/100 seeds, 300/300 T3
  seeds optimal across 0-299); no emergent claim. Verdict UNKNOWN.
- **Gates**: unittest 74/74 OK (71 carried + 3 new); aikit 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_column_traps -v` -> 3 FAIL
    (9 vs 7, 722 vs 718) before, 3 OK after (ablation corrected
    to blind==intact with mechanism note).
  - `python -m unittest discover -s tests -t .` -> 71 OK before,
    74 OK after.
  - `python aikit.py check brain` -> 5/5 before and after.
  - 0-29 + 0-99 + 100-199 + 200-299 probes before/after.
  - fixed-rig recompute identical.
  - 2-seed 3x repeats + depth-revert + blind checks.
- **Pinned regression baselines for cycle 19**: unittest 74 OK; aikit
  5/5; standing 466/240/217; 0-99 1581/800/683; T3 200-299 total
  718; trap 16/8/13/6/9 plus column 7/14; fixed-rig syn 0.05411532
  phi 0.0 n32; hub0/m0 0.0 p0/s0 identical.

## Cycle 19 — four-step exit lookahead for adjacent column blocks
- **Baseline** (cycle-18 pins re-verified):
  - canonical: 74 OK; aikit 5/5.
  - code: T1-71 16, T2-3 8, T3-15 13, T3-65 6, T3-74 9, T3-202 7,
    T3-272 14; 30-seed 466/240/217.
  - trace: fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0 n32;
    hub0/m0 0.0; p0/s0 identical.
  - seam: visit-oracle 5/5; hidden-transient 13/16;
    persistent-hidden 13/6.
  - headroom scan (new, seeds 300-399): T1 0 non-optimal; T2 0;
    T3 1 trap: 307 8 vs 6 (target [1,5] behind obstacle [1,4]);
    current T3 300-399 total 673.
  - dead ends: T1/T2 300-399 clean; mean_conf churn; hub no
    behavior; persistent store reserved; phi/P/S refused; live
    fine-tuning blocked; T2 wait kept; energy never binds; T1 items
    persistent-hidden stale-list reserved.
- **Gap**: depth-3 labels free cell (1,3) viable without seeing its
  only exit (1,4) is blocked.
- **Target delta**: depth 4; 307 8->6, 300-399 total 673->671, all
  else identical.
- **Falsifier**: 307 stays 8, or any 0-399 seed moves.
- **Change** (agent.py one constant; tests/test_adjacent_block.py
  new): _has_exit depth 3->4. No new deps.
- **After**:
  - code: 307 8->6/1.0; 30-seed 466/240/217; 0-99 1581/800/683;
    T3 100-199 optimal; T3 200-299 718; T3 300-399 673->671 with
    other 99 identical; 400/400 T3 0-399 optimal; 3x repeats
    variance 0.
  - trace: fixed-rig syn 0.05411532 phi 0.0 n32 unchanged; trap
    trace 8->6 (S -2, M -2).
  - seam carried: all oracles unchanged; depth-4 alone suffices
    here (blind==intact); visits coupling pinned by 74 blind 200.
- **Ablation** (depth revert 4->3 restores 8/673; seed-74 blind 200
  carried):
  - intact depth-4: 6 optimal.
  - depth-3 cut: 8 detour (pre-change baseline).
  - adjacent blind: 6 (lookahead suffices honestly recorded).
- **Verdict**: efficiency win (-2 steps, 400/400 optimal 0-399); no
  emergent claim. Verdict UNKNOWN.
- **Gates**: unittest 77/77 OK (74 carried + 3 new); aikit 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_adjacent_block -v` -> 3 FAIL
    (8 vs 6, 673 vs 671) before, 3 OK after (ablation corrected
    with note).
  - `python -m unittest discover -s tests -t .` -> 74 OK before,
    77 OK after.
  - `python aikit.py check brain` -> 5/5 before and after.
  - 0-29 + 0-99 + 100-199 + 200-299 + 300-399 probes; optimality
    scans 0/100/200/300 all 0 non-optimal after.
  - fixed-rig recompute identical; 3x repeats + revert + blind.
- **Pinned regression baselines for cycle 20**: unittest 77 OK; aikit
  5/5; standing 466/240/217; 0-99 1581/800/683; T3 200-299 718;
  T3 300-399 671; trap 16/8/13/6/9 + column 7/14 + adjacent 6;
  fixed-rig syn 0.05411532 phi 0.0 n32; hub0/m0 0.0 p0/s0
  identical.

## Cycle 20 — blocked-corridor entry deprioritization
- **Baseline** (cycle-19 pins re-verified):
  - canonical: 77 OK; aikit 5/5.
  - code: 8 pins optimal (16/8/13/6/9/7/14/6); 30-seed 466/240/217.
  - trace: fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0 n32;
    hub0/m0 0.0; p0/s0 identical.
  - seam: visit-oracle 5/5; hidden-transient 13/16;
    persistent-hidden 13/6.
  - headroom scan (new, seeds 400-499): T1 0 non-optimal; T2 0;
    T3 1 trap: 479 12 vs 10 (target [3,7] behind obstacle [3,6]);
    current T3 400-499 total 677.
  - dead ends: T1/T2 400-499 clean; mean_conf churn; hub no
    behavior; persistent store reserved; phi/P/S refused; live
    fine-tuning blocked; T2 wait kept; energy never binds; T1 items
    persistent-hidden stale-list reserved; unbounded depth chase
    rejected (corridor rule is O(1), distance-independent).
- **Gap**: goal-column entry with a blocker ahead at any distance;
  depth alone needs unbounded ply.
- **Target delta**: corridor deprioritization; 479 12->10,
  400-499 total 677->675, all else identical.
- **Falsifier**: 479 stays 12, or any 0-499 seed moves.
- **Change** (agent.py _step_toward grouping only;
  tests/test_blocked_corridor.py new): sort viable/dead by
  (enters_blocked, visits) stable; backup unchanged. No new deps.
- **After**:
  - code: 479 12->10/1.0; 30-seed 466/240/217; 0-99 1581/800/683;
    T3 100-199 732; T3 200-299 718; T3 300-399 671; T3 400-499
    677->675 (99 identical); 500/500 T3 0-499 optimal; 3x repeats
    variance 0.
  - trace: fixed-rig syn 0.05411532 phi 0.0 n32 unchanged; trap
    12->10 (S -2, M -2).
  - seam carried: all oracles unchanged; corridor+depth suffices
    (blind==intact); visits pinned by 74 blind 200.
- **Ablation** (corridor-cut = visits-only ordering restores 12/677;
  seed-74 blind 200 carried):
  - intact: 10 optimal.
  - cut: 12 detour (pre-change baseline).
  - corridor blind: 10 (sufficiency honestly recorded).
- **Verdict**: efficiency win (-2 steps, 500/500 optimal 0-499); no
  emergent claim. Verdict UNKNOWN.
- **Gates**: unittest 80/80 OK (77 carried + 3 new); aikit 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_blocked_corridor -v` -> 3 FAIL
    (12 vs 10, 677 vs 675) before, 3 OK after (ablation corrected
    with note).
  - `python -m unittest discover -s tests -t .` -> 77 OK before,
    80 OK after.
  - `python aikit.py check brain` -> 5/5 before and after.
  - 0-29 + 0-99 + 100/200/300/400-range probes; optimality scans
    0/100/200/300/400 all 0 non-optimal after.
  - fixed-rig identical; 3x repeats + cut + blind.
- **Pinned regression baselines for cycle 21**: unittest 80 OK; aikit
  5/5; standing 466/240/217; 0-99 1581/800/683; T3 200-299 718;
  T3 300-399 671; T3 400-499 675; pins 16/8/13/6/9 + 7/14 + 6/10;
  fixed-rig syn 0.05411532 phi 0.0 n32; hub0/m0 0.0 p0/s0
  identical.

## Cycle 22 — generation manifest fingerprints (idea transfer)
- **Source survey** (neurocore, research-engine, Atlas, lattice,
  modelduck, chatduck, crucible, lacon READMEs + modelduck idea
  audit/implement lists + crucible/lacon/lattice design notes):
  - modelduck: determinism lockdown (batch-1 + triple-run),
    generation-manifest fingerprints, quant-aware memory-fit
    preflight, GGUF preflight, per-model template registry, tune
    gate (paired gain, early stop, unseen items), provenance
    receipts, bench test-hash discipline.
  - crucible: freeze split first (overlap 0 or exit 1),
    train/holdout separation (never grade own homework),
    train-only analyst API + audit, random-patch control, sanity
    cap, frontier floor, WSP column-edit verdict (WIN needs >=10pp
    vs base AND >=5pp vs best of 3 randoms).
  - lacon: letter budget + cheapest thought, recursive
    split/recurse/merge with cap, frozen alphabet, What/Why/Fix
    exit codes.
  - lattice: provenance-first claims (exact quote + locator),
    token-frugal external context (index -> snippets w/ stable ref
    -> full text on drill), snapshot diffing as gate (exit 1 when
    differ), evidence matrix + consensus score.
- **Gap**: Brain's same-prompts gate proof is textual; no
  fingerprint binds a backend proposal to the exact bytes the
  model saw, so prompt-set identity across batteries is asserted,
  not hashed.
- **Target delta**: manifest module + backend recorder + 6-test
  probe; standing behavior and trace byte-identical; determinism
  variance 0; sensitivity (prompt/visits change -> digest change).
- **Falsifier**: standing totals move, trace numbers move, or
  same-input manifests differ across repeats.
- **Change** (models/manifest.py new; models/llamacpp.py recorder:
  __init__ slot + per-generate fingerprint, None-safe;
  tests/test_manifest.py new): canonical JSON SHA-256 over
  {model_id, checkpoint label, prompt, observation, sampling};
  prompt_set_manifest sorted battery digest. No new deps; no
  weights in repo (labels only). No ADR beyond ADR-021.
- **Baseline** (cycle-20 pins re-verified): 80 OK; 5/5; 9 pins;
  30-seed 466/240/217; fixed-rig syn 0.05411532 phi 0.0 n32;
  probe gap: models/manifest absent (import error, no versioning).
- **After**:
  - code identical: 30-seed 466/240/217; all 80 carried tests pass.
  - trace identical: syn 0.05411532 phi 0.0 n32; lesions unchanged.
  - seam versioned: determinism 4x repeat byte-identical
    (variance 0); enriched-vs-minimal and visits-change digests
    differ; planner obs->prompt->manifest chain stable;
    prompt-set digest order-independent; backend slot present.
- **Ablation** (remove models/manifest.py): test_manifest errors
  on import (6/6 uncollectable); restore returns 6/6 OK. Probe AND
  versioning die with the cut, return with the restore.
- **Verdict**: provenance win (same-prompts proof is now hashed);
  no emergent claim. Verdict UNKNOWN.
- **Gates**: unittest 86/86 OK (80 carried + 6 new); aikit 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_manifest -v` -> 6 OK (module
    absent before = import error).
  - `python -m unittest discover -s tests -t .` -> 80 OK before,
    86 OK after.
  - `python aikit.py check brain` -> 5/5 before and after.
  - standing 30-seed + fixed-rig recompute identical.
  - manifest removal/restore ablation.
- **Pinned regression baselines for cycle 23**: unittest 86 OK; aikit
  5/5; standing 466/240/217; 0-99 1581/800/683; T3 200-299 718;
  T3 300-399 671; T3 400-499 675; pins 16/8/13/6/9 + 7/14 + 6/10;
  fixed-rig syn 0.05411532 phi 0.0 n32; hub0/m0 0.0 p0/s0
  identical; manifest determinism 4x variance 0.

## Cycle 23 — frozen holdout split 500-599 (idea transfer)
- **Source**: Crucible frozen splits + train/holdout separation (second
  transfer after cycle-22 ModelDuck manifests; other surveyed ideas
  remain backlog: ModelDuck tune gate/quota ladder, Lattice
  token-frugal context + snapshot diffing, Lacon budgets).
- **Gap**: probe seeds 0-499 drove every fix, but verified-optimal
  wider ranges had no pins; a future change could move holdout seeds
  while all probe tests stay green.
- **Target delta**: freeze 500-599 with exact totals (T1 1581 / T2 800
  / T3 738); no source change; standing behavior and trace
  byte-identical.
- **Falsifier**: standing totals move, trace numbers move, or the
  holdout pin fails on the intact tree.
- **Change** (tests/test_holdout_500s.py new only; ADR-022): exact
  totals over 300 holdout episodes. No source diff; no new deps.
- **Baseline** (cycle-22 pins re-verified): 86 OK; 5/5; 30-seed
  466/240/217; fixed-rig syn 0.05411532 phi 0.0 n32; holdout audit
  totals computed T1 1581 / T2 800 / T3 738 (500-599 all optimal,
  11 blocked-corridor layouts present incl. 560, a 307-twin).
- **After**:
  - code identical: 30-seed 466/240/217; all 86 carried tests pass.
  - trace identical: syn 0.05411532 phi 0.0 n32; lesions unchanged.
  - holdout pinned: 87/87 with T1 1581 / T2 800 / T3 738 (300
    episodes, 0.345s).
- **Ablation** (corridor-cut = visits-only ordering, source
  temporarily reverted then restored byte-identical):
  - intact: holdout T3 738; 479 10/1.0; 400-499 total 675.
  - cut: holdout T3 742 (+4 across holdout corridor layouts);
    479 12/1.0; 400-499 total 677.
  - Behavior AND trace-relevant totals die with the cut, return
    with the restore: the holdout pin is load-bearing for shipped
    corridor/depth integrations, not vacuous.
- **Verdict**: provenance win (frozen split regress-proofs 600
  episodes of verified optimality); no emergent claim. Verdict
  UNKNOWN.
- **Gates**: unittest 87/87 OK (86 carried + 1 new); aikit 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_holdout_500s -v` -> 1 OK
    (pin computed from intact-tree audit).
  - corridor-cut: holdout + corridor tests 4 FAIL (742 vs 738,
    12 vs 10, 677 vs 675); restore -> all OK.
  - `python -m unittest discover -s tests -t .` -> 86 OK before,
    87 OK after.
  - `python aikit.py check brain` -> 5/5 before and after.
  - standing 30-seed + fixed-rig identical; git status shows test
    file only (no source diff).
- **Pinned regression baselines for cycle 24**: unittest 87 OK; aikit
  5/5; standing 466/240/217; 0-99 1581/800/683; T3 200-299 718;
  T3 300-399 671; T3 400-499 675; holdout 500-599 1581/800/738;
  pins 16/8/13/6/9 + 7/14 + 6/10; fixed-rig syn 0.05411532 phi 0.0
  n32; hub0/m0 0.0 p0/s0 identical; manifest determinism variance 0.

## Cycle 21 — full audit, zero verified improvements (STOP)
- **Baseline** (cycle-20 pins re-verified):
  - canonical: 80 OK; aikit 5/5.
  - code: 9 pins optimal; 30-seed 466/240/217.
  - trace: fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0 n32;
    hub0/m0 0.0; p0/s0 identical.
  - seam: visit-oracle 5/5; hidden-transient 13/16;
    persistent-hidden 13/6.
  - audit scans (new): T1/T2/T3 500-599 all optimal (0 traps);
    T1/T2/T3 600-999 all optimal (0 traps); 1000/1000 T3 seeds
    optimal across 0-999; 400/400 T1+T2 across 600-999 optimal.
  - substrate re-read: planner/plan.py tracker (mark_fail/recover
    never used in production, unit-covered only); self_model/model.py
    counters (never read by planner); telemetry/log.py bins (strict,
    pinned); inventory/demo peripherals (no task numbers).
  - dead ends, one line each: T1/T2/T3 500-999 fully optimal (no
    routing headroom 0-999); mean_conf consumed by nothing (churn);
    hub last_action no failing behavior (dead); persistent store
    recall zero headroom on visible tasks (reserved); phi/P/S
    lifting would be gaming (refused); live fine-tuning needs
    torch/TRL + approval (blocked); T2 wait kept (contract); energy
    never binds; T1 items persistent-hidden stale-list reserved
    (needs new family + collected-filtering).
- **Gap**: none qualifies. Routing optimal 0-999 on all tasks;
  every remaining candidate is dead, refused, blocked, or reserved
  (see dead ends). No depth chase (corridor rule already
  distance-independent); no metric edits (would be gaming); no new
  task family in an audit cycle (scope expansion, not a gap fix).
- **Target delta**: none. Falsifier is moot: any change would need a
  failing eval first, and none exists.
- **Change**: none. No code, no harness, no ADR (audit result, not
  a design decision).
- **After**: identical battery re-verified — 80 OK, T3-0-99 683,
  T1-100 1581, aikit 5/5. No deltas, variance not applicable.
- **Ablation**: none (no integration claim).
- **Verdict**: full cycle with zero verified improvements. Stopping
  per goal rule (allowed stop: told to stop, zero-findings cycle,
  or unfixable gate failure). Verdict STOP.
- **Gates**: unittest 80/80 OK; aikit 5/5 PASS (re-verified, no
  changes).
- **Commands run**:
  - `python -m unittest discover -s tests -t .` -> 80 OK.
  - `python aikit.py check brain` -> 5/5.
  - T1/T2/T3 500-599 + 600-999 optimality scans (all 0 traps).
  - standing pins re-verified (T3-0-99 683, T1-100 1581).
- **Pinned regression baselines carried (no new pins)**: unittest 80
  OK; aikit 5/5; standing 466/240/217; 0-99 1581/800/683;
  T3 200-299 718; T3 300-399 671; T3 400-499 675; pins
  16/8/13/6/9 + 7/14 + 6/10; fixed-rig syn 0.05411532 phi 0.0 n32;
  hub0/m0 0.0 p0/s0 identical.

## Cycle 24 — triple-run repro gate (idea transfer)
- **Source**: ModelDuck determinism lockdown (IDEA-1627 batch-1 +
  triple-run) and its --deterministic repro mode (each variant 3x
  with noise-floor report); third transfer after cycle-22 manifests
  and cycle-23 frozen split.
- **Gap**: variance-0 replay was recorded ad hoc per cycle but never
  gated; future nondeterminism (ordering, clock, RNG) could hide.
- **Target delta**: 9 pin seeds x 3 runs byte-identical action
  sequences (counts, rewards, SHA-256); no source change.
- **Falsifier**: standing totals move, trace numbers move, or any
  repeat diverges.
- **Change** (tests/test_repro.py new only; ADR-023): hashed
  canonical action sequences over 27 episodes (0.034s). No source
  diff; no new deps.
- **Baseline** (cycle-23 pins re-verified): 87 OK; 5/5; 30-seed
  466/240/217; fixed-rig syn 0.05411532 phi 0.0 n32.
- **After**:
  - code identical: 30-seed 466/240/217; all 87 carried tests pass.
  - trace identical: syn 0.05411532 phi 0.0 n32; lesions unchanged.
  - repro pinned: 88/88 with 27/27 repeats byte-identical
    (variance 0).
- **Ablation / sensitivity** (honestly recorded):
  - routing-cut (corridor removal) does NOT break this gate by
    design (deterministic 12-step vs 10-step replays agree with
    themselves) — value pins live in trap/range tests.
  - single-action perturbation flips the fingerprint
    (99aa6b.. vs 21dcfa.., differ True): the exact-equality check
    is action-sensitive, not vacuous.
  - decision paths verified RNG/clock/set-iteration free by grep
    (no import random/time, no set()/hash() in agent.py).
- **Verdict**: harness win (replay determinism now gated, not just
  noted); no emergent claim. Verdict UNKNOWN.
- **Gates**: unittest 88/88 OK (87 carried + 1 new); aikit 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_repro -v` -> 1 OK (27 episodes).
  - corridor-cut check: repro still OK (variance gate, not value
    gate — recorded, not hidden).
  - single-action fingerprint flip probe (differ True).
  - `python -m unittest discover -s tests -t .` -> 87 OK before,
    88 OK after.
  - `python aikit.py check brain` -> 5/5 before and after.
  - standing 30-seed identical; git status shows test file only.
- **Pinned regression baselines for cycle 25**: unittest 88 OK; aikit
  5/5; standing 466/240/217; 0-99 1581/800/683; T3 200-299 718;
  T3 300-399 671; T3 400-499 675; holdout 500-599 1581/800/738;
  pins 16/8/13/6/9 + 7/14 + 6/10; fixed-rig syn 0.05411532 phi 0.0
  n32; hub0/m0 0.0 p0/s0 identical; manifest + repro determinism
  variance 0.

## Cycle 25 — exhaustive T3 config coverage (idea transfer)
- **Source**: Lattice evidence matrix + coverage gaps (fourth transfer
  after ModelDuck manifests, Crucible holdout, ModelDuck repro).
- **Gap**: T3 pins sampled seeds 0-999 (1000 of 3906 configs); most of
  the one-target-one-obstacle family unverified.
- **Target delta**: enumerate all 3906 (target, obstacle) pairs,
  assert per-config BFS-optimality + grand total; no source change.
- **Falsifier**: standing totals move, trace numbers move, or any
  config non-optimal on the intact tree.
- **Change** (tests/test_exhaustive_t3.py new only; ADR-024):
  _ForcedLayoutWorld subclass hook (no cross-module private writes;
  guidelines gate refused the direct version); per-config equality
  + total 27860; 1.3s. T1 exhaustive (39711/39711 optimal) and T2
  2/2 recorded as one-off audit evidence; live gate keeps 100-seed
  + holdout pins for T1 (40s+ gate cost refused). No new deps.
- **Baseline** (cycle-24 pins re-verified): 88 OK; 5/5; 30-seed
  466/240/217; fixed-rig syn 0.05411532 phi 0.0 n32.
- **After**:
  - code identical: 30-seed 466/240/217; all 88 carried tests pass.
  - trace identical: syn 0.05411532 phi 0.0 n32 (no source diff).
  - coverage proven: 3906/3906 optimal, total 27860; T1 audit
    39711/39711 optimal; seed sampling retired as the coverage
    argument for T3.
- **Ablation** (corridor-cut, source reverted then restored
  byte-identical):
  - intact: 3906 optimal, total 27860.
  - cut: 21 non-optimal configs, total 27902 (+42).
  - Behavior AND config totals die with the cut, return with the
    restore: the battery catches 21 traps where seed sampling
    caught a handful.
- **Verdict**: coverage win (exhaustive proof for the trap-bearing
  family); no emergent claim. Verdict UNKNOWN.
- **Gates**: unittest 89/89 OK (88 carried + 1 new); aikit 5/5 PASS
  (after subclass-hook rewrite; direct private writes failed the
  guidelines gate with 3 PRINCIPLE-009 R5 findings).
- **Commands run**:
  - `python -m unittest tests.test_exhaustive_t3 -v` -> 1 OK (1.3s).
  - corridor-cut exhaustive probe: 21 bad, 27902 vs 27860; restore
    -> all optimal.
  - `python -m unittest discover -s tests -t .` -> 88 OK before,
    89 OK after.
  - `python aikit.py check brain` -> 4/5 then 5/5 after rewrite.
  - standing 30-seed identical; T1 39711 audit scan (all optimal).
- **Pinned regression baselines for cycle 26**: unittest 89 OK; aikit
  5/5; standing 466/240/217; 0-99 1581/800/683; T3 200-299 718;
  T3 300-399 671; T3 400-499 675; holdout 500-599 1581/800/738;
  exhaustive T3 3906/3906 total 27860; pins 16/8/13/6/9 + 7/14 +
  6/10; fixed-rig syn 0.05411532 phi 0.0 n32; hub0/m0 0.0 p0/s0
  identical; manifest + repro determinism variance 0.

## Cycle 26 — executable negative controls (idea transfer)
- **Source**: research-engine kill-test discipline (EVID-008/009: a test
  must be able to fail; verified tests need controls; a control that
  never fails errors). Fifth transfer after ModelDuck manifests,
  Crucible holdout, ModelDuck repro, Lattice exhaustive coverage.
- **Gap**: trap/range/holdout tests pin intact optimality, but the
  failing side lived only in one-off manual cut runs; a future change
  could neuter a probe silently with all tests still green.
- **Target delta**: permanent in-tree negative control with pinned
  failing signatures (479 12 vs 10; holdout-500s T3 742 vs 738) plus
  engagement proof; extract-method refactor only, no behavior change.
- **Falsifier**: standing totals move, trace numbers move, or the
  patched control unexpectedly optimal (corridor no longer
  load-bearing).
- **Change** (agent.py extract _enters_blocked_corridor to module
  level; tests/test_negative_control.py new; ADR-025): mock.patch to
  False reproduces visits-only ordering (pre-cycle-20 semantics,
  depth kept 4) from production code — zero duplication. No behavior
  change; no new deps.
- **Baseline** (cycle-25 pins re-verified): 89 OK; 5/5; 30-seed
  466/240/217; fixed-rig syn 0.05411532 phi 0.0 n32.
- **After**:
  - code identical: 30-seed 466/240/217; all 89 carried tests pass
    (refactor verified by corridor/holdout/trap/exhaustive suites).
  - trace identical: syn 0.05411532 phi 0.0 n32; lesions unchanged.
  - control pinned: 91/91 with patched cut 479=12 + holdout T3=742
    vs intact 10/738; call_count>0 engagement proven.
- **Ablation**: the control test IS the standing ablation — patched
  cut fails optimality with pinned signatures (12, 742); unpatched
  full suite green. Routing-cut N/A by design for repro (variance
  gate); value pins live in trap/range/holdout tests.
- **Verdict**: harness win (failing side now gated, not ritual);
  no emergent claim. Verdict UNKNOWN.
- **Gates**: unittest 91/91 OK (89 carried + 2 new); aikit 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_negative_control -v` -> 2 OK.
  - `python -m unittest discover -s tests -t .` -> 89 OK before,
    91 OK after.
  - `python aikit.py check brain` -> 5/5 before and after.
  - standing 30-seed + fixed-rig identical.
- **Pinned regression baselines for cycle 27**: unittest 91 OK; aikit
  5/5; standing 466/240/217; 0-99 1581/800/683; T3 200-299 718;
  T3 300-399 671; T3 400-499 675; holdout 500-599 1581/800/738;
  exhaustive T3 3906/3906 total 27860; corridor-cut control 12/742;
  pins 16/8/13/6/9 + 7/14 + 6/10; fixed-rig syn 0.05411532 phi 0.0
  n32; hub0/m0 0.0 p0/s0 identical; manifest + repro determinism
  variance 0.

## Cycle 27 — random-policy floor as a verdict control (idea transfer)
- **Source**: Crucible random-patch controls (sixth transfer; remaining
  backlog: ModelDuck tune gate/quota ladder, Lattice token-frugal
  context + snapshot diffing, Lacon budgets — all dead on arrival for
  stdlib Brain: no tunable settings, no memory pressure, no
  unmeasured tokens; training-stack items blocked).
- **Gap**: blind ablations sever memory but keep lookahead, so nothing
  quantified how far the shipped planner stands above chance.
- **Target delta**: best-of-3 seeded randoms on 9 pins; rule must win
  by pre-registered margins (steps x10, reward +5). No source change.
- **Falsifier**: standing totals move, trace numbers move, or random
  meets the margins.
- **Change** (tests/test_random_floor.py new only; ADR-026): uniform
  RandomBackend over legal actions, seeds 9001-9003, 27 episodes +
  determinism check (~4s). Pre-registered thresholds, not fitted.
  No source diff; no new deps.
- **Baseline** (cycle-26 pins re-verified): 91 OK; 5/5; 30-seed
  466/240/217; fixed-rig syn 0.05411532 phi 0.0 n32; random floor
  measured: best 1271 steps / 5.0 reward vs rule 89 / 11.0.
- **After**:
  - code identical: 30-seed 466/240/217; all 91 carried tests pass.
  - trace identical: syn 0.05411532 phi 0.0 n32; lesions unchanged.
  - floor pinned: 93/93 with rule 89/11.0 beating best random
    1271/5.0 by 14x steps and +6 reward (margins x10/+5 held).
- **Ablation / sensitivity** (no source touched):
  - memory-blind planner as degraded variant: 280 steps / 10.0
    reward — fails the steps margin (280x10 > 1271) while passing
    reward: the verdict binds on efficiency, exactly as designed,
    proving it discriminates planner quality, not just code
    presence.
- **Verdict**: control win (chance floor now gated); no emergent
  claim. Verdict UNKNOWN.
- **Gates**: unittest 93/93 OK (91 carried + 2 new); aikit 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_random_floor -v` -> 2 OK.
  - blind-vs-random margin probe (fails steps margin as designed).
  - `python -m unittest discover -s tests -t .` -> 91 OK before,
    93 OK after.
  - `python aikit.py check brain` -> 5/5 before and after.
  - standing 30-seed + fixed-rig identical.
- **Pinned regression baselines for cycle 28**: unittest 93 OK; aikit
  5/5; standing 466/240/217; 0-99 1581/800/683; T3 200-299 718;
  T3 300-399 671; T3 400-499 675; holdout 500-599 1581/800/738;
  exhaustive T3 3906/3906 total 27860; corridor-cut control 12/742;
  random floor best 1271/5.0 vs rule 89/11.0 (margins x10/+5); pins
  16/8/13/6/9 + 7/14 + 6/10; fixed-rig syn 0.05411532 phi 0.0 n32;
  hub0/m0 0.0 p0/s0 identical; manifest + repro determinism
  variance 0.

## Cycle 28 — backfill range pins 0-199 (idea transfer)
- **Source**: Lattice snapshot-diffing, completion pass: audit mapped
  every asserted total and found four ledger-verified numbers with no
  test pins. Seventh transfer overall.
- **Gap**: T3 0-99 (683), T3 100-199 (732), T2 0-99 (800), T1 100-199
  (1646) verified in cycles 3/5/6 and carried as prose; a drift in
  the most-exercised ranges would pass all gates.
- **Target delta**: one pin test, four exact totals, 400 episodes in
  0.4s. No source change.
- **Falsifier**: standing totals move, trace numbers move, or any
  range total differs on the intact tree.
- **Change** (tests/test_range_pins_0_199.py new only; ADR-027):
  exact totals over 0-99/100-199 ranges. T1 100-199 sum differs per
  range (1646 vs 1581) — sums are layout-driven, optimality is
  per-seed tour+3 (pinned/audited separately). No source diff.
- **Baseline** (cycle-27 pins re-verified): 93 OK; 5/5; 30-seed
  466/240/217; fixed-rig syn 0.05411532 phi 0.0 n32; missing totals
  measured on intact tree (683/732/800/1646).
- **After**:
  - code identical: 30-seed 466/240/217; all 93 carried tests pass.
  - trace identical: syn 0.05411532 phi 0.0 n32; lesions unchanged.
  - matrix complete: 94/94 with all ledger totals now asserted
    (30-seed, 0-99, 100-199, 200-299, 300-399, 400-499, 500-599,
    exhaustive T3).
- **Ablation / sensitivity** (no source touched):
  - memory-blind cut moves T3 0-99 683 -> 874 (+191 via seed-74
    truncation): the new pins catch memory-coupling regressions.
  - corridor-cut sensitivity stays carried by 200+/holdout pins
    (738->742) — sensitivity is partitioned by range, honestly
    recorded.
- **Verdict**: provenance win (snapshot matrix complete); no
  emergent claim. Verdict UNKNOWN.
- **Gates**: unittest 94/94 OK (93 carried + 1 new); aikit 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_range_pins_0_199 -v` -> 1 OK.
  - blind-cut T3-0-99 probe: 874 vs 683 (catches coupling loss).
  - `python -m unittest discover -s tests -t .` -> 93 OK before,
    94 OK after.
  - `python aikit.py check brain` -> 5/5 before and after.
  - standing 30-seed + fixed-rig identical.
- **Pinned regression baselines for cycle 29**: unittest 94 OK; aikit
  5/5; standing 466/240/217; 0-99 1581/800/683; T1 100-199 1646;
  T3 100-199 732; T3 200-299 718; T3 300-399 671; T3 400-499 675;
  holdout 500-599 1581/800/738; exhaustive T3 3906/3906 total
  27860; corridor-cut control 12/742; random floor best 1271/5.0
  vs rule 89/11.0 (margins x10/+5); pins 16/8/13/6/9 + 7/14 +
  6/10; fixed-rig syn 0.05411532 phi 0.0 n32; hub0/m0 0.0 p0/s0
  identical; manifest + repro determinism variance 0.

## Cycle 29 — hash-chained telemetry (idea transfer)
- **Source**: Assay hash-chained evidence ledger + retrospective
  review (eighth transfer; remaining backlog re-audited below).
- **Gap**: telemetry records were tamper-silent — recompute, bins,
  and strict read_all never check integrity, so a hand-edited log
  reads back without complaint.
- **Target delta**: prev+digest on every record + verify_chain with
  named-defect findings; standing behavior and trace byte-identical
  (additive keys, schema stays 2).
- **Falsifier**: standing totals move, trace numbers move, existing
  telemetry tests break, or any tamper class passes verify
  silently.
- **Change** (telemetry/log.py: chain fields + _head tracking +
  verify_chain; tests/test_chain.py new 6 tests; ADR-028): SHA-256
  over canonical JSON without digest; GENESIS first link,
  LEGACY-anchored continuation onto old tails; first-defect naming
  (corrupt-line, unchained-record, edited-record,
  reordered-record, broken-link); seq intentionally unchecked
  (shared action/result seqs, verdict -1 — order rides the chain).
  No new deps.
- **Baseline** (cycle-28 pins re-verified): 94 OK; 5/5; 30-seed
  466/240/217; fixed-rig syn 0.05411532 phi 0.0 n32; gap proven:
  verify_chain absent (import error), records digest-free.
- **After**:
  - code identical: 30-seed 466/240/217; all 94 carried tests pass
    (roundtrip/bins/strictness untouched by additive keys).
  - trace identical: syn 0.05411532 phi 0.0 n32; lesions unchanged.
  - evidence chained: intact 3-record log verifies ok with head ==
    last digest and GENESIS-linked prevs; real 32-record run
    verifies clean.
- **Ablation** (5 tamper classes, no source revert needed — each is
  a failing control by construction):
  - edit middle record -> edited-record:1.
  - delete middle -> broken-link (prev matches nothing).
  - swap last two -> reordered-record (prev matches a later
    digest).
  - digest-free legacy line -> unchained-record:0.
  - non-JSON line -> corrupt-line:1.
  - All fail loudly with named findings; intact passes.
- **Verdict**: provenance win (evidence integrity now checked, not
  asserted); no emergent claim. Verdict UNKNOWN.
- **Gates**: unittest 100/100 OK (94 carried + 6 new); aikit 5/5.
- **Commands run**:
  - `python -m unittest tests.test_chain -v` -> 6 OK.
  - `python -m unittest discover -s tests -t .` -> 94 OK before,
    100 OK after.
  - `python aikit.py check brain` -> 5/5 before and after.
  - standing 30-seed + fixed-rig + real-run verify identical.
- **Pinned regression baselines for cycle 30**: unittest 100 OK;
  aikit 5/5; standing 466/240/217; 0-99 1581/800/683; T1 100-199
  1646; T3 100-199 732; T3 200-299 718; T3 300-399 671; T3 400-499
  675; holdout 500-599 1581/800/738; exhaustive T3 3906/3906
  total 27860; corridor-cut control 12/742; random floor best
  1271/5.0 vs rule 89/11.0 (margins x10/+5); chain intact ok +
  5 named tamper findings; pins 16/8/13/6/9 + 7/14 + 6/10;
  fixed-rig syn 0.05411532 phi 0.0 n32; hub0/m0 0.0 p0/s0
  identical; manifest + repro determinism variance 0.
- **Backlog re-audit (all 8 surveyed projects)**: implemented 8
  (manifests, holdout, repro, exhaustive T3, negative controls,
  random floor, range pins, hash chain). Dead on arrival for
  stdlib Brain (re-confirmed): ModelDuck tune gate/quota ladder
  and memory-fit (no tunable settings, no memory pressure);
  Lattice token-frugal context (full-history recall carries all
  goal keys on standing tasks — budgeting would save nothing);
  Lacon budgets (2^4 search bound already caps planner);
  ChatDuck/Atlas/NeuroCore server-side ideas (need
  network/GPU/models); NeuroCore model_limits (prompts never near
  any ceiling); Atlas quality scores (no gap to move one).
  Blocked: anything needing torch/TRL (fine-tuning) or live-model
  server runs as gates.

## Cycle 30 — golden trace hashes (idea transfer)
- **Source**: Keystone --simulate --expect-hash (pinned simulation
  hash). Ninth transfer; second sweep also covered noesis (state
  machines already deterministic/headless here), PNN (domain drug
  work, no transfer), foundry (generator+validator gatekeeper —
  subsumed by exhaustive coverage), harness (provider-by-config,
  no behavioral delta), meridian/tessera/weft (browser games),
  keystone 3D (needs GPU/numpy).
- **Gap**: step counts and rewards pin outcomes, but a
  behavior-neutral path swap at identical counts would drift
  silently past all 100 tests.
- **Target delta**: SHA-256 over canonical action sequences for the
  9 pin seeds, computed once on the intact tree; 0.014s.
- **Falsifier**: standing totals move, trace numbers move, or any
  pin path differs.
- **Change** (tests/test_golden_traces.py new only; ADR-029):
  GOLDEN map + one equality test per seed; regeneration rule is
  deliberately manual (reviewed edit, no auto-update flag) so
  goldens can never rebaseline a red tree green. No source diff;
  no new deps.
- **Baseline** (cycle-29 pins re-verified): 100 OK; 5/5; 30-seed
  466/240/217; fixed-rig syn 0.05411532 phi 0.0 n32.
- **After**:
  - code identical: 30-seed 466/240/217; all 100 carried tests pass.
  - trace identical: syn 0.05411532 phi 0.0 n32; lesions unchanged.
  - paths pinned: 101/101 with 9/9 golden hashes exact.
- **Ablation / sensitivity** (no source touched):
  - single-action flip changes the fingerprint (proven cycle 24:
    99aa6b.. vs 21dcfa.., differ True).
  - corridor-cut moves 479 10->12 steps, which necessarily changes
    its hash (different-length list) — the golden gate inherits
    every routing cut's sensitivity on top of count pins.
- **Verdict**: provenance win (paths now pinned, not just counts);
  no emergent claim. Verdict UNKNOWN.
- **Gates**: unittest 101/101 OK (100 carried + 1 new); aikit 5/5.
- **Commands run**:
  - `python -m unittest tests.test_golden_traces -v` -> 1 OK.
  - `python -m unittest discover -s tests -t .` -> 100 OK before,
    101 OK after.
  - `python aikit.py check brain` -> 5/5 before and after.
  - standing 30-seed + fixed-rig identical.
- **Pinned regression baselines for cycle 31**: unittest 101 OK; aikit
  5/5; standing 466/240/217; 0-99 1581/800/683; T1 100-199 1646;
  T3 100-199 732; T3 200-299 718; T3 300-399 671; T3 400-499 675;
  holdout 500-599 1581/800/738; exhaustive T3 3906/3906 total
  27860; corridor-cut control 12/742; random floor best 1271/5.0
  vs rule 89/11.0 (margins x10/+5); chain intact ok + 5 named
  tamper findings; golden 9/9 paths; pins 16/8/13/6/9 + 7/14 +
  6/10; fixed-rig syn 0.05411532 phi 0.0 n32; hub0/m0 0.0 p0/s0
  identical; manifest + repro determinism variance 0.

## Cycle 31 — policy citation in run headers (idea transfer)
- **Source**: Assay per-record policy citation + research-engine 3b
  evidence binding (tenth transfer; deep read of MECHANICS.md also
  re-audited the remainder: golden-path/demo, deterministic
  projections, revisions, cascades, UNKNOWN, screening, digests,
  backup trails, stats, search, duplicates, calibration — all
  already embodied, dead, or blocked for stdlib Brain as recorded
  in cycle 29).
- **Gap**: run_task_logged wrote headers with manifest_sha256 always
  None and no policy reference — a log could not say which
  configuration produced it.
- **Target delta**: headers cite planner name + config digest + model
  label, all covered by the hash chain; behavior and trace
  byte-identical (additive header keys).
- **Falsifier**: standing totals move, trace numbers move, existing
  telemetry tests break, or a header citation mismatches.
- **Change** (agent.py PLANNER_POLICY + policy_digest() +
  model_label() + header call; telemetry/log.py optional
  policy/policy_sha256/model header fields; tests/test_policy_binding.py
  new 4 tests; ADR-030): declared-config digest (not code bytes), so
  behavior-preserving refactors keep evidence valid while any policy
  change invalidates it. No new deps.
- **Baseline** (cycle-30 pins re-verified): 101 OK; 5/5; 30-seed
  466/240/217; fixed-rig syn 0.05411532 phi 0.0 n32; gap proven
  (write_header rejects policy kwargs; headers cite nothing).
- **After**:
  - code identical: 30-seed 466/240/217; all 101 carried tests pass
    (header keys additive; roundtrip/bins/strictness untouched).
  - trace identical: syn 0.05411532 phi 0.0 n32; lesions unchanged.
  - binding live: rule headers cite grid-rule/planner + digest +
    model rule; stub runs cite StubBackend; real 32-record run
    verifies clean with the cited header.
- **Ablation** (no source revert needed — each probe is a failing
  control):
  - config-variant digest differs (sensitivity proven).
  - header policy tamper -> edited-record:0 under verify.
  - pre-change tree: TypeError on policy kwargs + missing fields.
- **Verdict**: provenance win (runs now cite their producer);
  no emergent claim. Verdict UNKNOWN.
- **Gates**: unittest 105/105 OK (101 carried + 4 new); aikit 5/5.
- **Commands run**:
  - `python -m unittest tests.test_policy_binding -v` -> 4 OK.
  - `python -m unittest discover -s tests -t .` -> 101 OK before,
    105 OK after.
  - `python aikit.py check brain` -> 5/5 before and after.
  - standing 30-seed + fixed-rig + real-run verify identical.
- **Pinned regression baselines for cycle 32**: unittest 105 OK; aikit
  5/5; standing 466/240/217; 0-99 1581/800/683; T1 100-199 1646;
  T3 100-199 732; T3 200-299 718; T3 300-399 671; T3 400-499 675;
  holdout 500-599 1581/800/738; exhaustive T3 3906/3906 total
  27860; corridor-cut control 12/742; random floor best 1271/5.0
  vs rule 89/11.0 (margins x10/+5); chain intact ok + 5 named
  tamper findings; headers cite policy+digest+model; golden 9/9
  paths; pins 16/8/13/6/9 + 7/14 + 6/10; fixed-rig syn
  0.05411532 phi 0.0 n32; hub0/m0 0.0 p0/s0 identical; manifest +
  repro determinism variance 0.

## Cycle 32 — collapse dead lookahead depth (idea transfer)
- **Source**: lacon RLM's explicit depth caps prompted the question;
  proof is Brain's own exhaustive battery (Lattice transfer).
- **Gap**: _has_exit carried a depth-4 recursion knob that corridor
  avoidance (cycle 20) had silently subsumed — a misleading tuner
  with zero verified effect anywhere in the task family.
- **Target delta**: delete the depth parameter (leaf check only);
  byte-identical behavior everywhere; control re-pinned with
  documented background change.
- **Falsifier**: any config, pin, golden path, oracle, or trace
  number moves.
- **Change** (agent.py _has_exit collapse + tests/test_negative_
  control.py re-pin 742->744 + docstring; ADR-031): recursion and
  depth param removed; viable/dead structure untouched. No new deps.
- **Baseline** (cycle-31 pins re-verified): 105 OK; 5/5; 30-seed
  466/240/217; fixed-rig syn 0.05411532 phi 0.0 n32.
- **Proof before edit**: depth-2 + corridor = 3906/3906 optimal
  (total 27860, identical); depth-2 vs depth-4 action sequences
  byte-identical on all 3906 configs (0 path diffs); depth-1 also
  0 diffs — the parameter is dead given corridor + visits.
- **After**:
  - code identical: 30-seed 466/240/217; all 105 tests pass
    (incl. 9 goldens, exhaustive, holdout, oracles, hidden).
  - trace identical: syn 0.05411532 phi 0.0 n32; lesions unchanged.
  - T1 re-audit under final code: 39711/39711 optimal (loop closed).
- **Ablation / sensitivity**:
  - corridor-cut control now reads 479=12, holdout T3=744
    (was 742 vs depth-4: without corridor, depth had fixed 2 more
    steps) — fails loudly vs intact 10/738 as designed; call_count
    engagement still asserted.
  - Exhaustive battery would catch any revival-relevant divergence
    (21-trap precedent under the cut).
  - Revival condition: multi-obstacle layouts or larger grids, where
    leaf viability may no longer suffice — re-add depth then, with
    a failing config first.
- **Verdict**: substrate simplification with exhaustive proof (-3
  lines, dead knob removed, no wall-time claim — battery dominated
  by world-sim, noise floor); no emergent claim. Verdict UNKNOWN.
- **Gates**: unittest 105/105 OK (control re-pinned, rest untouched);
  aikit 5/5 PASS.
- **Commands run**:
  - depth-2 + corridor exhaustive: 3906/3906, total 27860.
  - depth-2 vs depth-4 path-hash diff: 0/3906.
  - depth-1 vs depth-2: 0/3906 (collapse justified).
  - T1 39711 re-audit under final code: 0 bad.
  - `python -m unittest discover -s tests -t .` -> 104/105 with
    cut-background mismatch before re-pin, 105/105 after.
  - `python aikit.py check brain` -> 5/5 before and after.
  - standing 30-seed + fixed-rig identical.
- **Pinned regression baselines for cycle 33**: unittest 105 OK; aikit
  5/5; standing 466/240/217; 0-99 1581/800/683; T1 100-199 1646;
  T3 100-199 732; T3 200-299 718; T3 300-399 671; T3 400-499 675;
  holdout 500-599 1581/800/738; exhaustive T3 3906/3906 total
  27860; corridor-cut control 12/744 (leaf background); random
  floor best 1271/5.0 vs rule 89/11.0 (margins x10/+5); chain
  intact ok + 5 named tamper findings; headers cite policy+digest
  +model; golden 9/9 paths; pins 16/8/13/6/9 + 7/14 + 6/10;
  fixed-rig syn 0.05411532 phi 0.0 n32; hub0/m0 0.0 p0/s0
  identical; manifest + repro determinism variance 0.

## Cycle 33 — accurate policy citation after depth collapse
- **Baseline** (cycle-32 pins re-verified, same rig/seeds):
  - canonical: 105 OK; aikit 5/5 PASS.
  - code behavior: T1-71 16, T2-3 8, T3-15 13, T3-65 6, T3-74 9,
    T3-202 7, T3-272 14, T3-307 6, T3-479 10; 30-seed 466/240/217.
  - trace internals: fixed-rig (T1 seed7) syn 0.05411532 syn_n
    0.10814360 phi 0.0 n_records 32; hub0/m0 syn 0.0;
    p0/s0 bit-identical.
  - model-seam internals: PLANNER_POLICY cites lookahead_depth 4
    (dead since cycle 32 leaf collapse); policy_digest
    99d014313656292a6c3cee8f6acf199999e78f14b4856fff2de4b3dce1c95d3b;
    manifest determinism True; visit-oracle 5/5; repro variance 0;
    headers cite stale digest with chain verify ok.
  - probe gap: tests/test_policy_accuracy.py absent (import error);
    new 3-test accuracy probe FAILs 3/3 on intact tree (depth knob
    present, viability missing, legacy digest equals current).
- **Gap**: _has_exit is a leaf check, but the declared policy still
  advertises a depth-4 tuner — evidence misbinding with zero
  behavior effect.
- **Target delta**: declare viability leaf, drop dead knob; digest
  changes; behavior and trace byte-identical; accuracy 3/3 green.
- **Falsifier**: standing totals move, trace numbers move, or
  accuracy still red after the change.
- **Change** (agent.py PLANNER_POLICY only: lookahead_depth 4 ->
  viability leaf; tests/test_policy_accuracy.py new 3 tests;
  tests/test_policy_binding.py sensitivity mutates viability):
  no planner logic touched; no new deps. ADR-032.
- **After** (identical battery, same seeds):
  - code identical: 30-seed 466/240/217; all 105 carried tests pass.
  - trace identical: syn 0.05411532 syn_n 0.10814360 phi 0.0 n32;
    lesions unchanged.
  - seam versioned: policy_digest
    18edf1ca2b1e371a79701e1b89a76591cf35d0987f5884b352a1e9715a8393d5
    (!= legacy 99d01431...); header cites grid-rule/planner +
    new digest + rule with chain verify ok; accuracy 3/3 green;
    viability-variant digest differs (sensitivity).
- **Ablation** (legacy depth-4 policy, no source revert needed —
  pre-change measurement is the cut):
  - intact leaf policy: digest 18edf1ca..., accuracy 3/3 OK.
  - legacy depth-4 cut: digest 99d01431..., accuracy 0/3 (all FAIL
    on missing viability / dead knob / digest equality).
  - Provenance dies with the cut, returns with the restore; routing
    and trace identical under both (declared-only change, honestly
    recorded — value pins live in trap/range/exhaustive suites).
- **Verdict**: provenance win (declared config now matches shipped
  code); no emergent claim. Verdict UNKNOWN.
- **Gates**: unittest 108/108 OK (105 carried + 3 new); aikit 5/5
  PASS.
- **Commands run**:
  - `python -m unittest tests.test_policy_accuracy -v` -> 3 FAIL
    before, 3 OK after.
  - `python -m unittest tests.test_policy_binding -v` -> 4 OK after
    (sensitivity re-pinned to viability).
  - `python -m unittest discover -s tests -t .` -> 105 OK before,
    108 OK after.
  - `python aikit.py check brain` -> 5/5 before and after.
  - standing 30-seed + fixed-rig recompute identical; header +
    chain-verify probe identical except digest rotation.
- **Pinned regression baselines for cycle 34**: unittest 108 OK; aikit
  5/5; standing 466/240/217; 0-99 1581/800/683; T1 100-199 1646;
  T3 100-199 732; T3 200-299 718; T3 300-399 671; T3 400-499 675;
  holdout 500-599 1581/800/738; exhaustive T3 3906/3906 total
  27860; corridor-cut control 12/744 (leaf background); random
  floor best 1271/5.0 vs rule 89/11.0 (margins x10/+5); chain
  intact ok + 5 named tamper findings; headers cite
  grid-rule/planner + 18edf1ca... + model; golden 9/9 paths; pins
  16/8/13/6/9 + 7/14 + 6/10; fixed-rig syn 0.05411532 phi 0.0 n32;
  hub0/m0 0.0 p0/s0 identical; manifest + repro determinism
  variance 0.

## Cycle 34 — hub-carried collect evidence for persistent-hidden forage
- **Baseline** (cycle-33 pins re-verified, same rig/seeds):
  - canonical: 108 OK; aikit 5/5 PASS.
  - code behavior: standing 466/240/217; T1-71 16/3.0 visible;
    persistent-hidden T1 (HiddenT1 omits items after init):
    71/74/78 all 200/1.0 vs 16/12/18 intact with 3.0.
  - trace internals: fixed-rig syn 0.05411532 syn_n 0.10814360
    phi 0.0 n32; hub0/m0 0.0; p0/s0 identical; substrate_errors
    all zero; hub dict carries last_step/last_action/last_reward
    only (planner reads and discards).
  - model-seam internals: policy_digest 18edf1ca... (viability
    leaf); manifest determinism True; visit-oracle 5/5; hidden
    13/16; persistent-hidden T3 13/6.
  - probe gap: tests/test_persistent_hidden_forage.py absent;
    new 3-test probe FAILs 2/3 on intact tree (hidden 200/1.0 vs
    16/3.0; hub-blind 200/1.0 control not yet gated).
- **Gap**: full-history recall returns the initial 3-cell list
  forever on persistent-hidden forage; after the first collect the
  stale cell routes the agent back and it loops to cap with 1.0.
  Planner ignores hub collect evidence by construction.
- **Target delta**: hub accumulates successful collect cells;
  planner filters recalled items against them; hidden 200/1.0 ->
  16/12/18 with 3.0; standing and trace byte-identical.
- **Falsifier**: standing totals move, trace numbers move, or any
  hidden seed stays 200/1.0; emergence falsifier: hub-blind lesion
  must restore 200/1.0 or the gain is not hub-carried.
- **Change** (agent.py only: Planner.plan reads
  collected_positions and filters recalled items_positions;
  Agent.run appends successful collect cells to hub with dedupe;
  tests/test_persistent_hidden_forage.py new 3 tests): deterministic,
  stdlib only. ADR-033.
- **After** (identical battery, same seeds):
  - code: standing 466/240/217 identical; hidden T1-71 200->16,
    T1-74 200->12, T1-78 200->18, all 3.0; 3x repeats variance 0
    (deterministic replay, carried repro 27/27).
  - trace: fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0 n32
    identical; lesions unchanged; substrate_errors all zero.
  - seam carried: visit/hidden/persistent oracles unchanged;
    hidden-forage obs now carries filtered items (hub-filtered).
- **Ablation** (hub-blind: read_hub empty, same HiddenT1):
  - intact hub: 16/3.0.
  - cut blind: 200/1.0.
  - Gain dies with the cut, returns with the restore: hub
    collected channel load-bearing. Standing None control
    unchanged (466/240/217, full suite green).
- **Verdict**: robustness win with proven hub-memory coupling; no
  emergent claim. Verdict UNKNOWN.
- **Gates**: unittest 111/111 OK (108 carried + 3 new); aikit 5/5
  PASS (one hygiene finding on the way: bare except pass at
  filtering — fixed to value-preserving fallback).
- **Commands run**:
  - `python -m unittest tests.test_persistent_hidden_forage -v`
    -> 2 FAIL (200/1.0) before, 3 OK after.
  - `python -m unittest discover -s tests -t .` -> 108 OK before,
    111 OK after.
  - `python aikit.py check brain` -> 5/5 before; 4/5 (hygiene
    silent-except) then 5/5 after fallback fix.
  - standing 30-seed + fixed-rig recompute identical; hidden 3-seed
    + hub-blind ablation.
- **Pinned regression baselines for cycle 35**: unittest 111 OK; aikit
  5/5; standing 466/240/217; hidden-T1 16/12/18 with 3.0;
  hub-blind ablation 200/1.0; 0-99 1581/800/683; T1 100-199 1646;
  T3 100-199 732; T3 200-299 718; T3 300-399 671; T3 400-499 675;
  holdout 500-599 1581/800/738; exhaustive T3 3906/3906 total
  27860; corridor-cut 12/744; random floor 1271/5.0 vs 89/11.0;
  chain ok + 5 findings; headers grid-rule/planner + 18edf1ca...;
  golden 9/9; pins 16/8/13/6/9 + 7/14 + 6/10; fixed-rig syn
  0.05411532 phi 0.0 n32; hub0/m0 0.0 p0/s0 identical; manifest +
  repro variance 0.

## Cycle 35 — visit-pooled detours for multi-obstacle navigation
- **Baseline** (cycle-34 pins re-verified, same rig/seeds):
  - canonical: 111 OK; aikit 5/5 PASS.
  - code behavior: standing 466/240/217; T1-100 1581; exhaustive
    T3 3906/3906 total 27860; two-blocker probes (new):
    (5,0) 200/0.0 vs BFS 9, (7,5) 200/0.0 vs 12, (3,6) 13/1.0
    vs 9; seed-74 blind 200/0.0 (visits coupling carried).
  - trace internals: fixed-rig syn 0.05411532 syn_n 0.10814360
    phi 0.0 n32; hub0/m0 0.0; p0/s0 identical; errors zero.
  - model-seam internals: digest 18edf1ca...; manifest True;
    visit-oracle 5/5; hidden-T1 16/12/18; persistent-hidden 13/6.
  - probe gap: tests/test_multi_obstacle.py absent; new 3-test
    probe FAILs 2/3 on intact tree (200/0.0 vs 9/20/11).
- **Gap**: viable-first routing oscillates on two-blocker cul-de-sacs
  (dead goal step beats backup detour, viable back-edge beats
  unexplored exit), truncating twice. Single-obstacle exhaustive
  cannot see it; revival condition from cycle 32 explicitly names
  multi-obstacle layouts.
- **Target delta**: obstacle navigation pools viable with backup by
  least-visited; open-field keeps viable-first; multi 200->9,
  200->20, 13->11 all complete; standing/exhaustive byte-identical.
- **Falsifier**: standing totals move, exhaustive moves, golden moves,
  or any multi stays 200/0.0; emergence falsifier: memory-blind must
  restore 200/0.0 on all three or the gain is not visit-carried.
- **Change** (agent.py _step_toward only: obstacles-empty keeps
  viable/dead/backup order; obstacles-present pools viable+backup
  deduped by least-visited with dead last; tests/test_multi_obstacle.py
  new 3 tests): deterministic, stdlib only. ADR-034.
- **After** (identical battery, same seeds):
  - code: standing 466/240/217 identical; T1-100 1581 identical;
    exhaustive 3906/3906 total 27860 identical; goldens 9/9 identical;
    multi (5,0) 200->9/1.0, (7,5) 200->20/1.0, (3,6) 13->11/1.0;
    variance 0 (deterministic, carried repro 27/27).
  - trace: fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0 n32
    identical; multi traces carry deltas (S -191/-180/-2 steps,
    M -191/-180/-2); lesions unchanged.
  - seam carried: visit/hidden/persistent/hub oracles unchanged.
- **Ablation** (memory-blind: Planner.plan with None memories):
  - intact pooled: 9/20/11 with 1.0.
  - cut blind: 200/0.0 on all three.
  - Gain dies with the cut, returns with the restore: visit channel
    load-bearing. Honestly recorded: pool structure alone suffices
    nowhere without visits on these three (unlike single-obstacle
    seeds 15/65 where lookahead suffices). Standing None control
    unchanged (full suite green).
- **Verdict**: robustness win (2 truncations fixed, 1 detour -2)
  with proven visit coupling; 2 multis remain non-optimal
  (20 vs 12, 11 vs 9) — reserved for depth revival with failing
  configs. No emergent claim. Verdict UNKNOWN.
- **Gates**: unittest 114/114 OK (111 carried + 3 new); aikit 5/5
  PASS (one full-suite red on the way: naive pool broke T1-100
  1581->1591, goldens, and seed-74 blind — fixed by gating the pool
  on obstacles-present and sorting visits-only).
- **Commands run**:
  - `python -m unittest tests.test_multi_obstacle -v` -> 2 FAIL
    (200/0.0) before, 3 OK after.
  - `python -m unittest discover -s tests -t .` -> 111 OK before,
    114 OK after (mid-cycle 5 FAIL with naive pool, then green).
  - `python aikit.py check brain` -> 5/5 before and after.
  - standing 30-seed + T1-100 + fixed-rig identical; exhaustive
    3906/3906 total 27860 identical; multi 3-seed + blind ablation.
- **Pinned regression baselines for cycle 36**: unittest 114 OK; aikit
  5/5; standing 466/240/217; multi 9/20/11 with 1.0; blind multi
  200/0.0 x3; seed-74 9 intact / 200 blind; 0-99 1581/800/683;
  T1 100-199 1646; T3 100-199 732; T3 200-299 718; T3 300-399 671;
  T3 400-499 675; holdout 1581/800/738; exhaustive 3906/3906
  27860; corridor-cut 12/744; random floor 1271/5.0 vs 89/11.0;
  chain ok + 5 findings; headers 18edf1ca...; golden 9/9; pins
  16/8/13/6/9 + 7/14 + 6/10; fixed-rig syn 0.05411532 phi 0.0 n32;
  hub0/m0 0.0 p0/s0 identical; manifest + repro variance 0.

## Cycle 36 — accurate pooling citation in run headers
- **Baseline** (cycle-35 pins re-verified, same rig/seeds):
  - canonical: 114 OK; aikit 5/5 PASS.
  - code behavior: standing 466/240/217; T1-100 1581; multi
    9/20/11 with 1.0; blind multi 200/0.0 x3; exhaustive 27860.
  - trace internals: fixed-rig syn 0.05411532 syn_n 0.10814360
    phi 0.0 n32; hub0/m0 0.0; p0/s0 identical; errors zero.
  - model-seam internals: PLANNER_POLICY without detour_pooling
    (pre-pool citation); digest 18edf1ca2b1e371a79701e1b89a76591cf35d0987f5884b352a1e9715a8393d5;
    manifest True; visit-oracle 5/5; headers cite stale digest.
  - probe gap: tests/test_pool_policy.py absent; new 3-test probe
    FAILs 2/3 on intact tree (pooling key missing, legacy digest
    equals current).
- **Gap**: cycle 35 pooled viable with backup for obstacle navigation
  but left the declared policy on the pre-pool configuration —
  evidence misbinding with zero behavior effect on standing tasks.
- **Target delta**: declare detour_pooling visits; digest rotates;
  behavior and trace byte-identical; pool accuracy 3/3 green.
- **Falsifier**: standing totals move, trace numbers move, multi
  numbers move, or accuracy still red after the change.
- **Change** (agent.py PLANNER_POLICY only: add detour_pooling visits;
  tests/test_pool_policy.py new 3 tests): no planner logic touched;
  no new deps. ADR-035.
- **After** (identical battery, same seeds):
  - code identical: 30-seed 466/240/217; T1-100 1581; multi
    9/20/11; all 114 carried tests pass.
  - trace identical: syn 0.05411532 syn_n 0.10814360 phi 0.0 n32;
    lesions unchanged; errors zero.
  - seam versioned: policy_digest
    4245d56ed814756b3691aa8cb156c483e84eb7b62a57d8dcc2684c4060de9729
    (!= legacy 18edf1ca...); header cites grid-rule/planner +
    new digest + rule with chain verify ok; pooling sensitivity
    via none-variant differs.
- **Ablation** (pre-pool legacy policy without the key, no source
  revert needed — pre-change measurement is the cut):
  - intact pooled policy: digest 4245d56e..., accuracy 3/3 OK.
  - legacy pre-pool cut: digest 18edf1ca..., accuracy 0/3 on the
    declaration/digest-equality assertions.
  - Provenance dies with the cut, returns with the restore; routing
    and trace identical under both (declared-only, honestly
    recorded — value pins live in trap/range/exhaustive/multi suites).
- **Verdict**: provenance win (declared config now matches shipped
  pooling); no emergent claim. Verdict UNKNOWN.
- **Gates**: unittest 117/117 OK (114 carried + 3 new); aikit 5/5
  PASS.
- **Commands run**:
  - `python -m unittest tests.test_pool_policy -v` -> 2 FAIL
    before, 3 OK after.
  - `python -m unittest discover -s tests -t .` -> 114 OK before,
    117 OK after.
  - `python aikit.py check brain` -> 5/5 before and after.
  - standing 30-seed + T1-100 + fixed-rig recompute identical;
    multi 9/20/11 carried; header + chain-verify with digest rotation.
- **Pinned regression baselines for cycle 37**: unittest 117 OK; aikit
  5/5; standing 466/240/217; multi 9/20/11 with 1.0; blind multi
  200/0.0 x3; seed-74 9 intact / 200 blind; 0-99 1581/800/683;
  T1 100-199 1646; T3 100-199 732; T3 200-299 718; T3 300-399 671;
  T3 400-499 675; holdout 1581/800/738; exhaustive 3906/3906
  27860; corridor-cut 12/744; random floor 1271/5.0 vs 89/11.0;
  chain ok + 5 findings; headers grid-rule/planner + 4245d56e...;
  golden 9/9; pins 16/8/13/6/9 + 7/14 + 6/10; fixed-rig syn
  0.05411532 phi 0.0 n32; hub0/m0 0.0 p0/s0 identical; manifest +
  repro variance 0.

## Cycle 37 — corridor-weighted pooling for the missed two-blocker truncation
- **Baseline** (cycle-36 pins re-verified, same rig/seeds):
  - canonical: 117 OK; aikit 5/5 PASS.
  - code behavior: standing 466/240/217; T1-100 1581; exhaustive
    27860; two-blocker audit (new): (5,6) with (4,4),(5,5)
    200/0.0 vs BFS 11; carried multis (5,0) 9, (7,5) 20 vs 12,
    (3,6) 11 vs 9; seed-74 9 intact / 200 blind.
  - trace internals: fixed-rig syn 0.05411532 syn_n 0.10814360
    phi 0.0 n32; hub0/m0 0.0; p0/s0 identical; errors zero.
  - model-seam internals: digest 4245d56e... (pooling visits);
    manifest True; visit-oracle 5/5; headers cite current digest.
  - probe gap: tests/test_multi_obstacle.py pins 3 multis; 4th
    config (5,6)->13 plus (7,5) 20->18 FAIL 2/3 on intact tree
    (200 vs 13, 20 vs 18).
- **Gap**: visits-only pooling avoids (5,4) dead step and loops
  north into an 8-cycle on (5,6); corridor entry is ignored in the
  pool, so the early eastward entry into the blocked column wins
  every tie.
- **Target delta**: two-or-more blockers weigh blocked-corridor
  after visits in the pool; single blockers stay visits-only;
  open-field keeps viable-first; (5,6) 200->13, (7,5) 20->18,
  others identical; standing/exhaustive byte-identical.
- **Falsifier**: standing totals move, exhaustive moves, golden
  moves, seed-74 blind moves, or any multi stays 200/0.0;
  emergence falsifier: memory-blind must restore 200/0.0 on the
  corridor-fixed multis or the gain is not visit-carried.
- **Change** (agent.py _step_toward only: >=2 obstacles pool sorts
  by visits then blocked-corridor; 1 obstacle visits-only; 0
  obstacles viable-first; tests/test_multi_obstacle.py extended to
  4 configs with (7,5) re-pinned 18): deterministic, stdlib only.
  ADR-036.
- **After** (identical battery, same seeds):
  - code: standing 466/240/217 identical; T1-100 1581 identical;
    exhaustive 3906/3906 total 27860 identical; goldens 9/9
    identical; multi (5,0) 9, (7,5) 20->18, (3,6) 11,
    (5,6) 200->13/1.0, (5,7) 14 carried; variance 0.
  - trace: fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0 n32
    identical; multi traces carry deltas (S -187/-2, M -187/-2);
    lesions unchanged.
  - seam carried: visit/hidden/persistent/hub oracles unchanged;
    digest unchanged 4245d56e... (pooling visits + corridor
    avoidance both already declared — refinement, not new policy).
- **Ablation** (memory-blind: Planner.plan with None memories):
  - intact pooled: 9/18/11/13 with 1.0.
  - cut blind: (5,0) 9/1.0 (pool-sufficient, honest exception like
    seeds 15/65); (7,5),(3,6),(5,6) 200/0.0.
  - Gain dies with the cut on the three corridor-fixed multis,
    returns with the restore: visit channel load-bearing where
    corridor alone does not suffice. Standing None control
    unchanged (full suite green).
- **Verdict**: robustness win (1 truncation fixed, 1 detour -2)
  with proven visit coupling on 3/4; (5,0) pool-sufficient honestly
  recorded. No emergent claim. Verdict UNKNOWN.
- **Gates**: unittest 117/117 OK (test file extended, count
  unchanged); aikit 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_multi_obstacle -v` -> 2 FAIL
    (20 vs 18, 200 vs 13) before, 3 OK after.
  - `python -m unittest discover -s tests -t .` -> 117 OK before
    and after.
  - `python aikit.py check brain` -> 5/5 before and after.
  - standing 30-seed + T1-100 + fixed-rig + exhaustive identical;
    multi 4-seed + blind ablation.
- **Pinned regression baselines for cycle 38**: unittest 117 OK; aikit
  5/5; standing 466/240/217; multi 9/18/11/13 with 1.0; blind
  9/200/200/200; seed-74 9 intact / 200 blind; 0-99 1581/800/683;
  T1 100-199 1646; T3 100-199 732; T3 200-299 718; T3 300-399 671;
  T3 400-499 675; holdout 1581/800/738; exhaustive 3906/3906
  27860; corridor-cut 12/744; random floor 1271/5.0 vs 89/11.0;
  chain ok + 5 findings; headers 4245d56e...; golden 9/9; pins
  16/8/13/6/9 + 7/14 + 6/10; fixed-rig syn 0.05411532 phi 0.0 n32;
  hub0/m0 0.0 p0/s0 identical; manifest + repro variance 0.

## Cycle 38 — multi-obstacle golden paths (idea transfer)
- **Source**: Keystone pinned simulation hash (tenth transfer; cycle-30
  goldens pinned the nine standing seeds, cycle-25 exhaustive and
  cycle-35 multi pinned counts only).
- **Gap**: multi counts pin outcomes (9/18/11/13), but a
  behavior-neutral path swap at identical counts would drift
  silently past all 117 tests.
- **Target delta**: SHA-256 over canonical action sequences for the
  four multi configs, computed once on the intact tree; 0.007s.
- **Falsifier**: standing totals move, trace numbers move, multi
  counts move, or any multi path differs.
- **Change** (tests/test_multi_goldens.py new only; ADR-037):
  MULTI_GOLDEN map + one equality test per config across the four
  pinned multis; regeneration deliberately manual (reviewed edit, no
  auto-update) so goldens can never rebaseline a red tree green. No
  source diff; no new deps.
- **Baseline** (cycle-37 pins re-verified): 117 OK; 5/5; 30-seed
  466/240/217; fixed-rig syn 0.05411532 phi 0.0 n32; multi
  9/18/11/13 deterministic 3x identical (variance 0).
- **After**:
  - code identical: 30-seed 466/240/217; multi 9/18/11/13; all 117
    carried tests pass.
  - trace identical: syn 0.05411532 phi 0.0 n32; lesions unchanged.
  - paths pinned: 118/118 with 4/4 multi golden hashes exact.
- **Ablation / sensitivity** (no source touched):
  - single-action flip changes the fingerprint (proven cycle 24:
    99aa6b.. vs 21dcfa.., differ True; multi uses the same
    canonical-hash helper).
  - pre-pool ordering gives 200/200/13/200 step counts on the same
    four configs (different-length lists), which necessarily changes
    every affected hash — the golden gate inherits every routing
    cut's sensitivity on top of count pins.
- **Verdict**: provenance win (multi paths now pinned, not just
  counts); no emergent claim. Verdict UNKNOWN.
- **Gates**: unittest 118/118 OK (117 carried + 1 new); aikit 5/5
  PASS.
- **Commands run**:
  - `python -m unittest tests.test_multi_goldens -v` -> 1 OK.
  - `python -m unittest discover -s tests -t .` -> 117 OK before,
    118 OK after.
  - `python aikit.py check brain` -> 5/5 before and after.
  - standing 30-seed + fixed-rig + multi counts identical;
    determinism 3x identical.
- **Pinned regression baselines for cycle 39**: unittest 118 OK; aikit
  5/5; standing 466/240/217; multi 9/18/11/13 with 1.0; multi
  goldens 4/4 paths; blind 9/200/200/200; seed-74 9 intact / 200
  blind; 0-99 1581/800/683; T1 100-199 1646; T3 100-199 732;
  T3 200-299 718; T3 300-399 671; T3 400-499 675; holdout
  1581/800/738; exhaustive 3906/3906 27860; corridor-cut 12/744;
  random floor 1271/5.0 vs 89/11.0; chain ok + 5 findings; headers
  4245d56e...; golden 9/9 + multi 4/4; pins 16/8/13/6/9 + 7/14 +
  6/10; fixed-rig syn 0.05411532 phi 0.0 n32; hub0/m0 0.0 p0/s0
  identical; manifest + repro variance 0.

## Cycle 39 — backfill fifth two-blocker pin (idea transfer)
- **Source**: Lattice snapshot-diffing completion (eleventh transfer;
  cycle-28 backfilled range pins, cycle-38 pinned four multi paths).
- **Gap**: (5,7) with (5,6),(4,2) completes in 14/1.0 with blind
  200/0.0 and a deterministic path, but no test pins its count,
  path, or blind differential — a drift in the fifth verified trap
  would pass all 118 tests.
- **Target delta**: pin fifth config count 14, golden path, and blind
  200/0.0 already covered by existing blind test shape (7,5);
  explicit (5,7) blind verified in audit; 5/5 multi matrix complete.
- **Falsifier**: standing totals move, trace numbers move, or any of
  the five multi numbers moves on the intact tree.
- **Change** (tests/test_multi_obstacle.py extended to five configs
  with (5,7)->14; tests/test_multi_goldens.py extended to five
  hashes; ADR-038): audit-measured numbers pinned, fifth golden
  computed once on the intact tree; no source diff; no new deps.
- **Baseline** (cycle-38 pins re-verified): 118 OK; 5/5; 30-seed
  466/240/217; fixed-rig syn 0.05411532 phi 0.0 n32; multi audit
  (5,7) 14/1.0 deterministic 3x identical, blind 200/0.0.
- **After**:
  - code identical: 30-seed 466/240/217; multi 9/18/11/13/14; all
    118 carried tests pass (file extensions, count unchanged).
  - trace identical: syn 0.05411532 phi 0.0 n32; lesions unchanged.
  - matrix complete: multi counts 5/5, multi goldens 5/5, blind
    killing configs (7,5),(3,6),(5,6),(5,7) all 200/0.0 with
    (5,0) 9/1.0 pool-sufficient honestly carried.
- **Ablation / sensitivity** (no source touched):
  - memory-blind cut moves (5,7) 14 -> 200 with 0.0 reward: the new
    pin catches memory-coupling loss like the three carried blind
    pins.
  - pre-pool ordering on the same five gives 200/200/13/200/200,
    necessarily changing every affected golden hash.
- **Verdict**: provenance win (multi snapshot matrix complete); no
  emergent claim. Verdict UNKNOWN.
- **Gates**: unittest 118/118 OK (files extended, count unchanged);
  aikit 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_multi_obstacle tests.test_multi_goldens -v` -> 4 OK.
  - `python -m unittest discover -s tests -t .` -> 118 OK before
    and after.
  - `python aikit.py check brain` -> 5/5 before and after.
  - standing 30-seed + fixed-rig identical; (5,7) determinism 3x +
    blind 200/0.0 audit.
- **Pinned regression baselines for cycle 40**: unittest 118 OK; aikit
  5/5; standing 466/240/217; multi 9/18/11/13/14 with 1.0; multi
  goldens 5/5 paths; blind 9/200/200/200/200; seed-74 9 intact / 200
  blind; 0-99 1581/800/683; T1 100-199 1646; T3 100-199 732;
  T3 200-299 718; T3 300-399 671; T3 400-499 675; holdout
  1581/800/738; exhaustive 3906/3906 27860; corridor-cut 12/744;
  random floor 1271/5.0 vs 89/11.0; chain ok + 5 findings; headers
  4245d56e...; golden 9/9 + multi 5/5; pins 16/8/13/6/9 + 7/14 +
  6/10; fixed-rig syn 0.05411532 phi 0.0 n32; hub0/m0 0.0 p0/s0
  identical; manifest + repro variance 0.

## Cycle 40 — declare the pool-corridor gate in run headers
- **Baseline** (cycle-39 pins re-verified, same rig/seeds):
  - canonical: 118 OK; aikit 5/5 PASS.
  - code behavior: standing 466/240/217; multi 9/18/11/13/14 with
    1.0; blind 9/200/200/200/200; exhaustive 27860.
  - trace internals: fixed-rig syn 0.05411532 syn_n 0.10814360
    phi 0.0 n32; hub0/m0 0.0; p0/s0 identical; errors zero.
  - model-seam internals: PLANNER_POLICY without pool_corridor
    (pre-gate citation); digest 4245d56ed814756b3691aa8cb156c483e84eb7b62a57d8dcc2684c4060de9729;
    manifest True; headers cite stale config.
  - probe gap: tests/test_pool_corridor_policy.py absent; new 3-test
    probe FAILs 2/3 on intact tree (gate key missing, legacy digest
    equals current).
  - audit dead ends (one line): mean_conf churn still consumed by
    nothing; hub last_action still written-not-read; persistent store
    recall still zero headroom on current tasks; tracker/self_model
    still unit-only; T2 wait still unreachable; energy still never
    binds; phi/P/S still gameable if read; 3-blocker (6,5) 200/0.0
    truncation documented for the routing track (no safe fix this
    cycle without breaking seed-74/T1 pins).
- **Gap**: cycle 37 gated corridor weighting in the pool on >=2
  blockers but left the declared policy on pooling-visits only —
  evidence misbinding with zero behavior effect on standing tasks.
- **Target delta**: declare pool_corridor >=2; digest rotates;
  behavior and trace byte-identical; gate accuracy 3/3 green.
- **Falsifier**: standing totals move, trace numbers move, multi
  numbers move, or accuracy still red after the change.
- **Change** (agent.py PLANNER_POLICY only: add pool_corridor >=2;
  tests/test_pool_corridor_policy.py new 3 tests): no planner logic
  touched; no new deps. ADR-039.
- **After** (identical battery, same seeds):
  - code identical: 30-seed 466/240/217; multi 9/18/11/13/14; all
    118 carried tests pass.
  - trace identical: syn 0.05411532 syn_n 0.10814360 phi 0.0 n32;
    lesions unchanged; errors zero.
  - seam versioned: policy_digest
    ffa19359a91b91d5dd5ccaba781fd73a6049e13037679b0a5af2c84f6ac22a49
    (!= legacy 4245d56e...); header cites grid-rule/planner +
    new digest + rule with chain verify ok; never-variant differs.
- **Ablation** (pre-gate legacy policy without the key, no source
  revert needed — pre-change measurement is the cut):
  - intact gated policy: digest ffa19359..., accuracy 3/3 OK.
  - legacy pre-gate cut: digest 4245d56e..., accuracy 0/3 on the
    declaration/digest-equality assertions.
  - Provenance dies with the cut, returns with the restore; routing
    and trace identical under both (declared-only).
- **Verdict**: provenance win (declared config now matches shipped
  >=2 gate); no emergent claim. Verdict UNKNOWN.
- **Gates**: unittest 121/121 OK (118 carried + 3 new); aikit 5/5
  PASS.
- **Commands run**:
  - `python -m unittest tests.test_pool_corridor_policy -v` -> 2 FAIL
    before, 3 OK after.
  - `python -m unittest discover -s tests -t .` -> 118 OK before,
    121 OK after.
  - `python aikit.py check brain` -> 5/5 before and after.
  - standing 30-seed + fixed-rig recompute identical; multi carried;
    header + chain-verify with digest rotation.
- **Pinned regression baselines for cycle 41**: unittest 121 OK; aikit
  5/5; standing 466/240/217; multi 9/18/11/13/14 with 1.0; multi
  goldens 5/5 paths; blind 9/200/200/200/200; seed-74 9 intact / 200
  blind; 0-99 1581/800/683; T1 100-199 1646; T3 100-199 732;
  T3 200-299 718; T3 300-399 671; T3 400-499 675; holdout
  1581/800/738; exhaustive 3906/3906 27860; corridor-cut 12/744;
  random floor 1271/5.0 vs 89/11.0; chain ok + 5 findings; headers
  grid-rule/planner + ffa19359...; golden 9/9 + multi 5/5; pins
  16/8/13/6/9 + 7/14 + 6/10; fixed-rig syn 0.05411532 phi 0.0 n32;
  hub0/m0 0.0 p0/s0 identical; manifest + repro variance 0.

## Cycle 41 — three-blocker snapshot matrix (idea transfer)
- **Source**: Lattice snapshot-diffing completion (twelfth transfer;
  cycle-39 completed the two-blocker matrix, cycle-38 its paths).
- **Gap**: five three-obstacle configs verified deterministic 3x
  identical with visit-coupled blinds, but no test pins any of them
  — a drift in the 3-blocker family would pass all 121 tests. One
  truncates (6,5) 200/0.0 vs BFS 13 and is documented as reserved
  routing headroom (no safe fix without breaking seed-74/T1 pins,
  per cycles 35/37 prototypes); four complete (15/12/10/13).
- **Target delta**: pin five counts with rewards, one blind
  differential (6,7) 15 vs 200, and determinism 3x; 0.75s.
- **Falsifier**: standing totals move, trace numbers move, or any of
  the five numbers moves on the intact tree.
- **Change** (tests/test_three_blocker.py new only; ADR-040):
  _ForcedThreeWorld hook (no private writes) + THREE_CONFIGS with
  wants + pins test + blind test on (6,7); regeneration deliberately
  manual (reviewed edit, no auto-update). No source diff; no new deps.
- **Baseline** (cycle-40 pins re-verified): 121 OK; 5/5; 30-seed
  466/240/217; fixed-rig syn 0.05411532 phi 0.0 n32; three-blocker
  audit 15/12/10/13/200 deterministic 3x identical, blinds
  200/200/10/200/200 (4/5 killing, (6,0) 10/1.0 pool-sufficient
  honestly carried like (5,0)).
- **After**:
  - code identical: 30-seed 466/240/217; two-blocker 9/18/11/13/14;
    all 121 carried tests pass.
  - trace identical: syn 0.05411532 phi 0.0 n32; lesions unchanged.
  - matrix new: three-blocker counts 5/5 with rewards, blind (6,7)
    15 vs 200 pinned; variance 0 (deterministic 3x).
- **Ablation / sensitivity** (no source touched):
  - memory-blind cut moves (6,7) 15 -> 200 with 0.0 reward and kills
    (7,3),(4,7) the same way (200/0.0); (6,0) 10/1.0 and (6,5)
    200/0.0 are pool-sufficient/truncation baselines honestly
    recorded — the pin catches coupling loss where coupling exists.
  - any routing change that moves a count fails the pins; a
    behavior-neutral path swap at identical counts is not yet
    hashed for this family (reserved: extend goldens only after a
    reviewed routing change, never to make red green).
- **Verdict**: provenance win (3-blocker family now pinned); no
  emergent claim. Verdict UNKNOWN.
- **Gates**: unittest 123/123 OK (121 carried + 2 new); aikit 5/5
  PASS.
- **Commands run**:
  - `python -m unittest tests.test_three_blocker -v` -> 2 OK
    (pins from intact-tree audit).
  - `python -m unittest discover -s tests -t .` -> 121 OK before,
    123 OK after.
  - `python aikit.py check brain` -> 5/5 before and after.
  - standing 30-seed + fixed-rig identical; three-blocker 3x
    determinism + blind audit.
- **Pinned regression baselines for cycle 42**: unittest 123 OK; aikit
  5/5; standing 466/240/217; multi 9/18/11/13/14 with 1.0; multi
  goldens 5/5 paths; three-blocker 15/12/10/13/200 with rewards;
  blind 9/200/200/200/200 + 200/200/10/200/200; seed-74 9 intact /
  200 blind; 0-99 1581/800/683; T1 100-199 1646; T3 100-199 732;
  T3 200-299 718; T3 300-399 671; T3 400-499 675; holdout
  1581/800/738; exhaustive 3906/3906 27860; corridor-cut 12/744;
  random floor 1271/5.0 vs 89/11.0; chain ok + 5 findings; headers
  ffa19359...; golden 9/9 + multi 5/5; pins 16/8/13/6/9 + 7/14 +
  6/10; fixed-rig syn 0.05411532 phi 0.0 n32; hub0/m0 0.0 p0/s0
  identical; manifest + repro variance 0.

## Cycle 42 — three-blocker golden paths (idea transfer)
- **Source**: Keystone pinned simulation hash (thirteenth transfer;
  cycle-38 pinned four multi paths, cycle-41 pinned five
  three-blocker counts).
- **Gap**: three-blocker counts pin outcomes (15/12/10/13/200) but a
  behavior-neutral path swap at identical counts would drift silently
  past all 123 tests.
- **Target delta**: SHA-256 over canonical action sequences for the
  five three-blocker configs, computed once on the intact tree.
- **Falsifier**: standing totals move, trace numbers move,
  three-blocker counts move, or any three-blocker path differs.
- **Change** (tests/test_three_goldens.py new only; ADR-041):
  THREE_GOLDEN map + one equality test across the five configs;
  regeneration deliberately manual (reviewed edit, no auto-update).
  No source diff; no new deps.
- **Baseline** (cycle-41 pins re-verified): 123 OK; 5/5; 30-seed
  466/240/217; fixed-rig syn 0.05411532 phi 0.0 n32; three-blocker
  15/12/10/13/200 deterministic 3x identical (variance 0).
- **After**:
  - code identical: 30-seed 466/240/217; multi 9/18/11/13/14;
    three-blocker 15/12/10/13/200; all 123 carried tests pass.
  - trace identical: syn 0.05411532 phi 0.0 n32; lesions unchanged.
  - paths pinned: 124/124 with 5/5 three-blocker golden hashes exact.
- **Ablation / sensitivity** (no source touched):
  - single-action flip changes the fingerprint (proven cycle-24 and
    reused in cycles 30/38 with the same canonical-hash helper).
  - any routing change that moves a count (e.g., pre-pool ordering
    on the same five) necessarily changes every affected hash — the
    golden gate inherits every routing cut's sensitivity on top of
    count pins.
- **Verdict**: provenance win (three-blocker paths now pinned, not
  just counts); no emergent claim. Verdict UNKNOWN.
- **Gates**: unittest 124/124 OK (123 carried + 1 new); aikit 5/5
  PASS.
- **Commands run**:
  - `python -m unittest tests.test_three_goldens -v` -> 1 OK.
  - `python -m unittest discover -s tests -t .` -> 123 OK before,
    124 OK after.
  - `python aikit.py check brain` -> 5/5 before and after.
  - standing 30-seed + fixed-rig + three-blocker counts identical;
    determinism 3x identical.
- **Pinned regression baselines for cycle 43**: unittest 124 OK; aikit
  5/5; standing 466/240/217; multi 9/18/11/13/14 with 1.0; multi
  goldens 5/5 paths; three-blocker 15/12/10/13/200 with rewards and
  5/5 paths; blind 9/200/200/200/200 + 200/200/10/200/200; seed-74 9
  intact / 200 blind; 0-99 1581/800/683; T1 100-199 1646; T3 100-199
  732; T3 200-299 718; T3 300-399 671; T3 400-499 675; holdout
  1581/800/738; exhaustive 3906/3906 27860; corridor-cut 12/744;
  random floor 1271/5.0 vs 89/11.0; chain ok + 5 findings; headers
  ffa19359...; golden 9/9 + multi 5/5 + three 5/5; pins
  16/8/13/6/9 + 7/14 + 6/10; fixed-rig syn 0.05411532 phi 0.0 n32;
  hub0/m0 0.0 p0/s0 identical; manifest + repro variance 0.

## Cycle 43 — complete the killing-blind matrices (idea transfer)
- **Source**: Lattice negative-control completion (fourteenth transfer;
  cycle-26 pinned corridor-cut, cycles 35/37/41 pinned single blind
  exemplars).
- **Gap**: blind tests pin one killing exemplar per family — multi
  (7,5) and three-blocker (6,7) — so coupling loss on the other
  killing configs ((3,6),(5,6),(5,7) and (7,3),(4,7)) would pass all
  124 tests. Pool-sufficient (5,0) 9/1.0 and (6,0) 10/1.0 plus the
  (6,5) 200/0.0 truncation baseline are honest exceptions (blind ==
  intact, vacuous) and stay documented, not pinned as kills.
- **Target delta**: loop the blind differential over every killing
  config in both families; 4/4 multi kills + 3/3 three kills pinned.
- **Falsifier**: standing totals move, trace numbers move, or any
  newly pinned blind stops killing on the intact tree.
- **Change** (tests/test_multi_obstacle.py + tests/test_three_blocker.py
  blind tests extended to loops; ADR-042): audit-measured 200/0.0
  pins, honest-exception comments; no source diff; no new deps.
- **Baseline** (cycle-42 pins re-verified): 124 OK; 5/5; 30-seed
  466/240/217; fixed-rig syn 0.05411532 phi 0.0 n32; blind audit
  multi 9/200/200/200/200, three 200/200/10/200/200.
- **After**:
  - code identical: 30-seed 466/240/217; multi 9/18/11/13/14;
    three-blocker 15/12/10/13/200; all 124 carried tests pass
    (files extended, count unchanged).
  - trace identical: syn 0.05411532 phi 0.0 n32; lesions unchanged.
  - matrices complete: multi blind kills 4/4, three blind kills 3/3
    pinned; variance 0.
- **Ablation / sensitivity** (no source touched):
  - the extended loops are themselves the cuts: intact 18/11/13/14
    vs blind 200/0.0 on every newly pinned seed — coupling loss on
    any of them fails loudly where the single-exemplar gate stayed
    green.
  - pool-sufficient (5,0),(6,0) and truncation-baseline (6,5) are
    excluded by construction with honest comments, so no vacuous
    pin can block a genuine coupling gain.
- **Verdict**: provenance win (negative-control matrices now
  complete); no emergent claim. Verdict UNKNOWN.
- **Gates**: unittest 124/124 OK (files extended, count unchanged);
  aikit 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_multi_obstacle tests.test_three_blocker -v` -> 5 OK.
  - `python -m unittest discover -s tests -t .` -> 124 OK before
    and after.
  - `python aikit.py check brain` -> 5/5 before and after.
  - standing 30-seed + fixed-rig identical; blind audit 10/10
    signatures.
- **Pinned regression baselines for cycle 44**: unittest 124 OK; aikit
  5/5; standing 466/240/217; multi 9/18/11/13/14 with 1.0; multi
  goldens 5/5 paths; three-blocker 15/12/10/13/200 with rewards and
  5/5 paths; blind kills multi 4/4 + three 3/3 pinned (sufficient
  (5,0) 9/1.0, (6,0) 10/1.0 and truncation (6,5) 200/0.0 honestly
  carried); seed-74 9 intact / 200 blind; 0-99 1581/800/683;
  T1 100-199 1646; T3 100-199 732; T3 200-299 718; T3 300-399 671;
  T3 400-499 675; holdout 1581/800/738; exhaustive 3906/3906 27860;
  corridor-cut 12/744; random floor 1271/5.0 vs 89/11.0; chain ok +
  5 findings; headers ffa19359...; golden 9/9 + multi 5/5 + three
  5/5; pins 16/8/13/6/9 + 7/14 + 6/10; fixed-rig syn 0.05411532
  phi 0.0 n32; hub0/m0 0.0 p0/s0 identical; manifest + repro
  variance 0.

## Cycle 44 — full audit, zero verified safe improvements (STOP)
- **Baseline** (cycle-43 pins re-verified, same rig/seeds):
  - canonical: 124 OK; aikit 5/5 PASS.
  - code behavior: standing 466/240/217; T1-100 1581; T1 100-199
    1646; T3 ranges 732/718/671/675; holdout 1581/800/738;
    exhaustive T3 3906/3906 total 27860; T1 exhaustive 39711/39711
    carried; multi 9/18/11/13/14 with 1.0; three-blocker
    15/12/10/13/200 with rewards; goldens 9/9 + multi 5/5 + three
    5/5 paths.
  - trace internals: fixed-rig syn 0.05411532 syn_n 0.10814360
    phi 0.0 n32; hub0/m0 0.0; p0/s0 identical; errors zero.
  - model-seam internals: digest ffa19359... (viability leaf,
    corridor True, visits True, recall full-history, pooling visits,
    pool_corridor >=2); manifest True; visit-oracle 5/5; hidden
    13/16; persistent-hidden 13/6; hidden-T1 16/12/18; headers cite
    current digest with chain verify ok.
  - substrate re-read: planner/_step_toward pooling conditional
    (>=2 corridor-weighted, 1 visits-only, 0 viable-first);
    memory/store persistent recall never read by planner; hub
    last_action written-not-read (except collected_positions);
    planner_tracker/self_model unit-only; telemetry bins strict.
  - audit scans (new): 3-blocker family 5/5 pinned; blind matrices
    multi 4/4 + three 3/3 killing pinned; 19 golden paths exact.
  - dead ends, one line each: multi detours +6/+2/+2/+2 and
    3-blocker +2/+2/+2/+2 fixable only by breaking T1-100 goldens
    and seed-74 blind (proven cycles 35/37: naive pool 5 FAIL);
    3-blocker truncation (6,5) 200/0.0 reserved (same proof);
    axis-order swap breaks 19 goldens + 39711/3906 (no surviving
    eval); depth revival untested on multi, risks 3906 single proof;
    mean_conf consumed by nothing (churn); hub last_action dead
    (except collected); persistent store zero headroom on current
    tasks (reserved); tracker/self_model unit-only; T2 wait
    unreachable (min distance 7 > 2); energy never binds (200/200
    caps together); phi/P/S gameable if read (refused); live
    fine-tuning blocked (torch/TRL + approval); new task family in
    an audit cycle is scope expansion, not a gap fix; codebase map
    warning is bookkeeping (gate still 5/5).
- **Gap**: none qualifies. Routing optimal everywhere except
  reserved detours/truncation whose fixes break carried pins;
  every remaining candidate is dead, refused, blocked, or reserved
  (see dead ends). No depth chase (pool already balanced);
  no metric edits (gaming); no new family in an audit cycle.
- **Target delta**: none. Falsifier is moot: any change would need a
  failing eval first, and none exists that survives the quadruple
  without regressing 19 goldens, 39711/3906, or blind coupling.
- **Change**: none. No code, no harness, no ADR (audit result, not
  a design decision).
- **After**: identical battery re-verified — 124 OK, 5/5, 30-seed
  466/240/217, fixed-rig syn 0.05411532 phi 0.0 n32, multi and
  three-blocker pins identical. No deltas, variance not applicable.
- **Ablation**: none (no integration claim).
- **Verdict**: full cycle with zero verified safe improvements.
  Stopping per goal rule (allowed stop: told to stop, zero-findings
  cycle, or unfixable gate failure). Verdict STOP.
- **Gates**: unittest 124/124 OK (re-verified, no changes); aikit 5/5
  PASS (re-verified, no changes).
- **Commands run**:
  - `python -m unittest discover -s tests -t .` -> 124 OK.
  - `python aikit.py check brain` -> 5/5.
  - standing 30-seed + T1-100 + fixed-rig + multi/three pins
    re-verified identical.
- **Pinned regression baselines carried (no new pins)**: unittest 124
  OK; aikit 5/5; standing 466/240/217; multi 9/18/11/13/14; multi
  goldens 5/5; three-blocker 15/12/10/13/200 + 5/5 paths; blind
  kills 4/4 + 3/3; seed-74 9/200; 0-99 1581/800/683; exhaustive
  27860; headers ffa19359...; fixed-rig syn 0.05411532 phi 0.0 n32;
  hub0/m0 0.0 p0/s0 identical.

## Cycle 45 - persistent layout recall for cold-start recovery

- **Baseline** (clean HEAD worktree 3a4ea9a; identical harness, model label, seeds and probe code):
  - canonical gate: 124 tests OK before the new tests; aikit check 5/5.
  - standing behavior: 30-seed T1 466 / T2 240 / T3 217; T1 seeds 0-99 1581; fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0.
  - cold-start battery (T1:71, T2:3, T3:15, T3:65; capture backend): success 0/4; steps 200/200/200/200; reward 0/0/0/0; transfer gain 0; recovery 0; probe absent; model observations lacked items_positions/target/cue/obstacles; action hash 4b2b1802... for every case.
- **Gap**: the persistent MemoryStore is written every step but read only through count(); Planner.plan recalls from the current state then the in-memory episode. A restart with hidden goal fields has no route to the persisted layout.
- **Target delta**: success 0/4 -> 4/4; steps 200/200/200/200 -> 16/8/13/6; rewards 0 -> 3/1/1/1; gain 0 -> .92/.96/.935/.97; trace probe store_reads 0 -> 1 with persistent fields; model observation keys gain the recovered fields; ablation restores baseline.
- **Falsifier**: any cold case stays at 200/0; ablation does not; any standing pin moves; probe does not name the persistent source.
- **Change**: memory/store.py additive layouts table plus first-write-wins save_layout/get_layout; agent.py layout persistence, recall-source binding, lazy episode cache with task-field gating, per-plan probe in telemetry args, PLANNER_POLICY recovery_recall; evals/coldstart.py warm/cold/ablation battery with capture backend; tests/test_coldstart_recovery.py five failing-first tests.
- **After** (same harness, same model label CaptureBackend, same seeds, same probe code):
  - cold-start: success 4/4; steps 16/8/13/6; rewards 3/1/1/1; gain .92/.96/.935/.97; recovery 1.0 x4; action hashes match the four standing goldens (bafe50ff..., 8d077e83..., 63c67660..., 8484f2ab...).
  - trace: first probe store_reads 1; persistent [items_positions] / [cue,target] / [obstacles,target] / [obstacles,target]; model first-observation keys include those fields.
  - model-track prompt hashes (same capture model/seed): T1:71 19843a2f -> 53ff78c8; T2:3 b1014f83 -> d8da4712; T3:15 0663429f -> d0447fba; T3:65 495e6bbc -> 34fd0e2f.
  - standing behavior and trace: 466/240/217; T1 seeds 0-99 1581; fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0; warm probe store_reads 0 and persistent [] (store not consulted when the state carries the fields).
  - recompute syn/phi on cold logs: 0.0/0.0 (terminal-sparse reward; no synergy claim).
- **Ablation** (bind_recall_source(None), same seeds and store):
  - behavior: success 0/4; steps 200/200/200/200; rewards 0; gain 0; recovery 0.
  - trace: store_reads 0; persistent []; model observations lack the goal fields; action hash 4b2b1802... equals the pre-change baseline. Property and trace die with the cut.
- **Verdict**: integration confirmed for cold-start recovery only. No sentience or general emergence claim; the numeric synergy estimator is flat, and the claim rests on the behavior quadruple plus the source probe and its ablation.
- **Gates**: unittest 129/129 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_coldstart_recovery -v` -> before: 2 failures, 3 errors; after: 5 OK.
  - `python -m evals.coldstart --capture` -> before (HEAD worktree) / after JSON; `--ablate` for the cut.
  - `python -m unittest discover -s tests -t .` -> 129 OK.
  - `python aikit.py check brain` -> 5/5.
  - standing scan -> 466/240/217, T1 seeds 0-99 1581, fixed syn 0.05411532 phi 0.0, warm store_reads 0.
- **Pinned regression baselines for cycle 46**: unittest 129 OK; aikit 5/5; cold-start 16/8/13/6 with 3/1/1/1; cold ablate/before 200/200/200/200 with 0; probe store_reads 1 cold / 0 warm; model obs keys include the recovered fields; standing 466/240/217; T1 seeds 0-99 1581; holdout 500-599 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; policy f53f99a8...; goldens 9/9 + multi 5/5 + three 5/5.
