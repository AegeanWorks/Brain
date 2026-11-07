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
