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

## Cycle 46 - layout completeness gate and incomplete-row healing

- **Baseline** (commit cdd5479, cycle 45; identical cold-first harness, model label, seeds and probes):
  - canonical gate: 129 tests OK; aikit check 5/5; policy f53f99a8...
  - standing behavior: 30-seed T1 466 / T2 240 / T3 217; T1 seeds 0-99 1581; fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0.
  - cold-first battery (cold with empty store -> warm -> cold; T1:71, T2:3, T3:15, T3:65): cold1 200/200/200/200 with 0 reward; layout after cold1 stripped (energy/items/steps/task/x/y only); warm 16/8/13/6 with 3/1/1/1; layout after warm still stripped; cold2 200/200/200/200 with 0 reward; cold2 probe persistent []; model observations lacked goal fields; cold2 action hash 4b2b1802... for all four.
- **Gap**: a cold-first run writes an incomplete layout, and first-write-wins then prevents a later complete warm run from replacing it. Recovery is permanently disabled for that (task, seed).
- **Target delta**: cold2 success 0/4 -> 4/4; cold2 steps 200/200/200/200 -> 16/8/13/6; cold2 rewards 0 -> 3/1/1/1; layout after cold1 stripped -> absent; layout after warm stripped -> complete; cold2 probe persistent [] -> task fields; model observations gain the recovered fields; gate-patch ablation restores the baseline.
- **Falsifier**: cold-first still writes a layout, warm still cannot heal it, cold2 stays at 200/0, or any standing pin moves.
- **Change**: agent.py `_layout_complete` gate and complete-over-incomplete healing in `_remember_layout`; memory/store.py `save_layout(..., replace=True)` upsert path (default remains first-write-wins); evals/coldstart.py `cold-first` scenario; tests/test_coldstart_recovery.py three new failing-first tests.
- **After** (same harness, same model label CaptureBackend, same seeds, same probes):
  - cold1: 200/200/200/200 with 0 reward (expected: no layout exists yet); layout after cold1 absent for all four.
  - warm: 16/8/13/6 with 3/1/1/1; layout after warm contains items_positions for T1, cue+target for T2, target+obstacles for T3.
  - cold2: success 4/4; steps 16/8/13/6; rewards 3/1/1/1; gain .92/.96/.935/.97; recovery 1.0 x4; action hashes match the four standing goldens (bafe50ff..., 8d077e83..., 63c67660..., 8484f2ab...).
  - trace: cold2 probe store_reads 1; persistent [items_positions] / [cue,target] / [obstacles,target] / [obstacles,target]; model first-observation keys include those fields; prompt hashes 53ff78c8 / d8da4712 / d0447fba / 34fd0e2f (same as the cycle-45 recovered runs).
  - cold2 recompute syn/phi: 0.0/0.0 (terminal-sparse reward; no synergy claim).
  - warm-cold cycle-45 battery unchanged: 16/8/13/6 with 3/1/1/1; ablation 200/200/200/200 with 0.
  - standing behavior and trace: 466/240/217; T1 seeds 0-99 1581; fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0; warm probe store_reads 0 and persistent [].
- **Ablation** (patch `Agent._layout_complete` to always True, same seeds and store):
  - cold1 writes a stripped layout; warm cannot heal; cold2 200/200/200/200 with 0 reward; probe persistent []; model observations lack goal fields; cold2 action hash 4b2b1802..., equal to baseline. Property and trace die with the cut.
- **Verdict**: integration confirmed for layout durability. The cycle fixes a self-inflicted recovery loss without changing the planner policy digest; the claim rests on the cold-first behavior quadruple plus the completeness-gate ablation.
- **Gates**: unittest 132/132 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_coldstart_recovery -v` -> before: 2 failures, 1 error; after: 8 OK.
  - `python -m evals.coldstart --scenario cold-first --capture` -> 4/4 recovered after warm.
  - `python -m evals.coldstart --scenario cold-first --capture --ablate` -> 200/0 x4, stripped layout.
  - `python -m evals.coldstart --capture` -> cycle-45 warm-cold battery unchanged.
  - `python -m unittest discover -s tests -t .` -> 132 OK.
  - `python aikit.py check brain` -> 5/5.
  - standing scan -> 466/240/217, T1 seeds 0-99 1581, fixed syn 0.05411532 phi 0.0, warm store_reads 0.
- **Pinned regression baselines for cycle 47**: unittest 132 OK; aikit 5/5; cold-first 200/200/200/200 then 16/8/13/6 with 3/1/1/1; cold-first layout absent after cold1 and complete after warm; warm-cold 16/8/13/6; ablation 200/0; probe store_reads 1 cold / 0 warm; standing 466/240/217; T1 seeds 0-99 1581; holdout 500-599 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; policy f53f99a8...; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 47 - bounded trust for legal backend proposals

- **Baseline** (commit b1de6ca, cycle 46; same WaitingBackend, seeds, prompts and probes):
  - canonical gate: 132 tests OK; aikit check 5/5; policy f53f99a8...
  - standing behavior: 30-seed T1 466 / T2 240 / T3 217; T1 seeds 0-99 1581; fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0.
  - stalled backend (`wait` every step): success 0/4; steps 200/200/200/200; reward 0; fallbacks 0; model calls 200; no `model_decision` probe; prompt hashes 6e19bc1d / 78c208fb / 816fa226 / ae3c4f52; gain 0; recovery 0; action hash 4b2b1802... for all four.
- **Gap**: the planner returns any legal backend proposal forever, so a stalled but legal policy cannot be corrected. The hub's outcome fields are written but not load-bearing.
- **Target delta**: success 0/4 -> 4/4; steps 200/200/200/200 -> <=40 each; rewards 0 -> 3/1/1/1; trace gains proposed/rule/steps_since_reward/distrusted/accepted and nonzero fallbacks; prompts stay byte-identical; ablation (`trust_window=None`) restores the stall.
- **Falsifier**: any pin case remains at 200/0; the gate changes rule-only or good-backend actions; the prompts differ; or the ablation does not restore the stall.
- **Change**: agent.py extracts the rule action before the backend decision, reads `steps_since_reward` from the hub, trusts legal proposals until the 20-step stall window, then keeps the backend match-only for the episode (`reset_trust` per episode); telemetry probe `model_decision`; PLANNER_POLICY `backend_trust: stall>=20->match-only`; README trust contract; evals/trust.py battery; tests for stall, ablation, good-backend, policy and validation; random-floor control disables the gate to keep measuring raw randomness.
- **After** (same backend, seeds, prompts and probe code):
  - success 4/4; steps 36/28/33/26; rewards 3/1/1/1; gain .82/.86/.835/.87; recovery 1.0 x4.
  - trace: fallbacks 16/8/13/6; rejected_steps 16/8/13/6; model calls 36/28/33/26; last decision shows `distrusted: true`, `accepted: false`, `proposed: wait`, rule action at that step; prompt hashes unchanged (6e19bc1d / 78c208fb / 816fa226 / ae3c4f52).
  - action hashes 90a61333 / 1736021f / 33d9f09c / 55e279bf (the first 20 waits differ from the rule-only paths by construction).
  - intermediate prototype (trust reset on every reward) measured T1 76 steps; changed to episode-scoped match-only before pinning the final numbers.
  - rule-only standing behavior and trace unchanged: 466/240/217; T1 seeds 0-99 1581; fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0; good-backend replay still 0 fallbacks.
- **Ablation** (`trust_window=None`, same backend/prompts/seeds):
  - success 0/4; steps 200/200/200/200; rewards 0; fallbacks 0; model calls 200; decision accepted=true, distrusted=false; gain 0; recovery 0; prompt hashes identical; action hash 4b2b1802... equals baseline. Property and trace die with the cut.
- **Verdict**: integration confirmed for backend stall safety. The model receives byte-identical prompts; only the planner's acceptance decision and its trace change, and the rule-only path is untouched.
- **Gates**: unittest 137/137 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_model_backend -v` -> 8 OK.
  - `python -m evals.trust` -> 4/4 recovered; `--ablate` -> 200/0 x4.
  - `python -m unittest discover -s tests -t .` -> 137 OK.
  - `python aikit.py check brain` -> 5/5.
  - standing scan -> 466/240/217, T1 seeds 0-99 1581, fixed syn 0.05411532 phi 0.0, warm store_reads 0.
- **Pinned regression baselines for cycle 48**: unittest 137 OK; aikit 5/5; trust after 36/28/33/26 with 3/1/1/1 and fallbacks 16/8/13/6; trust ablate 200/0 x4; prompt hashes 6e19bc1d/78c208fb/816fa226/ae3c4f52 unchanged; standing 466/240/217; T1 seeds 0-99 1581; holdout 500-599 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; policy e400adcd...; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 48 - honest verdicts at the step cap

- **Baseline** (commit 409c17e, cycle 47; same stalled backend, seeds and prompts):
  - canonical gate: 137 tests OK; aikit check 5/5; policy e400adcd...
  - standing behavior: 30-seed T1 466 / T2 240 / T3 217; T1 seeds 0-99 1581; fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0.
  - stalled-backend cap run: 200 steps, 0.0 reward, 402 records, verdict `done`, reason `steps=200`.
  - trusted-backend success run: 33 steps, 1.0 reward, 68 records, verdict `done`, reason `steps=33`.
- **Gap**: the world sets `done` at the step/energy cap, so `run_task_logged` labels a failed 200-step run as a success. The trace says `done` while the reward is 0.0.
- **Target delta**: cap verdict `done` -> `truncated`; cap reason `steps=200` -> `steps=200 reward=0.0`; success reason gains `reward=1.0`; behavior actions, steps and rewards stay identical; the legacy-predicate ablation restores `done`.
- **Falsifier**: the cap still reads `done`; the success run becomes `truncated`; record count or chain changes; any standing pin moves.
- **Change**: agent.py `_episode_verdict` distinguishes pre-cap completion from budget exhaustion and carries steps+reward in the reason; `run_task_logged` consumes it; tests/test_verdict.py adds success, cap and legacy-predicate ablation; README verdict-facts contract. No policy change; no new deps.
- **After** (same runs):
  - behavior unchanged: cap 200 steps / 0.0 reward; success 33 steps / 1.0 reward; 402 and 68 records.
  - trace: cap verdict `truncated`, reason `steps=200 reward=0.0`; success verdict `done`, reason `steps=33 reward=1.0`.
  - policy e400adcd... unchanged; standing 466/240/217, T1 seeds 0-99 1581, fixed syn 0.05411532 phi 0.0 unchanged.
  - recompute syn/phi for the cap run: 0.0/0.0 (terminal-sparse reward; no synergy claim).
- **Ablation** (patch `Agent._episode_verdict` to the legacy `done` predicate, same seed and backend):
  - cap verdict returns to `done`, reason `steps=200`; behavior unchanged. The corrected fact and its trace die with the cut.
- **Verdict**: measurement-integrity fix, trace-only instrumentation by design. No behavior or emergence claim; the value is that a capped run can no longer read back as a success.
- **Gates**: unittest 140/140 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_verdict -v` -> before: 2 failures, 1 error; after: 3 OK.
  - `python -m unittest discover -s tests -t .` -> 140 OK.
  - `python aikit.py check brain` -> 5/5.
  - verdict baseline/after script -> cap done/steps=200 -> truncated/steps=200 reward=0.0; success done/steps=33 -> done/steps=33 reward=1.0.
  - standing scan -> 466/240/217, T1 seeds 0-99 1581, fixed syn 0.05411532 phi 0.0.
- **Pinned regression baselines for cycle 49**: unittest 140 OK; aikit 5/5; cap verdict truncated with reward 0.0; success verdict done with reward 1.0; record counts 402/68; standing 466/240/217; T1 seeds 0-99 1581; holdout 500-599 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; policy e400adcd...; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 49 - full audit, zero verified safe improvements (STOP)

- **Baseline** (commit bebfb50, cycle 48; no code change in this cycle):
  - canonical gate: 140 tests OK; aikit check 5/5; policy e400adcd...
  - standing behavior: 30-seed T1 466 / T2 240 / T3 217; T1 seeds 0-99 1581; fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0.
  - cold-start warm-cold: 16/8/13/6 steps with 3/1/1/1, success 4/4, probe persistent fields.
  - cold-first: cold1 200/200/200/200 with 0, layout absent; cold2 16/8/13/6 with 3/1/1/1, success 4/4.
  - model trust: stalled legal backend 36/28/33/26 with 3/1/1/1, fallbacks 16/8/13/6; `trust_window=None` 200/200/200/200 with 0.
  - verdict facts: cap 200/0 -> `truncated` with `reward=0.0`; success 33/1 -> `done` with `reward=1.0`.
- **Gap**: none qualifies. Candidates audited and rejected, one line each:
  - cumulative `planner.fallbacks` across reused planner episodes: no current harness reuses an episode; the per-step `model_decision` probe carries acceptance, so no claim moves.
  - trust window hard-coded at 20: declared in `PLANNER_POLICY` and the constructor; no failing eval.
  - harnesses duplicate success-verdict logic: consistent with `_episode_verdict` on current runs; cleanup only, no number moves.
  - moving `steps_since_reward` into the persistent SelfModel/S vector: same value, same behavior, refactor only.
  - layout schema version / world fingerprint: no current failing eval; version or custom-world scenarios are a new task family, not a gap fix.
  - llama.cpp retry/backoff: no local server or weights; untestable in this battery, speculative.
  - `mean_conf` still has no consumer: inventing a confidence policy is not a measured gap.
  - `planner_tracker` remains unit-only: no behavior gap in the grid loop.
  - custom-world layout key collision: built-in task/seed layouts are deterministic; exercising it needs a new world family.
- **Target delta**: none. Falsifier is moot: any change would need a failing eval first, and none exists that survives the four-slot battery without regressing the 140-test pin set or adding a speculative family.
- **Change**: none. No code, no harness, no ADR (audit result, not a design decision).
- **After**: identical battery re-verified: 140 OK, 5/5, 466/240/217, cold-start 16/8/13/6, cold-first 200 -> 16/8/13/6, trust 36/28/33/26, verdict facts unchanged. No deltas, variance not applicable.
- **Ablation**: none (no integration claim).
- **Verdict**: full cycle with zero verified safe improvements. Stopping per the goal rule (allowed stop: zero-findings cycle). STOP.
- **Gates**: unittest 140/140 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest discover -s tests -t .` -> 140 OK.
  - `python aikit.py check brain` -> 5/5.
  - `python -m evals.coldstart --capture` -> warm-cold 16/8/13/6.
  - `python -m evals.coldstart --scenario cold-first --capture` -> cold1 200, cold2 16/8/13/6.
  - `python -m evals.trust` -> 36/28/33/26 with fallbacks 16/8/13/6.
  - `python -m evals.trust --ablate` -> 200/0 x4.
  - `git -C projects/brain grep -n "steps_since_reward|model_decision|save_layout|get_layout|_layout_complete|fallbacks" -- "*.py"` -> all channels have live consumers.
  - standing scan -> 466/240/217, T1 seeds 0-99 1581, fixed syn 0.05411532 phi 0.0.
- **Pinned regression baselines carried (no new pins)**: unittest 140 OK; aikit 5/5; cold-start 16/8/13/6; cold-first 200 then 16/8/13/6; trust 36/28/33/26 with fallbacks 16/8/13/6; trust ablate 200/0; verdict cap truncated/reward 0.0; standing 466/240/217; T1 seeds 0-99 1581; holdout 500-599 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; policy e400adcd...; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 50 - reject legal no-op backend proposals immediately

- **Baseline** (commit 1430c4c, cycle 49; same WaitingBackend, seeds, prompts and probes):
  - canonical gate: 140 tests OK; aikit check 5/5; policy e400adcd...
  - standing behavior: 30-seed T1 466 / T2 240 / T3 217; T1 seeds 0-99 1581; fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0.
  - stalled backend (`wait` every step, trust on): success 4/4 but steps 36/28/33/26; rewards 3/1/1/1; fallbacks 16/8/13/6; first decision accepted=true, last rejected with distrusted=true; prompt hashes 6e19bc1d / 78c208fb / 816fa226 / ae3c4f52; gain .82/.86/.835/.87.
- **Gap**: the trust gate waits 20 unrewarded steps before rejecting `wait`, even when the rule has a productive move. `wait` is a legal but dominated no-op; the 20-step delay is pure cost (T1 36 vs rule-optimal 16).
- **Target delta**: steps 36/28/33/26 -> 16/8/13/6; gain .82/.86/.835/.87 -> .92/.96/.935/.97; first decision rejected with reason `no-op`; prompts unchanged; ablation with `noop_guard=False` restores 36/28/33/26.
- **Falsifier**: any case stays above the rule-optimal step count; the no-op guard changes a rule-only or good-backend run; prompts differ; the no-op-off ablation does not restore the stall.
- **Change**: Planner `noop_guard` (default on, independent of `trust_window`); reject `wait` when the rule action is not wait, and `collect` when the rule action is not collect; `model_decision.reason`; PLANNER_POLICY `backend_noop_guard: on`; trust battery adds `--ablate-noop`, `--ablate-trust`, `--ablate`; random-floor control disables both guards; three new tests and two updated setup tests.
- **After** (same backend, seeds, prompts and probe code):
  - success 4/4; steps 16/8/13/6; rewards 3/1/1/1; gain .92/.96/.935/.97; recovery 1.0 x4; action hashes match the four standing goldens (bafe50ff, 8d077e83, 63c67660, 8484f2ab).
  - trace: fallbacks 16/8/13/6; first and last decision accepted=false, reason `no-op`, distrusted=false; prompt hashes identical to baseline.
  - rule-only standing behavior and trace unchanged: 466/240/217; T1 seeds 0-99 1581; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; good-backend replay 0 fallbacks; policy e400adcd... -> 180ba03d....
- **Ablation** (same backend/prompts/seeds):
  - no-op guard off, trust on: 36/28/33/26, first accepted=true, last `stall`/distrusted=true; exactly the baseline.
  - trust off, no-op guard on: 16/8/13/6, first/last `no-op`; the guard works without the stall window.
  - both off: 200/200/200/200 with 0 reward, accepted=true; raw backend control.
- **Verdict**: integration confirmed for the no-op guard. The model receives byte-identical prompts; the planner rejects a dominated legal token immediately, and the two-level ablation separates the no-op guard from the stall gate.
- **Gates**: unittest 143/143 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_model_backend tests.test_random_floor -v` -> 13 OK.
  - `python -m evals.trust` -> 16/8/13/6; `--ablate-noop` -> 36/28/33/26; `--ablate-trust` -> 16/8/13/6; `--ablate` -> 200/0 x4.
  - `python -m unittest discover -s tests -t .` -> 143 OK.
  - `python aikit.py check brain` -> 5/5.
  - standing scan -> 466/240/217, T1 seeds 0-99 1581, fixed syn 0.05411532 phi 0.0.
- **Pinned regression baselines for cycle 51**: unittest 143 OK; aikit 5/5; trust 16/8/13/6 with 3/1/1/1 and fallbacks 16/8/13/6; ablate-noop 36/28/33/26; ablate-trust 16/8/13/6; ablate-both 200/0; prompt hashes 6e19bc1d/78c208fb/816fa226/ae3c4f52; standing 466/240/217; T1 seeds 0-99 1581; holdout 500-599 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; policy 180ba03d...; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 51 - reject blocked-movement backend proposals as no-ops

- **Baseline** (commit 6013fd8, cycle 50; same NoopBackend, seeds, prompts and probes):
  - canonical gate: 143 tests OK; aikit check 5/5; policy 180ba03d...
  - standing behavior: 30-seed T1 466 / T2 240 / T3 217; T1 seeds 0-99 1581; fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0.
  - blocked-movement backend (`up` at a boundary or into an obstacle): success 4/4 but steps 36/28/33/26; rewards 3/1/1/1; fallbacks 16/8/13/6; first decision accepted=true with reason accepted; last rejected with distrusted=true; prompt hashes 4bd74314 / 7f1f5088 / 4f18a4b6 / e05d4d08; action hashes 70d2f67f / d510a6a0 / 5f561866 / bb9eba25.
- **Gap**: the no-op guard covered `wait` and premature `collect` but not a movement whose target is outside the board or in the obstacle set. Such a proposal is legal yet cannot change position, so it still burns the 20-step trust window.
- **Target delta**: steps 36/28/33/26 -> 16/8/13/6; gain .82/.86/.835/.87 -> .92/.96/.935/.97; first decision rejected with reason `no-op`; prompts unchanged; ablation with `noop_guard=False` restores 36/28/33/26.
- **Falsifier**: any case stays above the rule-optimal step count; the guard changes a rule-only or good-backend run; prompts differ; the no-op-off ablation does not restore the stall.
- **Change**: agent.py `_movement_noop` checks the proposed direction against the board bounds and current obstacle set, rejecting it when it differs from the rule action; same `noop_guard` flag; evals/trust.py adds a `NoopBackend` and `--backend noop`; tests cover immediate rejection and the no-guard stall window.
- **After** (same backend, seeds, prompts and probe code):
  - success 4/4; steps 16/8/13/6; rewards 3/1/1/1; gain .92/.96/.935/.97; recovery 1.0 x4; action hashes match the four standing goldens (bafe50ff, 8d077e83, 63c67660, 8484f2ab).
  - trace: fallbacks 16/8/13/6; first proposed `up` rejected as no-op; distrusted=false throughout; prompt hashes identical to baseline.
  - rule-only standing behavior and trace unchanged: 466/240/217; T1 seeds 0-99 1581; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; good-backend replay 0 fallbacks; policy 180ba03d... unchanged.
- **Ablation** (same backend/prompts/seeds):
  - no-op guard off, trust on: 36/28/33/26, first accepted=true, last distrusted=true; exactly the baseline.
  - both guards off: 200/200/200/200 with 0 reward, accepted=true; raw backend control.
  - trust off with the no-op guard on was already pinned in cycle 50 at 16/8/13/6; the new guard is independent of it.
- **Verdict**: integration confirmed for blocked-movement no-ops. The model receives byte-identical prompts; the planner rejects an impossible legal move immediately, and the ablation restores the 20-step stall.
- **Gates**: unittest 145/145 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_model_backend tests.test_random_floor -v` -> 15 OK.
  - `python -m evals.trust --backend noop` -> 16/8/13/6; `--backend noop --ablate-noop` -> 36/28/33/26; `--backend noop --ablate` -> 200/0 x4.
  - `python -m unittest discover -s tests -t .` -> 145 OK.
  - `python aikit.py check brain` -> 5/5.
  - standing scan -> 466/240/217, T1 seeds 0-99 1581, fixed syn 0.05411532 phi 0.0.
- **Pinned regression baselines for cycle 52**: unittest 145 OK; aikit 5/5; noop backend 16/8/13/6 with 3/1/1/1 and fallbacks 16/8/13/6; noop ablate-noop 36/28/33/26; noop ablate-both 200/0; wait backend 16/8/13/6; prompt hashes 4bd74314/7f1f5088/4f18a4b6/e05d4d08; standing 466/240/217; T1 seeds 0-99 1581; holdout 500-599 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; policy 180ba03d...; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 52 - full audit after the no-op guard closure, zero verified safe improvements (STOP)

- **Baseline** (commit d0203a2, cycle 51; no code change in this cycle):
  - canonical gate: 145 tests OK; aikit check 5/5; policy 180ba03d...
  - standing behavior: 30-seed T1 466 / T2 240 / T3 217; T1 seeds 0-99 1581; fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0.
  - cold-start warm-cold: 16/8/13/6 with 3/1/1/1; cold-first: 200 then 16/8/13/6.
  - wait backend: 16/8/13/6 with 3/1/1/1, fallbacks 16/8/13/6.
  - noop (blocked-movement) backend: 16/8/13/6 with 3/1/1/1, fallbacks 16/8/13/6.
  - noop ablate-noop: 36/28/33/26; noop ablate-both: 200/0 x4.
- **Gap**: none qualifies. Candidates audited and rejected, one line each:
  - free-cell reverse/unproductive movement: the 20-step trust window is the declared mechanism; a shortest-path progress guard would reject legitimate detours and requires a new adversarial backend, so it is policy tuning, not a bug fix.
  - moving the stall counter into the persistent SelfModel/S vector: same values and behavior, refactor only.
  - planner-tracker integration: no failing behavior eval; needs a new plan representation, not a gap fix.
  - layout key collision / custom-world variants: built-in layouts are deterministic per task/seed; exercising it needs a new task family.
  - llama.cpp retry/backoff: no local server or weights; untestable in this battery, speculative.
  - harness verdict duplication and cumulative fallback counter: no current claim or number moves.
  - trust-window tuning (20 -> lower): declared safety threshold; tuning without a failing eval is not a gap.
  - `mean_conf` still has no consumer: inventing a confidence policy is not a measured gap.
- **Target delta**: none. Falsifier moot: any change would need a failing eval first, and none exists that survives the four-slot battery without regressing the 145-test pin set or adding a speculative family.
- **Change**: none. No code, no harness, no ADR (audit result, not a design decision).
- **After**: identical battery re-verified: 145 OK, 5/5, 466/240/217, cold-start 16/8/13/6, cold-first 200 -> 16/8/13/6, wait/noop 16/8/13/6, noop ablate-noop 36/28/33/26, both off 200/0. No deltas.
- **Ablation**: none (no integration claim).
- **Verdict**: full cycle with zero verified safe improvements. Stopping per the goal rule (zero-findings cycle). STOP.
- **Gates**: unittest 145/145 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest discover -s tests -t .` -> 145 OK.
  - `python aikit.py check brain` -> 5/5.
  - `python -m evals.trust` -> wait 16/8/13/6; `--backend noop` -> 16/8/13/6; `--backend noop --ablate-noop` -> 36/28/33/26; `--backend noop --ablate` -> 200/0.
  - `python -m evals.coldstart --capture` -> 16/8/13/6; `--scenario cold-first --capture` -> 200 then 16/8/13/6.
  - standing scan -> 466/240/217, T1 seeds 0-99 1581, fixed syn 0.05411532 phi 0.0.
- **Pinned regression baselines carried (no new pins)**: unittest 145 OK; aikit 5/5; cold-start 16/8/13/6; cold-first 200 then 16/8/13/6; wait/noop 16/8/13/6; noop ablate-noop 36/28/33/26; both off 200/0; verdict facts cap truncated/reward 0.0; standing 466/240/217; T1 seeds 0-99 1581; holdout 500-599 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; policy 180ba03d...; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 53 - serialize telemetry hash-chain appends with an AIKit-style lock

- **Baseline** (commit c274de4, cycle 52; AIKit `file_lock` inspected in `scripts/disruption_recovery.py` and `idea_catcher/registry.py`):
  - canonical gate: 145 tests OK; aikit check 5/5; policy 180ba03d...
  - standing behavior: 30-seed T1 466 / T2 240 / T3 217; T1 seeds 0-99 1581; fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0.
  - two writers, one record each, slowed head read: `verify_chain` returned `ok=false`, findings `['broken-link:1']`, records 2.
  - lock-off concurrent battery (two writers x two records): `broken-link:1`, `broken-link:2`, verified prefix 2 of 4 expected records.
- **Gap**: `Telemetry._write_record` reads the head digest and appends without a lock. Two writers can both read the same head and emit stale links, so a concurrent log is not a single valid chain. AIKit already serialises ledger/registry read-modify-write cycles with a bounded, stale-breaking advisory lock.
- **Target delta**: concurrent two-writer chain `broken-link` -> `ok=true` with 4/4 records; single-writer behavior/trace unchanged; lock-off ablation reproduces the broken links; timeout surfaces instead of silent interleaving.
- **Falsifier**: concurrent chain still breaks; single-writer record count or standing pins move; timeout still writes unprotected; the lock-off ablation does not reproduce the break.
- **Change**: telemetry/log.py adds `_append_lock` (O_CREAT|O_EXCL lock file, PID/timestamp, 30s stale break by atomic rename, bounded `lock_timeout`, TimeoutError with Why/Fix); `_write_record` holds the lock from head read through fsync and refreshes a size-stale head; `Telemetry(lock_timeout=3.0)`; evals/telemetry_lock.py; tests/test_telemetry_concurrency.py (two-writer chain, single-writer chain, timeout, stale lock).
- **After** (same two-writer battery, same backend/prompts/seeds):
  - locked chain: `ok=true`, `chain_records=4`, `expected_records=4`, no findings, no worker errors.
  - single writer: chain `ok=true`, 3 records; existing telemetry, wiring and recompute tests unchanged.
  - behavior and standing trace: 466/240/217; T1 seeds 0-99 1581; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; policy 180ba03d... unchanged.
  - 149 tests OK; aikit 5/5.
- **Ablation** (patch `telemetry.log._append_lock` to a no-op, same writers/prompts):
  - `ok=false`, findings `broken-link:1`, `broken-link:2`; verified prefix 2 of 4 expected records. The serialized chain and its verdict die with the cut.
- **Verdict**: trace-integrity integration confirmed. This is the first AIKit transfer cycle; the mined shortlist also includes reachability/round-trip audits, proof/evidence envelopes, the codebase-map digest and test budgets, none of which is a current measured gap.
- **Gates**: unittest 149/149 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_telemetry_concurrency -v` -> before: 1 failure (`broken-link:1`); after: 4 OK.
  - `python -m evals.telemetry_lock` -> ok, 4/4 records; `--ablate` -> broken-link:1,2, prefix 2/4.
  - `python -m unittest discover -s tests -t .` -> 149 OK.
  - `python aikit.py check brain` -> 5/5.
  - standing scan -> 466/240/217, T1 seeds 0-99 1581, fixed syn 0.05411532 phi 0.0.
- **Pinned regression baselines for cycle 54**: unittest 149 OK; aikit 5/5; locked telemetry chain 4/4; lock-off ablation broken-link:1,2 with prefix 2/4; timeout test raises; stale lock test recovers; standing 466/240/217; T1 seeds 0-99 1581; holdout 500-599 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; policy 180ba03d...; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 54 - repeated-position BFS escape for multi-obstacle routing loops

- **Baseline** (commit 17f28b7, cycle 53; pre-change worktree replay with the same declining backend, seeds 0 and prompt code):
  - canonical gate: 149 tests OK; aikit check 5/5; policy 180ba03d386a53368fc66a95f4825e1d68b5717fd22e43564925f24600afb75e.
  - standing behavior: 30-seed T1 466 / T2 240 / T3 217; T1 seeds 0-99 1581; holdout 500-599 1581/800/738; fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0.
  - cycle-a (target [6,5], obstacles [6,4],[5,5],[3,5]): 200 steps, 0.0 reward, success false, 200 model calls, 200 fallbacks, no `cycle_escape` probe; action hash 8baacf99..., first prompt hash 398a93d3..., syn 0.0 syn_n 0.0 phi 0.0, 404 records.
  - cycle-b (target [6,4], obstacles [5,4],[6,0],[6,3]): 200 steps, 0.0 reward, success false, 200 model calls, 200 fallbacks, no probe; action hash c1ae3ac7..., first prompt hash aa934aba..., syn 0.0 syn_n 0.0 phi 0.0, 404 records.
  - 300-config seeded three-blocker scan: two truncations (cycle-a is the documented pin; cycle-b was found by the scan), all other sampled configs byte-identical under the prototype.
- **Gap**: the local viability/pool order builds visit counts from only the last four memories, so a six-cell loop never observes its own repeat and re-enters the same cycle until the 200-step cap. The documented (6,5) pin and the sampled (6,4) layout are both 200/0.
- **Target delta**: cycle-a 200/0 -> 19/1.0; cycle-b 200/0 -> 18/1.0; success 0/2 -> 2/2; gain 0 -> .905/.91; recovery 0 -> 1.0; trace gains `probe.cycle_escape` on the repeated cell; first prompts byte-identical; `cycle_escape=False` and the memory-blind cut restore 200/0.
- **Falsifier**: either case stays at 200/0; any standing, single-obstacle, multi, three, trust, cold-start or holdout pin moves; the first prompt hash changes; the escape-off ablation does not restore the exact baseline action hashes; or the memory-blind cut completes.
- **Change**: agent.py adds module-level `_bfs_step` (deque BFS, fixed up/down/left/right order), gates it inside `_rule_action` on target tasks with no remaining items and >=2 obstacles and current-cell count >=2 in the full episode history, records `probe.cycle_escape` with position/visits/distance/action, adds `Planner(cycle_escape=True)` and `PLANNER_POLICY["cycle_escape"] = "repeat>=2->bfs"`; evals/escape.py adds intact/ablate/blind modes with a declining backend; tests/test_cycle_escape.py adds recovery, ablation, blind, probe, determinism and policy tests; test_three_blocker.py and test_three_goldens.py update the (6,5) pin to 19/1.0 and its golden hash; README and ADR-050 record the contract. No new dependencies; no schema change.
- **After** (same backend class, seeds, prompt builder and probe code):
  - cycle-a: 19 steps, 1.0 reward, success true, 19 model calls, 19 fallbacks, 2 escape probes: first at [5,2] visits 2 distance 6 action down, second at [5,3] visits 2 distance 5 action right; action hash 9ed8486f..., first prompt hash 398a93d3... (unchanged); syn -0.005187576 syn_n -0.025158955 phi 0.0, 42 records.
  - cycle-b: 18 steps, 1.0 reward, success true, 18 model calls, 18 fallbacks, 2 escape probes (first at [5,1] visits 2 distance 6 action down); action hash 722c4c33..., first prompt hash aa934aba... (unchanged); syn -0.002387766 syn_n -0.011128706 phi 0.0, 40 records.
  - gain .905/.91; recovery 1.0; rule-only standing behavior and trace unchanged: 466/240/217; T1 seeds 0-99 1581; holdout 500-599 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; trust 16/8/13/6 with fallbacks 16/8/13/6; cold-start 16/8/13/6; multi pins 9/18/11/13/14; three pins 15/12/10/13/19; exhaustive T3 still 3906/3906. `policy_digest` 180ba03d... -> ea4450748ebd2c555e0017c7d346230c5366f72cd4dd16fd84bbf3f8f463cb73.
  - shipped 300-config scan: 0 changed, 0 regressed outside the fixed cycle; the sampled cycle-b 200/0 -> 18/1.0.
- **Ablation** (same backend class, seeds, prompts and probe code):
  - `cycle_escape=False`: cycle-a 200/0 action hash 8baacf99..., cycle-b 200/0 action hash c1ae3ac7...; no escape probe; syn 0.0 phi 0.0; prompt hashes unchanged. Exactly the pre-change baseline.
  - memory-blind (`plan(state, None)`): both cases 200/0, no escape probe; action hashes cd16b302.../367ab500..., prompt hashes 99f16255.../6e41e2a7... (the `visits` field is absent by construction). The property and the probe die with the memory cut.
- **Verdict**: integration confirmed for memory-driven repeated-position escape. Behavior improves (0/2 -> 2/2 success, 200/200 -> 19/18 steps) and the trace gains a `cycle_escape` readout; the escape-off and memory-blind controls restore the loop. No emergence claim beyond the measured dependency.
- **Gates**: unittest 156/156 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_cycle_escape -v` -> before: recovery FAIL (0.0 != 1.0), memory-cut OK; after: 7 OK.
  - `python -m unittest tests.test_cycle_escape tests.test_three_blocker tests.test_three_goldens -v` -> 10 OK.
  - `python -m unittest discover -s tests -t .` -> 156 OK.
  - `python -m evals.escape` / `--mode ablate` / `--mode blind` -> intact 19/18 with 1.0 and 2 probes; ablate 200/200 with 0.0 and no probe; blind 200/200 with 0.0 and no probe.
  - `python -m evals.trust` -> 16/8/13/6 with 3/1/1/1 and fallbacks 16/8/13/6; `python -m evals.coldstart --capture` -> 16/8/13/6 with store_reads 1.
  - pre-change worktree replay at 17f28b7 -> cycle-a 200/0 hash 8baacf99, cycle-b 200/0 hash c1ae3ac7, first prompts 398a93d3/aa934aba.
  - 300-config seeded scan -> 1 fixed, 0 changed, 0 regressed; fixed case 200/0 -> 18/1.0 with blind 200/0.
  - standing scan -> 466/240/217, T1 seeds 0-99 1581, holdout 1581/800/738, fixed syn 0.05411532 phi 0.0.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 55**: unittest 156 OK; aikit 5/5; cycle-a 19/1.0 action hash 9ed8486f..., prompt 398a93d3...; cycle-b 18/1.0 action hash 722c4c33..., prompt aa934aba...; escape-off 200/0 hashes 8baacf99.../c1ae3ac7...; blind 200/0 hashes cd16b302.../367ab500...; standing 466/240/217; T1 seeds 0-99 1581; holdout 500-599 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; policy ea445074...; multi pins 9/18/11/13/14; three pins 15/12/10/13/19; exhaustive 3906/3906; trust 16/8/13/6; cold-start 16/8/13/6; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 55 - skip redundant backend calls after the trust gate distrusts

- **Baseline** (commit c762408, cycle 54; same WaitingBackend, seeds, prompts and probe code):
  - canonical gate: 156 tests OK; aikit check 5/5; policy ea4450748ebd2c555e0017c7d346230c5366f72cd4dd16fd84bbf3f8f463cb73.
  - standing behavior: 30-seed T1 466 / T2 240 / T3 217; T1 seeds 0-99 1581; holdout 500-599 1581/800/738; fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0.
  - stalled backend with `--ablate-noop` (trust window on, no-op guard off): steps 36/28/33/26; rewards 3/1/1/1; success 4/4; 36/28/33/26 model calls; fallbacks 16/8/13/6; rejected steps 16/8/13/6; skipped 0; last decision `proposed=wait`, `reason=stall`, `distrusted=true`; action hashes 90a61333/1736021f/33d9f09c/55e279bf; prompt hashes 6e19bc1d/78c208fb/816fa226/ae3c4f52; syn 0.11612872882479021/0.006591080505772978/0.015843139290281194/0.010002568849882792, phi 0.0.
  - default no-op guard on: 16/8/13/6, calls 16/8/13/6; trust off: 16/8/13/6; both off: 200/200/200/200 with 0 reward, 200 calls.
- **Gap**: after the 20-step stall window the planner is match-only, so only a proposal equal to the rule action could be accepted, and that returns the same rule action. Every later backend call is therefore redundant: 15/7/12/5 calls per stalled episode. The reason ladder also checks `since >= window` before `distrusted`, so every post-window rejection reports `stall` and the declared `distrusted` reason is unreachable.
- **Target delta**: calls 36/28/33/26 -> 21/21/21/21; fallbacks 16/8/13/6 -> 1/1/1/1; skipped 0 -> 15/7/12/5; last reason `stall` -> `skipped`; actions, steps, rewards, success, M/P/S/hub vectors and syn/phi unchanged; `--no-skip` restores the calls, fallbacks and `reason=distrusted`.
- **Falsifier**: any action hash, step count, reward or syn/phi moves; calls are not reduced; `--no-skip` does not restore the baseline calls/fallbacks; the default no-op-guard, trust-off, standing or cold-start pins move.
- **Change**: agent.py adds `Planner(skip_after_distrust=True)` and skips `backend.generate` once `_backend_distrusted` is set, emitting `model_decision{proposed:null, skipped:true, reason:"skipped"}` without incrementing `fallbacks`; reorders the reason ladder so `stall` marks only the triggering step and `distrusted` is reachable; adds `PLANNER_POLICY["backend_distrust_skip"] = "on"`. evals/trust.py gains `--no-skip`, `skip_after_distrust` and `skipped_steps`; tests cover the skip, the cost ablation, the reason, the policy key and flag validation. README and ADR-051 record the contract. No new dependencies; no schema change.
- **After** (same backend, seeds, prompts and probe code):
  - steps 36/28/33/26, rewards 3/1/1/1, success 4/4 and action hashes 90a61333/1736021f/33d9f09c/55e279bf are byte-identical.
  - model calls 21/21/21/21; fallbacks 1/1/1/1; skipped steps 15/7/12/5; rejected steps 16/8/13/6; last decision `proposed=null`, `skipped=true`, `distrusted=true`, `reason=skipped`.
  - M/P/S/hub vectors are unchanged, so syn/phi are byte-identical: 0.11612872882479021/0.006591080505772978/0.015843139290281194/0.010002568849882792, phi 0.0. The probe readout is the delta, not the estimator.
  - default no-op guard on 16/8/13/6 with calls 16/8/13/6; trust off 16/8/13/6; both off 200/0 with calls 200; standing 466/240/217, T1 seeds 0-99 1581, holdout 1581/800/738, fixed syn 0.05411532 phi 0.0, cold-start 16/8/13/6, cycle-escape battery 19/18 with 1.0. `policy_digest` ea445074... -> 8c2c51bc964cbe74120131e0cd3dffeee0e1052c10a5f6869531b37654257c77.
- **Ablation** (same backend, seeds and prompts):
  - `--no-skip` (`skip_after_distrust=False`): calls 36/28/33/26, fallbacks 16/8/13/6, skipped 0, last reason `distrusted`; actions identical. The cost reduction and the `skipped` readout die with the cut.
  - trust off (raw): 200/200/200/200 with 0 reward and 200 calls; never distrusted, so the skip gate cannot fire.
- **Verdict**: model-seam cost and trace-integrity improvement. The action trace is unchanged; the measured deltas are calls (36/28/33/26 -> 21/21/21/21), fallbacks (16/8/13/6 -> 1/1/1/1), skipped steps (0 -> 15/7/12/5) and the honest `stall`/`distrusted`/`skipped` reasons. No action or emergence claim.
- **Gates**: unittest 158/158 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_model_backend.TestModelBackendSeam.test_stalled_legal_backend_falls_back_after_window -v` -> before: FAIL (33 calls == 33 steps); after: OK.
  - `python -m unittest tests.test_model_backend -v` -> 15 OK.
  - `python -m unittest discover -s tests -t .` -> 158 OK.
  - `python -m evals.trust` -> 16/8/13/6 with 16/8/13/6 calls, 0 skipped; `--ablate-noop` -> 36/28/33/26 with 21/21/21/21 calls, fallbacks 1/1/1/1, skipped 15/7/12/5; `--ablate-noop --no-skip` -> 36/28/33/26 with 36/28/33/26 calls, fallbacks 16/8/13/6, last reason distrusted; `--ablate` -> 200/0 with 200 calls.
  - `python -m evals.escape --mode intact/ablate/blind` -> 19/18, 200/200, 200/200 as pinned.
  - `python -m evals.coldstart --capture` -> 16/8/13/6 with store_reads 1.
  - standing scan -> 466/240/217, T1 seeds 0-99 1581, holdout 1581/800/738, fixed syn 0.05411532 phi 0.0.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 56**: unittest 158 OK; aikit 5/5; stalled `--ablate-noop` 36/28/33/26 with actions 90a61333/1736021f/33d9f09c/55e279bf, calls 21/21/21/21, fallbacks 1/1/1/1, skipped 15/7/12/5; `--no-skip` calls 36/28/33/26, fallbacks 16/8/13/6, last reason distrusted; default wait 16/8/13/6 calls 16/8/13/6; trust-off 16/8/13/6; both-off 200/0; escape 19/18; standing 466/240/217; T1 seeds 0-99 1581; holdout 500-599 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; policy 8c2c51bc...; multi pins 9/18/11/13/14; three pins 15/12/10/13/19; exhaustive 3906/3906; cold-start 16/8/13/6; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 56 - bind each model decision to its generation-manifest hash

- **Baseline** (commit 82ecb79, cycle 55; same declining manifest backend, seeds, prompts and probe code):
  - canonical gate: 158 tests OK; aikit check 5/5; policy 8c2c51bc964cbe74120131e0cd3dffeee0e1052c10a5f6869531b37654257c77.
  - standing behavior: 30-seed T1 466 / T2 240 / T3 217; T1 seeds 0-99 1581; holdout 500-599 1581/800/738; fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0.
  - model-seam trace: the decision record keys were `proposed/rule/steps_since_reward/trust_window/noop_guard/distrusted/accepted/reason/skipped`; no generation-manifest hash. The backend held `last_manifest` for T3 seed 15 (`5d06a1dcef060583a71ec82cb2bdab6b91479b7cdb7fa47f5ee150c14298aec5`) but it never reached the log. A checkpoint swap under the same model label was invisible.
  - dead-end audit: excluding dead goal steps from the two-blocker pool improved pin (7,5) 18 -> 16 but regressed a sampled (3,0) config 11 -> 21; unsafe, discarded.
- **Gap**: the generation manifest is the model seam's only exact binding of action to prompt/observation/sampling/checkpoint. Computing it and discarding it means a run log cannot audit the "same model hash/prompts/seeds" claim, and a same-named checkpoint swap leaves no trace.
- **Target delta**: manifest coverage 0/N -> N/N; first digest equals the independently recomputed `manifest_for` hash; checkpoint A vs B changes every digest while actions stay identical; `probe_manifest=False` restores coverage 0 without changing actions; a raising call records `null`.
- **Falsifier**: the digest is absent or wrong; checkpoint swap leaves the digest unchanged; probe-off still emits the key; a raising backend leaks a stale digest; any action/steps/reward/syn/phi moves; standing, trust, escape or cold-start pins move.
- **Change**: agent.py adds `Planner(probe_manifest=True)` and copies `last_manifest.sha256` into `model_decision.model_manifest_sha256` after a successful generate (null on raise; null on skipped decisions when the probe is on); adds `PLANNER_POLICY["model_manifest_probe"] = "on"`. evals/manifest_binding.py adds intact/ablate/swap modes with a declining manifest backend; tests/test_manifest_binding.py covers per-step hashes, checkpoint swap, probe-off, stale-raise, policy and validation. README and ADR-052 record the contract. No new dependencies; no schema change.
- **After** (same backend class, seeds, prompts and probe code):
  - T1 seed 71: 16 steps, 3.0 reward, action hash bafe50ff..., first manifest hash cabec7a8... (A) / 6583aae7... (B); syn 0.03728282024294677 syn_n 0.07725767406794228 phi 0.0, 36 records.
  - T3 seed 15: 13 steps, 1.0 reward, action hash 63c67660..., first manifest hash 5ba4e50c... (A) / 4a410229... (B); syn -0.05791331748493783 syn_n -0.2135530490569846 phi 0.0, 30 records.
  - manifest coverage 1.0 on both; actions, steps, rewards and M/P/S/hub vectors are identical to the probe-off run; standing, T1 0-99, holdout, fixed-rig, trust, escape and cold-start unchanged; 164 tests OK. `policy_digest` 8c2c51bc... -> 136dec8aaa005c1248bd11b144fa0d3b1d627e468d5bdd083fbbbff4d17caa26.
- **Ablation** (same backend, seeds and prompts):
  - `probe_manifest=False`: coverage 0.0 on both cases, the key is absent, and action hashes/vectors/syn/phi are byte-identical (bafe50ff.../63c67660..., 0.03728282.../-0.05791332..., phi 0.0). The binding dies with the cut.
  - checkpoint swap: coverage stays 1.0, actions identical, and every digest moves (T1 cabec7a8... -> 6583aae7...; T3 5ba4e50c... -> 4a410229...). The trace distinguishes the swap that the baseline could not.
  - stale raise: `last_manifest` holds "stale" and `generate` raises; the decision records `null`, so no stale binding leaks.
- **Verdict**: trace-integrity instrumentation. Behavior is unchanged by design; the measured deltas are manifest coverage (0 -> 1.0), checkpoint discrimination (0 -> 1 swap detected) and stale-raise safety (stale -> null). No action or emergence claim.
- **Gates**: unittest 164/164 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_manifest_binding.TestManifestBinding.test_each_decision_binds_its_manifest -v` -> before: TypeError (`probe_manifest` missing) and a baseline probe with no `model_manifest_sha256`; after: OK.
  - `python -m unittest tests.test_manifest_binding -v` -> 6 OK.
  - `python -m unittest discover -s tests -t .` -> 164 OK.
  - `python -m evals.manifest_binding` -> intact coverage 1.0; `--mode ablate` -> coverage 0.0 with identical action hashes; `--mode swap` -> coverage 1.0 with different digests and identical action hashes.
  - `python -m evals.trust` / `--ablate-noop` / `--ablate` -> 16/8/13/6, 36/28/33/26 with 21 calls and 15/7/12/5 skipped, 200/0 unchanged.
  - `python -m evals.escape` -> 19/18 intact, 200/200 ablate and blind; `python -m evals.coldstart --capture` -> 16/8/13/6 with store_reads 1.
  - standing scan -> 466/240/217, T1 seeds 0-99 1581, holdout 1581/800/738, fixed syn 0.05411532 phi 0.0.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 57**: unittest 164 OK; aikit 5/5; manifest intact coverage 1.0 with T1 cabec7a8.../T3 5ba4e50c..., ablate coverage 0.0 with action hashes bafe50ff.../63c67660..., swap digests 6583aae7.../4a410229..., stale raise null; stalled `--ablate-noop` 36/28/33/26 with 21/21/21/21 calls, 1/1/1/1 fallbacks, 15/7/12/5 skipped; `--no-skip` calls 36/28/33/26, fallbacks 16/8/13/6; default wait 16/8/13/6; trust-off 16/8/13/6; both-off 200/0; escape 19/18; standing 466/240/217; T1 seeds 0-99 1581; holdout 500-599 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; policy 136dec8a...; multi pins 9/18/11/13/14; three pins 15/12/10/13/19; exhaustive 3906/3906; cold-start 16/8/13/6; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 57 - BFS-distance dead-pool guard for two-blocker routes

- **Baseline** (commit ef1f75d, cycle 56; same declining backend, seed and prompt code):
  - canonical gate: 164 tests OK; aikit check 5/5; policy 136dec8aaa005c1248bd11b144fa0d3b1d627e468d5bdd083fbbbff4d17caa26.
  - standing behavior: 30-seed T1 466 / T2 240 / T3 217; T1 seeds 0-99 1581; holdout 500-599 1581/800/738; fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0.
  - multi (7,5) with obstacles [6,1],[7,2]: 18 steps, 1.0 reward, action hash de1154e1..., no `dead_pool` probe; syn -0.002387766 syn_n -0.011128706 phi 0.0, 40 records; first prompt hash 22871fdb....
  - dead-end audit: a plain dead-step exclusion reached 16 on (7,5) but regressed a sampled (3,0) config 11 -> 21 because it chose a farther live backup; discarded.
- **Gap**: the local pool enters the dead goal step [7,1] even though the live backup [6,0] is closer to the goal (BFS 8 vs 10), adding two steps to the (7,5) pin. A live-vs-dead BFS-distance comparison can drop the dead step without choosing a farther backup.
- **Target delta**: (7,5) 18 -> 16 with 1.0 reward; action hash changes; `probe.dead_pool` records position [7,0], excluded down [7,1], live 8 / dead 10; all other multi/three pins and blind kills unchanged; `dead_pool_filter=False` restores 18.
- **Falsifier**: (7,5) stays 18; any other pin moves; the blind cut completes; the ablation does not restore the 18-step hash; the 300-config scan regresses; the probe is absent or wrong; standing, trust, escape, cold-start or exhaustive pins move.
- **Change**: agent.py adds a `dead_pool_filter` flag, extends `_step_toward` with an optional probe and a BFS-distance filter for exactly two obstacles, records `probe.dead_pool` when dead goal steps are dropped, and adds `PLANNER_POLICY["dead_pool_filter"] = "2-blockers:live<=dead-bfs"`. evals/dead_pool.py adds intact/ablate modes over the five multi pins; tests/test_dead_pool.py covers the probe, ablation, blind cut, determinism, policy and validation; the (7,5) count/golden and the multi docstring are updated. README and ADR-053 record the contract. No new dependencies; no schema change.
- **After** (same backend class, seed, prompts and probe code):
  - (7,5): 16 steps, 1.0 reward, action hash 1c9552d3..., one `dead_pool` probe at [7,0] excluding down [7,1] with live 8 / dead 10; syn -0.060504864 syn_n -0.258798213 phi 0.0, 36 records; first prompt hash 22871fdb... unchanged.
  - multi (5,0)/(3,6)/(5,6)/(5,7): 9/11/13/14 with 1.0, action hashes 28567d98.../399f17fe.../db4f17e3.../f307bfc3... unchanged; some emit the probe without an action change.
  - three pins/goldens 15/12/10/13/19 and their paths byte-identical; blind (7,5) 200/0. 300-config two-blocker scan: 0 improved, 0 regressed, 0 changed outside the pinned case; standing, T1 0-99, holdout, fixed-rig, trust, escape, cold-start and exhaustive T3 3906/3906 unchanged; 170 tests OK. `policy_digest` 136dec8a... -> d097b97b466264471c140abe3f9a1d116d7bdcda3c9e4a798413ddc38b09ba1e.
- **Ablation** (same backend, seed and prompts):
  - `dead_pool_filter=False`: (7,5) 18 steps, 1.0 reward, action hash de1154e1..., no probe, syn -0.002387766 phi 0.0, 40 records. Exactly the baseline; the two-step gain and the probe die with the cut.
  - memory-blind: (7,5) 200/0 with no completion; the routing gain is not a memory-coupling claim.
- **Verdict**: routing-efficiency win on one two-blocker dead-step probe. The property is the 2-step reduction; the trace gains `dead_pool` (excluded cell and live/dead BFS distances). No emergence claim: the guard is geometry, not episode memory, and is deliberately limited to exactly two blockers to preserve the three-blocker goldens.
- **Gates**: unittest 170/170 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_multi_obstacle.TestMultiObstacle.test_multi_obstacle_recovery -v` -> before: FAIL (18 != 16); after: OK.
  - `python -m unittest tests.test_dead_pool tests.test_multi_obstacle tests.test_multi_goldens -v` -> 10 OK.
  - `python -m unittest discover -s tests -t .` -> 170 OK.
  - `python -m evals.dead_pool` -> (7,5) 16/1.0 with one probe; `--mode ablate` -> 18/1.0 with no probe.
  - 300-config two-blocker scan -> 0 improved, 0 regressed, 0 changed outside the pin.
  - `python -m evals.trust` / `--ablate-noop` / `--ablate` -> 16/8/13/6, 36/28/33/26 with 21 calls, 200/0 unchanged.
  - `python -m evals.escape` -> 19/18 intact, 200/200 ablate and blind; `python -m evals.coldstart --capture` -> 16/8/13/6.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 58**: unittest 170 OK; aikit 5/5; multi (7,5) 16/1.0 action 1c9552d3... with probe [7,0]/down [7,1]/live 8/dead 10; dead-pool ablate 18/1.0 action de1154e1...; other multi 9/11/13/14; three 15/12/10/13/19; standing 466/240/217; T1 seeds 0-99 1581; holdout 500-599 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; policy d097b97b...; manifest intact coverage 1.0, ablate 0.0; trust 16/8/13/6, ablate-noop 36/28/33/26 with 21 calls; both-off 200/0; escape 19/18; exhaustive 3906/3906; cold-start 16/8/13/6; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 58 - terminal telemetry head/count anchor

- **Baseline** (commit 82dc85d, cycle 57; same log builder and verifier):
  - canonical gate: 170 tests OK; aikit check 5/5; policy d097b97b466264471c140abe3f9a1d116d7bdcda3c9e4a798413ddc38b09ba1e.
  - standing behavior: 30-seed T1 466 / T2 240 / T3 217; T1 seeds 0-99 1581; holdout 500-599 1581/800/738; fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0.
  - chain trace: a 5-record log verified `ok=true`, records 5, head e735d8e0...; deleting the last two lines still verified `ok=true`, records 3, head 4a2b4b01...; `Telemetry` had no `write_anchor`.
- **Gap**: `verify_chain` validates internal links only. A truncated tail leaves a valid prefix, so trailing actions and the verdict can be hidden while the log reads back as valid. There is no terminal head/count witness.
- **Target delta**: intact 8-record log with an anchor -> ok 8/8; truncate to 6 -> ok false with `truncated-tail:6<8`; the same truncation without the anchor -> ok true (control); missing anchor -> `missing-anchor`; edited anchor -> `anchor-mismatch`; no behavior or standing change.
- **Falsifier**: the truncated anchored log still returns ok; the intact anchored log fails; the anchor-off control detects the cut; missing/mismatched anchors pass; any standing or behavior pin moves.
- **Change**: telemetry/log.py adds `write_anchor` (atomic temp+fsync+replace sidecar `path + ".anchor"`), `read_anchor`, an optional `anchor_path` argument to `verify_chain`, and `Telemetry.write_anchor()`. `evals/chain_anchor.py` adds intact/truncated/unanchored modes; `tests/test_chain_anchor.py` covers intact, detected truncation, anchor-off exposure, missing/mismatch, atomic determinism and helper roundtrip. README and ADR-054 record the contract. No new dependencies; no schema change; the planner policy digest is unchanged.
- **After** (same log builder and verifier):
  - intact: 8 records before and after, ok true, no findings.
  - truncated: 8 -> 6 records, ok false, findings `["truncated-tail:6<8"]`, verified head 52cd39d9... vs anchor head 36a364f7....
  - unanchored control: 8 -> 6 records, ok true, no findings.
  - missing anchor: ok false, `missing-anchor`; mismatched anchor: ok false, `anchor-mismatch`; the sidecar write leaves no `.tmp` and is deterministic across rewrites.
  - behavior, standing 466/240/217, T1 0-99 1581, holdout 1581/800/738, ranges 683/732/800/1646, fixed syn 0.05411532 phi 0.0, trust 16/8/13/6, escape 19/18, dead-pool (7,5) 16 and cold-start 16/8/13/6 are unchanged; 177 tests OK.
- **Ablation** (same log builder):
  - anchor off (`verify_chain(path)`): the 8 -> 6 truncation returns ok true, records 6, no findings. The detection and the anchor evidence die with the cut; this is the documented residual exposure.
  - missing/mismatched anchor: the anchored verifier fails separately, so a missing or edited witness is not silently accepted.
- **Verdict**: trace-integrity instrumentation. Behavior is unchanged by design; the measured deltas are truncation detection (0 -> 1 class), records covered (3/5 unanchored -> 6/6 anchored verified), and the separate missing/mismatch findings. No action or emergence claim.
- **Gates**: unittest 177/177 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - baseline probe -> full 5 records ok; truncated 3 records ok; `has_write_anchor` false.
  - `python -m unittest tests.test_chain_anchor -v` -> before: ImportError (`write_anchor`); after: 7 OK.
  - `python -m unittest discover -s tests -t .` -> 177 OK.
  - `python -m evals.chain_anchor` -> intact 8/8 ok; truncated 8->6 `truncated-tail:6<8`; unanchored 8->6 ok.
  - `python -m evals.trust` / `--ablate-noop` -> 16/8/13/6 and 36/28/33/26 with 21 calls; `python -m evals.escape` -> 19/18 intact, 200/200 ablate/blind; `python -m evals.coldstart --capture` -> 16/8/13/6.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 59**: unittest 177 OK; aikit 5/5; chain intact 8/8 ok, truncated 8->6 `truncated-tail:6<8`, unanchored 8->6 ok, missing/mismatch fail; multi (7,5) 16/1.0 with probe; dead-pool ablate 18; other multi 9/11/13/14; three 15/12/10/13/19; standing 466/240/217; T1 seeds 0-99 1581; holdout 500-599 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; policy d097b97b...; manifest intact coverage 1.0, ablate 0.0; trust 16/8/13/6, ablate-noop 36/28/33/26 with 21 calls; both-off 200/0; escape 19/18; exhaustive 3906/3906; cold-start 16/8/13/6; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 59 - full audit of the remaining two-blocker detours, zero verified safe improvements (STOP)

- **Baseline** (commit eace8a7, cycle 58; no code change in this cycle):
  - canonical gate: 177 tests OK; aikit check 5/5; policy d097b97b466264471c140abe3f9a1d116d7bdcda3c9e4a798413ddc38b09ba1e.
  - standing behavior: 30-seed T1 466 / T2 240 / T3 217; T1 seeds 0-99 1581; holdout 500-599 1581/800/738; fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0.
  - multi intact 9/16/11/13/14 with 1.0; blind 9/200/200/200/200 (the four killing configs truncate at 0.0). three intact 15/12/10/13/19 with 1.0; blind 200/200/10/200/200.
  - chain anchor: intact 8/8 ok; truncated 8->6 `truncated-tail:6<8`; unanchored 8->6 ok.
- **Gap**: the remaining two-blocker detours are (3,6) 11 vs BFS 9, (5,6) 13 vs 11, (5,7) 14 vs 12 (and (7,5) is 16 vs BFS 12 after cycle 57). A BFS-distance-first ordering of the live candidates is the obvious candidate.
- **Target delta**: none qualifies. Candidate results, one line each:
  - BFS-distance live ordering (exactly 2 obstacles): intact becomes 9/12/9/11/12 (BFS-optimal), but the memory-blind cut also becomes 9/12/9/11/12; the four multi blind kills (7,5),(3,6),(5,6),(5,7) die, `test_blind_kills_multi_recovery` would fail, and the property no longer dies with the memory cut. Rejected; a 300-config scan showed 1 improved (3,0 11->9), 0 regressed, 0 other changes, but the coupling loss blocks it.
  - Extending the dead-pool guard to 3 blockers: counts stay 15/12/10/13/19 but the (6,7) golden path changes at the same 15 steps; path drift with no count gain. Rejected.
  - Global BFS policy (not just the first move): same blind-coupling loss as the live ordering; rejected.
  - 3-blocker BFS/order changes: no count target that survives the memory ablation; would only rewrite goldens. Rejected.
  - `mean_conf` consumer: still no failing eval; inventing a confidence policy is not a measured gap.
  - removing/batching per-step memory-store writes: no behavior gap; M vector and fixed-rig trace would move without a failing eval.
  - prompt visits cap: speculative prompt change with no behavior target.
  - llama.cpp retry/backoff: no local server or weights; untestable in this battery.
  - telemetry readers unlocked / anchor rewriteable with the log: documented boundaries (cycles 53/58); no new measured gap.
- **Change**: none. No code, no harness, no ADR (audit result, not a design decision). The BFS-live prototype was runtime-only and was not committed.
- **After**: identical battery re-verified: 177 tests OK; aikit 5/5; multi 9/16/11/13/14 with blind 9/200/200/200/200; three 15/12/10/13/19 with blind 200/200/10/200/200; standing 466/240/217; holdout 1581/800/738; fixed syn 0.05411532 phi 0.0; policy d097b97b unchanged. No deltas, variance not applicable.
- **Ablation**: none (no integration claim).
- **Verdict**: full cycle with zero verified safe improvements. Stopping per the goal rule (allowed stop: zero-findings cycle). STOP.
- **Gates**: unittest 177/177 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest discover -s tests -t .` -> 177 OK.
  - `python aikit.py check brain` -> 5/5.
  - audit script -> multi intact 9/16/11/13/14, blind 9/200/200/200/200; three 15/12/10/13/19, blind 200/200/10/200/200; standing 466/240/217; policy d097b97b.
  - runtime BFS-live prototype -> intact 9/12/9/11/12, blind 9/12/9/11/12; 300-config scan 1 improved, 0 regressed.
  - `python -m evals.chain_anchor` -> intact 8/8, truncated 8->6 detected, unanchored 8->6 ok.
- **Pinned regression baselines carried (no new pins)**: unittest 177 OK; aikit 5/5; chain intact 8/8, truncated 8->6 `truncated-tail:6<8`, unanchored 8->6 ok; multi 9/16/11/13/14 with blind 9/200/200/200/200; three 15/12/10/13/19 with blind 200/200/10/200/200; standing 466/240/217; T1 seeds 0-99 1581; holdout 500-599 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; policy d097b97b...; manifest coverage 1.0/0.0; trust 16/8/13/6, ablate-noop 36/28/33/26 with 21 calls; both-off 200/0; escape 19/18; exhaustive 3906/3906; cold-start 16/8/13/6; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 60 - tail-read telemetry head lookup (assay transfer)

- **Baseline** (commit 09d1755, cycle 59; same telemetry format):
  - canonical gate: 177 tests OK; aikit check 5/5; policy d097b97b466264471c140abe3f9a1d116d7bdcda3c9e4a798413ddc38b09ba1e.
  - `Telemetry._head_digest()` on a fresh instance read every line of the existing log: 100k records (1.29 MB) 191.3 ms, 500k (6.89 MB) 943.5 ms, 1M (13.89 MB) 1985.8 ms; the 200k failing-first fixture took 381.8 ms.
  - Head values and append bytes were already correct; the cost was only the full-file scan.
- **Gap**: when a fresh writer resumes an existing JSONL log, `_head_digest` walks the whole file to find the last `digest`. The cost grows linearly with history and is paid on every new `Telemetry` instance before the first append.
- **Target delta**: 200k-record head lookup < 120 ms; exact equality for a normal chain, blank tails, and legacy tails with/without a terminator; a fresh append still verifies as one chain; no schema, policy or record-byte change.
- **Falsifier**: the 200k lookup stays above 120 ms; any head value differs; a legacy tail hashes differently; a fresh append breaks the chain; the 177-test pin set regresses.
- **Change**: `telemetry/log.py` gains `_last_nonempty_line(path, chunk_size=65536)`, adapted from `assay/storage.py:27` (AegeanWorks/assay, AL-1.1): a bounded binary tail scan. `_head_digest` uses it, parses only the final line, and reconstructs the exact text-mode terminator only for a legacy tail so the `LEGACY:<sha256>` anchor is byte-identical. No new dependencies; no schema or policy change.
- **After** (same fixtures and chain):
  - failing-first 200k fixture: 381.8 ms -> 0.764 ms min (8.268 ms max) with the same `"a"*64` head.
  - benchmark: 100k 191.3 -> 0.979 ms; 500k 943.5 -> 0.812 ms; 1M 1985.8 -> 0.820 ms (min; max 14.467/9.638/9.580 ms).
  - normal/blank-tail/legacy head equivalence passes; a fresh append after 1,000 records yields `verify_chain` ok with 1,001 records; 179 tests OK; aikit 5/5; policy unchanged.
- **Ablation**: the pre-change full-scan path is the baseline (the same tests fail the 120 ms bound); no behavior or emergence claim. Removal of the tail helper restores the old scan.
- **Verdict**: performance-only transfer from assay. Behavior, trace bytes and chain semantics are unchanged; the measured delta is head-lookup cost. No integration or emergence claim.
- **Gates**: unittest 179/179 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - baseline benchmark -> 100k 191.3 ms, 500k 943.5 ms, 1M 1985.8 ms.
  - `python -m unittest tests.test_telemetry.TestTelemetry.test_head_digest_reads_tail_not_whole_file -v` -> before: FAIL (381.8 ms >= 120 ms); after: OK.
  - `python -m unittest tests.test_telemetry -v` -> 5 OK.
  - `python -m unittest discover -s tests -t .` -> 179 OK.
  - `python aikit.py check brain` -> 5/5.
  - 1,000-record fresh-append chain check -> `ok=true`, 1,001 records.
- **Pinned regression baselines for cycle 61**: unittest 179 OK; aikit 5/5; 200k head lookup < 120 ms (after 0.764 ms, before 381.8 ms); head/legacy equivalence; 1,001-record chain ok; standing 466/240/217; T1 seeds 0-99 1581; holdout 500-599 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; policy d097b97b...; multi 9/16/11/13/14 with blind 9/200/200/200/200; three 15/12/10/13/19 with blind 200/200/10/200/200; trust 16/8/13/6; escape 19/18; cold-start 16/8/13/6; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 61 - append-only anchor journal (assay transfer)

- **Baseline** (commit 8ae9750, cycle 60; same telemetry format):
  - canonical gate: 179 tests OK; aikit check 5/5; policy d097b97b466264471c140abe3f9a1d116d7bdcda3c9e4a798413ddc38b09ba1e.
  - the only terminal witness was one mutable `.anchor` sidecar (`{head, records}`); there was no journal of previous heads, so deleting or rewinding the sidecar left no internal evidence.
- **Gap**: a single anchor cannot show that an earlier run's head existed. A JSONL journal in which each anchor commits to the previous anchor hash makes a deleted/rewound middle anchor and a rewound seq detectable, and lets a later anchor verify an earlier log head.
- **Target delta**: two anchors form a verified chain (`prev` links, 2 anchors); an intact 16-record log verifies against the latest anchor; truncating it to 13 reports `truncated-tail:13<16`; deleting the first anchor is detected by the second `prev`; editing a head is detected by its hash; a backwards seq is refused; the single-anchor API remains valid.
- **Falsifier**: the journal accepts a broken prev/hash/seq; the intact log fails; truncation is not reported; the single-anchor path changes; any standing or policy pin moves.
- **Change**: telemetry/log.py adds `ANCHOR_JOURNAL_SCHEMA`, `append_anchor(path, head, records, journal_path=None, created_at=None)`, `verify_anchor_journal(journal_path)`, `Telemetry.write_anchor_journal()`, and `verify_chain(path, journal_path=...)`. Each record carries `schema/ledger/seq/head/created_at/prev/hash`; `hash` is SHA-256 over the canonical payload; `prev` links to the previous anchor or `GENESIS`; seq is the log record count and may not move backwards; validation names schema/field/head/prev/hash/seq defects; appends fsync the line and directory. `evals/anchor_journal.py` adds intact/truncated modes; `tests/test_anchor_journal.py` covers chaining, truncation, deleted anchor, tampered head, backwards seq, missing journal and the unchanged single-anchor path. README and ADR-055 record the contract. No new dependencies; the log schema is unchanged.
- **After** (same log builder and timestamps):
  - intact: 16 records, 2 anchors at seq 11 and 16, journal `ok=true`, `verify_chain` `ok=true` with 16/16 records.
  - truncated: 16 -> 13 records, journal still 2 anchors, latest seq 16, `verify_chain` `ok=false`, findings `["truncated-tail:13<16"]`.
  - deleted first anchor: journal `ok=false` with a `prev` error; tampered head: `hash` error; backwards seq: `ValueError` on append; missing journal: `missing-journal`; single anchor: 4-record log still `ok=true`.
  - behavior, standing 466/240/217, T1 0-99 1581, holdout 1581/800/738, fixed-rig syn 0.05411532 phi 0.0, trust 16/8/13/6, escape 19/18, dead-pool (7,5) 16, cold-start 16/8/13/6 and the 200k tail-read bound are unchanged; 186 tests OK; policy unchanged.
- **Ablation** (same log builder):
  - without the journal, the 16 -> 13 truncation returns `ok=true` (a valid prefix); with the journal it is `truncated-tail:13<16`. The journal and its finding die with the cut.
  - deleting tail anchors yields a shorter but internally valid journal; the latest anchor must be known externally to detect that. This is the recorded boundary, not a solved case.
- **Verdict**: trace-integrity extension. Behavior is unchanged by design; the measured deltas are anchor-chain integrity (2 anchors, seq 11/16), truncated-log detection (13<16), and named deleted/tampered anchor findings. No action or emergence claim.
- **Gates**: unittest 186/186 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_anchor_journal.TestAnchorJournal.test_journal_chains_two_anchors -v` -> before: ImportError (`append_anchor`); after: OK.
  - `python -m unittest tests.test_anchor_journal -v` -> 7 OK.
  - `python -m evals.anchor_journal` -> intact 16/16, 2 anchors, latest seq 16, ok; truncated 13/16, `truncated-tail:13<16`.
  - `python -m unittest discover -s tests -t .` -> 186 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 62**: unittest 186 OK; aikit 5/5; anchor journal 2 anchors seq 11/16; intact 16/16 ok; truncated 13/16 `truncated-tail:13<16`; deleted first anchor prev error; tampered head hash error; backwards seq ValueError; missing journal; single anchor 4/4 ok; 200k head lookup < 120 ms (0.764 ms); standing 466/240/217; T1 seeds 0-99 1581; holdout 500-599 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; policy d097b97b...; multi 9/16/11/13/14 with blind 9/200/200/200/200; three 15/12/10/13/19 with blind 200/200/10/200/200; trust 16/8/13/6; escape 19/18; cold-start 16/8/13/6; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 62 - optional HMAC-SHA256 telemetry signing (assay transfer)

- **Baseline** (commit 31c394d, cycle 61; same record format):
  - canonical gate: 186 tests OK; aikit check 5/5; policy d097b97b466264471c140abe3f9a1d116d7bdcda3c9e4a798413ddc38b09ba1e.
  - the chain was unkeyed. An attacker who recomputes every `digest`/`prev` and rewrites the anchor/journal can produce a self-consistent log; there was no verifier-held secret.
- **Gap**: hash chains prove internal consistency, not authorship. `assay/ledger.py:29 record_mac` signs the canonical payload with an HMAC key; without the key, an edited record cannot be re-signed.
- **Target delta**: a keyed 8-record log carries 8 MACs and verifies with the key; the wrong key reports `bad-mac:0`; a stripped MAC reports `missing-mac:0`; a payload edit with a recomputed digest reports `bad-mac`; an unkeyed log stays 0-MAC and verifies unkeyed, while a keyed verifier reports missing MACs. No schema/policy/standing change.
- **Falsifier**: the keyed log fails with the correct key; a wrong key or stripped MAC passes; a recomputed-digest tamper passes; an unkeyed log changes bytes or fails unkeyed verification; any standing/policy pin moves.
- **Change**: telemetry/log.py adds an optional `hmac_key` to `Telemetry`, `_mac_of`, `mac` emission after the digest, `_digest_of` excluding `mac`, and `hmac_key` verification in `verify_chain` with `missing-mac`/`bad-mac` findings. Keys are non-empty bytes or `None`; unkeyed writes remain byte-identical. `tests/test_telemetry_mac.py` covers correct/wrong/missing/tampered keys, unkeyed parity and key validation; `evals/telemetry_mac.py` measures all six states. README and ADR-056 record the contract. No new dependencies beyond stdlib `hmac`.
- **After** (same log builder and test keys):
  - keyed: 8 records, 8 MACs, correct-key `ok=true`; unkeyed verifier also `ok=true` (chain-only).
  - wrong key: `ok=false`, `bad-mac:0`; missing MAC: `ok=false`, `missing-mac:0`.
  - tampered payload with recomputed digest: `ok=false`, `bad-mac:0` plus downstream `broken-link` findings.
  - unkeyed: 0 MACs, `ok=true` unkeyed; with a key, `ok=false` with 8 `missing-mac` findings.
  - behavior, standing 466/240/217, T1 0-99 1581, holdout 1581/800/738, fixed-rig syn 0.05411532 phi 0.0, trust 16/8/13/6, escape 19/18, dead-pool (7,5) 16, cold-start 16/8/13/6, anchor journal and 200k tail-read bound unchanged; 192 tests OK; policy unchanged.
- **Ablation** (same log builder):
  - key off / unkeyed verifier: the chain still passes, but the keyed forgery resistance and the MAC findings are absent. The property dies with the key.
  - keyed verifier on an unkeyed log: 8 `missing-mac` findings, so a keyed run cannot silently accept an unsigned log.
- **Verdict**: trace-integrity extension. Behavior is unchanged by design; the measured deltas are 8/8 MAC coverage, wrong-key/missing/tamper findings, and unkeyed parity. No action or emergence claim.
- **Gates**: unittest 192/192 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_telemetry_mac.TestTelemetryMac.test_keyed_records_verify_with_key -v` -> before: TypeError (`hmac_key` missing); after: OK.
  - `python -m unittest tests.test_telemetry_mac -v` -> 6 OK.
  - `python -m evals.telemetry_mac` -> keyed 8/8 MAC ok; wrong-key bad-mac:0; missing-mac:0; tampered bad-mac:0; unkeyed 0 MAC ok; unkeyed-keyed 8 missing-mac.
  - `python -m unittest discover -s tests -t .` -> 192 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 63**: unittest 192 OK; aikit 5/5; keyed 8/8 MACs ok; wrong key `bad-mac:0`; missing MAC `missing-mac:0`; tampered+recomputed digest `bad-mac:0`; unkeyed 0 MAC ok; unkeyed-keyed 8 missing-mac; anchor journal 2 anchors seq 11/16, truncated 13/16; single anchor 4/4; 200k head lookup < 120 ms (0.764 ms); standing 466/240/217; T1 seeds 0-99 1581; holdout 500-599 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; policy d097b97b...; multi 9/16/11/13/14 with blind 9/200/200/200/200; three 15/12/10/13/19 with blind 200/200/10/200/200; trust 16/8/13/6; escape 19/18; cold-start 16/8/13/6; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 63 - token-budgeted model prompts (research-engine transfer)

- **Baseline** (commit e73deff, cycle 62; same prompt builder and T3:15):
  - canonical gate: 192 tests OK; aikit check 5/5; policy d097b97b466264471c140abe3f9a1d116d7bdcda3c9e4a798413ddc38b09ba1e.
  - `build_prompt` had no cap; the T3:15 prompt was 63 estimated tokens with 0 omitted, and the synthetic 64-visit observation was 228 estimated tokens.
- **Gap**: prompt size had no budget or readout. A long visits line could grow the prompt without a declared cap, and `LlamaCppBackend` could not enforce a context limit or report omissions.
- **Target delta**: at `max_tokens=60`, the synthetic prompt is <=60 tokens with 1 omitted line, target/obstacles kept and visits dropped; T3:15 prompt max 63 -> 52 tokens with 13 omitted visits; rule actions, steps, reward and success unchanged; default `None` remains byte-identical; the generation-manifest hash changes only because the prompt changed.
- **Falsifier**: the budgeted prompt exceeds 60; target/obstacles are dropped; visits survive; actions/steps/reward move; default prompt bytes change; any standing/policy pin moves.
- **Change**: models/llamacpp.py adds `estimate_tokens`, `pack`, `_prompt_lines`, `build_prompt(observation, max_tokens=None)`, `prompt_stats`; the anchor line carries task/position/legal/target/items/obstacles/cue, the visits line is last, and `OMITTED:n` names dropped lines. `LlamaCppBackend` gains `prompt_budget` and `last_prompt_stats`; `generate` renders the capped prompt and the manifest binds it. Tests cover uncapped exactness, token math, pack first-line retention, 120/60 budgets, backend prompt cap and invalid values; the eval runs uncapped/budgeted T3:15 with a declining capture backend. README and ADR-057 record the contract. No new dependencies; no policy change.
- **After** (same observation, backend, seed and prompts):
  - synthetic 64 visits: 228 tokens uncapped -> 52 tokens at `max_tokens=60`, 1 omitted, target/obstacles present, visits absent.
  - T3:15: 13 steps, 1.0 reward, success, actions identical to rule-only in both modes; prompt max 63 -> 52 tokens, 13 omitted visits, first manifest hash 714c1368... -> a5307733....
  - default `max_tokens=None` returns the exact original prompt; `prompt_stats` omitted 0; 200 tests OK; policy unchanged.
- **Ablation** (same observation and T3:15):
  - `max_tokens=None`: the 228-token synthetic prompt and 63-token T3 prompt return with 0 omitted; actions/steps/rewards stay identical. The budget and omission readout die with the cut.
  - The current line layout only omits visits; the anchor (including target/obstacles) is always kept. A budget below the anchor is a floor, not a hard cap.
- **Verdict**: model-seam cost/readout improvement. Behavior is unchanged for the rule path; the measured deltas are prompt tokens (228 -> 52 synthetic; 63 -> 52 T3:15), omitted lines (0 -> 1/13), and manifest hash binding. No action or emergence claim.
- **Gates**: unittest 200/200 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_prompt_budget.TestPromptBudget.test_budget_caps_trailing_visits -v` -> before: ImportError (`estimate_tokens`); after: OK.
  - `python -m unittest tests.test_prompt_budget -v` -> 8 OK.
  - `python -m evals.prompt_budget` -> uncapped 63/0, budgeted 52/13, actions match rule; synthetic 228 -> 52 with target/obstacles kept.
  - `python -m unittest discover -s tests -t .` -> 200 OK.
  - `python aikit.py check brain` -> 5/5 after fixing the ADR numbering gap (HMAC was ADR-056, prompt budget ADR-057).
- **Pinned regression baselines for cycle 64**: unittest 200 OK; aikit 5/5; prompt uncapped T3 63 tokens/0 omitted, budgeted 52/13; synthetic 228 -> 52 with target/obstacles; manifest first 714c1368... -> a5307733...; keyed 8/8 MACs; wrong/missing/tampered findings; anchor journal 2 anchors seq 11/16, truncated 13/16; single anchor 4/4; 200k head lookup < 120 ms (0.764 ms); standing 466/240/217; T1 seeds 0-99 1581; holdout 500-599 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; policy d097b97b...; multi 9/16/11/13/14 with blind 9/200/200/200/200; three 15/12/10/13/19 with blind 200/200/10/200/200; trust 16/8/13/6; escape 19/18; cold-start 16/8/13/6; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 64 - Merkle batch anchors and inclusion proofs (merklock transfer)

- **Baseline** (commit cfd8816, cycle 63; same 20-record log):
  - canonical gate: 200 tests OK; aikit check 5/5; policy d097b97b466264471c140abe3f9a1d116d7bdcda3c9e4a798413ddc38b09ba1e.
  - the linear chain and anchor journal proved order/continuity, but there was no compact batch commitment or detached inclusion proof for one record.
- **Gap**: verifying that a specific record belongs to a batch required replaying the chain. A Merkle root over the batch digests plus a sibling path gives O(log n) membership without the rest of the batch.
- **Target delta**: a 20-record log anchored over its last 8 records has start 12 / end 20 / count 8; the intact root verifies; record 15 yields a 3-sibling proof that verifies; truncation, a changed root, a changed batch digest, a tampered proof and a missing anchor are named; behavior/standing unchanged.
- **Falsifier**: the root/proof does not verify; a truncation/tamper passes; the proof accepts a wrong leaf; the single anchor/journal, prompt budget, telemetry chain or standing pins move.
- **Change**: telemetry/merkle.py adds domain-separated `pack`/`digest`, `merkle_root`, `merkle_proof`, `merkle_verify`, `write_merkle_anchor`, `verify_merkle_anchor`, `merkle_proof_for_record` and `verify_merkle_proof`; `Telemetry.write_merkle_anchor` writes the `.merkle` sidecar atomically. Leaves are existing record digests; odd nodes are promoted, empty trees have a defined root, and batch verification is independent of the log verifier (no import cycle). tests/test_merkle.py covers pure trees, odd/empty cases, batch anchor, proof, truncation, tampered root/digest/proof, missing anchor and atomic writes; evals/merkle_anchor.py measures intact/truncated/tampered/proof/missing. README and ADR-058 record the contract. No new dependencies; the log format is unchanged.
- **After** (same log and anchor settings):
  - intact: 20 records; batch start 12/end 20/count 8; anchor `ok=true`; record 15 proof 3 siblings `ok=true`.
  - truncated to 15: `ok=false`, `truncated-batch:20>15`; proof cannot be built.
  - tampered root: `ok=false`, `root-mismatch`; edited batch digest: `ok=false`, `root-mismatch`; proof-tampered: proof verify false; missing anchor: `missing-anchor`.
  - behavior, standing 466/240/217, T1 0-99 1581, holdout 1581/800/738, fixed-rig syn 0.05411532 phi 0.0, trust 16/8/13/6, escape 19/18, dead-pool (7,5) 16, cold-start 16/8/13/6, keyed telemetry, prompt budget and the 200k tail-read bound are unchanged; 211 tests OK; policy unchanged.
- **Ablation** (same log):
  - without the `.merkle` sidecar, verification reports `missing-anchor`; with the sidecar but a tampered root/digest/proof, verification fails. The batch-membership property and its findings die with the root/proof.
  - the root is a separate witness and can be rewritten with the log; the proof says membership in the committed batch, not global order/authorship. `verify_chain` remains the order/authorship check.
- **Verdict**: trace-integrity extension. Behavior is unchanged by design; the measured deltas are the 8-record batch root, the 3-sibling proof, and named truncation/tamper/missing findings. No action or emergence claim.
- **Gates**: unittest 211/211 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_merkle.TestMerkleTree.test_root_and_proof_roundtrip -v` -> before: ModuleNotFoundError (`telemetry.merkle`); after: OK.
  - `python -m unittest tests.test_merkle -v` -> 11 OK.
  - `python -m evals.merkle_anchor` -> intact 20/12-20/8, proof 3 siblings; truncated/tampered/missing detected.
  - `python -m unittest discover -s tests -t .` -> 211 OK.
  - `python aikit.py check brain` -> 5/5 after removing the log↔merkle import cycle.
- **Pinned regression baselines for cycle 65**: unittest 211 OK; aikit 5/5; Merkle batch 12-20/count 8 root/proof 3 siblings; truncated `truncated-batch:20>15`; tampered root/digest/proof/missing detected; prompt T3 63->52/13; synthetic 228->52; keyed 8/8 MACs; anchor journal 2 anchors seq 11/16; single anchor 4/4; 200k head lookup < 120 ms (0.764 ms); standing 466/240/217; T1 seeds 0-99 1581; holdout 500-599 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; policy d097b97b...; multi 9/16/11/13/14 with blind 9/200/200/200/200; three 15/12/10/13/19 with blind 200/200/10/200/200; trust 16/8/13/6; escape 19/18; cold-start 16/8/13/6; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 65 - opt-in execution budgets (neurocore transfer)

- **Baseline** (commit 0d09d42, cycle 64; same T3:15 and budgets absent):
  - canonical gate: 211 tests OK; aikit check 5/5; policy d097b97b466264471c140abe3f9a1d116d7bdcda3c9e4a798413ddc38b09ba1e.
  - `Agent.run` had only `max_steps`; `SelfModel` recorded cost after the fact; no shared step/LLM/token/time allowance, pressure snapshot or pre-action stop.
- **Gap**: a run could not be bounded across dimensions or stopped before the next action/call with a named limit and usage. `neurocore/core/execution_budget.py:51` provides the missing pattern.
- **Target delta**: a generous budget keeps T3:15 at 13 steps / 1.0 with actions identical to rule-only; a 3-step budget stops after 3 actions with `steps` used 4/3; a 2-call budget stops after 2 backend calls with `llm_calls` used 3/2; an 8-token budget stops after 2 calls with `tokens` used 10/8; a zero-second budget stops before the first action. `budget=None` remains a no-op.
- **Falsifier**: a tight budget lets the next action/call through; the error does not name the dimension/limit/usage; a generous budget changes actions; no-budget runs change; any standing/policy pin moves.
- **Change**: add `budget.py` with `DEFAULT_LIMITS`, `BudgetExceeded`, `ExecutionBudget` (remaining/spend/check_time/pressure/snapshot), a ContextVar, `use_budget`, `spend`, `push_budget`/`pop_budget` and `budget_from_limits`. `Agent.run(max_steps, budget=None)` installs it; `_run_loop` spends a step before each action; `Planner` spends an LLM call before `backend.generate` and prompt tokens from `last_prompt_stats`, re-raising `BudgetExceeded` outside the fallback catch. `run_task`/`run_task_logged` accept `budget`. Tests cover direct spend/pressure/limits, context scope, generous parity, step/LLM/token/time exhaustion and invalid values; `evals/execution_budget.py` measures all five modes. README and ADR-059 record the contract. No new dependencies; no policy change.
- **After** (same T3:15 and backends):
  - generous: 13 steps / 1.0 reward, actions match rule-only, steps used 13, pressure 0.065.
  - step cap 3: `BudgetExceeded(steps, 3, 4)`, 3 logged actions, pressure 1.0.
  - LLM cap 2: `BudgetExceeded(llm_calls, 2, 3)`, 2 backend calls, 2 logged steps.
  - token cap 8: `BudgetExceeded(tokens, 8, 10)`, 2 backend calls, 1 logged step.
  - time cap 0: `BudgetExceeded(seconds, 0, elapsed)` before the first action.
  - no-budget/standing behavior, T1 0-99, holdout, fixed-rig, trust, escape, cold-start, telemetry, prompt and Merkle pins unchanged; 221 tests OK; policy unchanged.
- **Ablation** (same T3:15):
  - `budget=None`: the 13-step/1.0 rule run returns with no spend accounting; the tight caps disappear. The runtime budget property dies with the cut.
  - over-limit spending is counted (`used` 4/3, 3/2, 10/8), matching the neurocore increment-then-raise pattern.
- **Verdict**: runtime cost-control extension. A generous budget is behavior-identical; tight budgets stop before the next action/call and name the dimension, limit and usage. No emergence claim.
- **Gates**: unittest 221/221 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_budget.TestExecutionBudget.test_step_limit_raises -v` -> before: ModuleNotFoundError (`budget`); after: OK.
  - `python -m unittest tests.test_budget -v` -> 10 OK.
  - `python -m evals.execution_budget` -> generous 13/1.0/actions match; step 4/3; LLM 3/2; token 10/8; time 0.
  - `python -m unittest discover -s tests -t .` -> 221 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 66**: unittest 221 OK; aikit 5/5; generous budget T3 13/1.0/actions match, steps 13, pressure 0.065; step cap 3 -> BudgetExceeded(steps,3,4) with 3 actions; LLM cap 2 -> (llm_calls,2,3) 2 calls; token cap 8 -> (tokens,8,10) 2 calls; time cap 0 -> seconds; Merkle batch 12-20/count 8 proof 3 siblings; prompt 63->52/13; synthetic 228->52; keyed 8/8 MACs; anchor journal 2 seq 11/16; single anchor 4/4; 200k head lookup <120 ms (0.764); standing 466/240/217; T1 0-99 1581; holdout 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; policy d097b97b...; multi 9/16/11/13/14 blind 9/200/200/200/200; three 15/12/10/13/19 blind 200/200/10/200/200; trust 16/8/13/6; escape 19/18; cold-start 16/8/13/6; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 66 - canonical episode identity and resume policy (neurocore transfer)

- **Baseline** (commit 100a40b, cycle 65; same T3:15/65 and logged runs):
  - canonical gate: 221 tests OK; aikit check 5/5; policy d097b97b466264471c140abe3f9a1d116d7bdcda3c9e4a798413ddc38b09ba1e.
  - logged headers had no episode digest, and there was no declared rule for resuming a stored episode after the task/seed/config changed.
- **Gap**: a rerun could not be compared with a stored episode from the log, and changed targets/configs had no `resume`/`new`/`ask` decision or pause guard.
- **Target delta**: same task/seed/config -> same digest and `resume`; changed seed/target/config -> different digest and `new`; volatile fields ignored; missing digest -> `ask`; policy `any` -> `resume`; logged header `episode_sha256` equals the independent digest; actions/steps/rewards unchanged.
- **Falsifier**: same episode differs; changed target/seed/config does not; volatile keys change the digest; a missing digest resumes; the header digest disagrees; any standing/policy pin moves.
- **Change**: identity.py adds `VOLATILE_KEYS`, `canonical_projection`, `digest_projection`, `input_digest`, `normalise_policy`, `resume_decision`, `resume_guard` and `prepare_resume`; `run_task_logged` computes the digest from the reset initial state/config and writes `episode_sha256` into the header; `Telemetry.write_header` accepts the additive field. tests/test_identity.py covers volatile exclusion, changed target/seed/config, the decision matrix, pause/allowed guards and header equality; evals/resume_identity.py measures same/changed/volatile/legacy/policy cases plus header traces. README and ADR-060 record the contract. No new dependencies; no schema bump.
- **After** (same T3:15/65 and logged runs):
  - same T3:15 reruns: identical `episode_sha256`, 13 steps each, actions identical; T3:65: different digest, 6 steps; changed target: different digest, `new`.
  - volatile `ts`/`created_at`/`session_id`: same digest, `resume`; absent digest: `ask`; policy `any` on a changed episode: `resume`.
  - logged header digest equals the independently computed `input_digest`; `prepare_resume` pauses a refused candidate and allows a matching one.
  - behavior, standing 466/240/217, T1 0-99 1581, holdout 1581/800/738, fixed-rig syn 0.05411532 phi 0.0, trust 16/8/13/6, escape 19/18, dead-pool (7,5) 16, cold-start 16/8/13/6, keyed telemetry, prompt budget, Merkle, execution budget and the 200k tail-read bound are unchanged; 230 tests OK; policy unchanged.
- **Ablation** (same inputs):
  - no `episode_sha256` in the header: the independent digest still exists, but the log cannot name the episode; adding the field restores the binding.
  - a changed target/seed/config changes the digest and `strict` returns `new`; a volatile-only change keeps `resume`. The identity property and its decision die with the projection/decision cut.
- **Verdict**: episode-identity trace binding. Behavior is unchanged; the measured deltas are same/different digests, the resume/new/ask matrix, the pause guard, and the header `episode_sha256`. No action or emergence claim.
- **Gates**: unittest 230/230 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_identity.TestEpisodeIdentity.test_volatile_fields_are_ignored -v` -> before: ModuleNotFoundError (`identity`); after: OK.
  - `python -m unittest tests.test_identity -v` -> 9 OK.
  - `python -m evals.resume_identity` -> same resume/13, changed-seed new/6, changed-target new, volatile resume, legacy ask, policy-any resume; headers match.
  - `python -m unittest discover -s tests -t .` -> 230 OK.
  - `python aikit.py check brain` -> 5/5 after adding `budget.py` and `identity.py` to the README tree.
- **Pinned regression baselines for cycle 67**: unittest 230 OK; aikit 5/5; same T3:15 digest/resume/13 steps; T3:65 different digest/6; changed target new; volatile resume; legacy ask; policy-any resume; header digest binding; generous budget 13/1.0/actions match; caps 4/3, 3/2, 10/8, seconds; Merkle 12-20/count 8 proof 3; prompt 63->52/13; synthetic 228->52; keyed 8/8 MACs; anchor journal 2 seq 11/16; single anchor 4/4; 200k head lookup <120 ms (0.764); standing 466/240/217; T1 0-99 1581; holdout 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; policy d097b97b...; multi 9/16/11/13/14 blind 9/200/200/200/200; three 15/12/10/13/19 blind 200/200/10/200/200; trust 16/8/13/6; escape 19/18; cold-start 16/8/13/6; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 67 - workspace source hash bound into run headers (harness transfer)

- **Baseline** (commit 6c4a572, cycle 66; same T3:15 and temp tree):
  - canonical gate: 230 tests OK; aikit check 5/5; policy d097b97b466264471c140abe3f9a1d116d7bdcda3c9e4a798413ddc38b09ba1e.
  - headers bound episode identity, policy and model manifests, but not the source tree that produced the run; there was no workspace file map or tree digest.
- **Gap**: a run log could not be tied to the exact source tree. A replay/evidence claim needs a deterministic source digest that ignores caches, logs, reports and databases.
- **Target delta**: a three-file temp tree hashes stably; editing `a.py` changes the digest; adding `__pycache__/x.pyc` does not; `run_task_logged(workspace_root=...)` writes a matching `workspace_sha256`; default `None` leaves it null; T3:15 stays 13/1.0.
- **Falsifier**: the digest changes on a cache file or rerun; a source edit leaves it unchanged; the header disagrees with the independent digest; default headers gain a value; behavior/pins move.
- **Change**: workspace.py adds `workspace_files` and `workspace_digest` with a stable skip set (`.git`, caches, `.aikit`, reports, logs/JSONL/db/bak/tmp). `run_task_logged` gains `workspace_root=None`; when supplied it computes the digest and writes `workspace_sha256` into the header via the additive `Telemetry.write_header` field. Tests cover map exclusions, digest stability/sensitivity, missing roots, header binding and default null; the eval measures same/changed/ignored-cache/default. README and ADR-061 record the contract. No new dependencies; no schema bump.
- **After** (same temp tree and T3:15):
  - same: digest stable, header matches, 13 steps/1.0; changed `a.py`: different digest and header, 13/1.0; ignored cache: same digest/header, 13/1.0; default: header `workspace_sha256` null, 13/1.0.
  - behavior, standing 466/240/217, T1 0-99 1581, holdout 1581/800/738, fixed-rig syn 0.05411532 phi 0.0, trust 16/8/13/6, escape 19/18, dead-pool (7,5) 16, cold-start 16/8/13/6, keyed telemetry, prompt budget, Merkle, execution budget, resume identity and the 200k tail-read bound are unchanged; 235 tests OK; policy unchanged.
- **Ablation** (same T3:15):
  - `workspace_root=None`: the header field is null and no source tree is hashed; the binding and its evidence die with the cut.
  - ignored cache/`.git`/logs/reports: the digest is unchanged, so only source changes move the evidence.
- **Verdict**: evidence-binding extension. Behavior is unchanged; the measured deltas are the source digest and header binding. No action or emergence claim.
- **Gates**: unittest 235/235 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_workspace.TestWorkspaceHash.test_file_map_excludes_noise -v` -> before: ModuleNotFoundError (`workspace`); after: OK.
  - `python -m unittest tests.test_workspace -v` -> 5 OK.
  - `python -m evals.workspace_binding` -> same/cache stable, changed source differs, default null, 13/1.0.
  - `python -m unittest discover -s tests -t .` -> 235 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 68**: unittest 235 OK; aikit 5/5; workspace same/cache digest stable, changed source differs, default null; T3:15 13/1.0; episode same/resume/13, T3:65 new/6; generous budget 13/1.0, caps 4/3, 3/2, 10/8, seconds; Merkle 12-20/count 8 proof 3; prompt 63->52/13; synthetic 228->52; keyed 8/8 MACs; anchor journal 2 seq 11/16; single anchor 4/4; 200k head lookup <120 ms (0.764); standing 466/240/217; T1 0-99 1581; holdout 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; policy d097b97b...; multi 9/16/11/13/14 blind 9/200/200/200/200; three 15/12/10/13/19 blind 200/200/10/200/200; trust 16/8/13/6; escape 19/18; cold-start 16/8/13/6; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 68 - portable run snapshots and deterministic diffs (lattice transfer)

- **Baseline** (commit 167c555, cycle 67; same T3:15/65):
  - canonical gate: 235 tests OK; aikit check 5/5; policy d097b97b466264471c140abe3f9a1d116d7bdcda3c9e4a798413ddc38b09ba1e.
  - cycle evidence was prose and ad hoc; there was no portable run snapshot or deterministic added/removed/changed diff.
- **Gap**: comparing two batteries required manual reading and could not distinguish a changed record from a volatile bookkeeping difference. `lattice/diff.py:40` keys records by `(record_type,id)`, ignores volatile fields and sorts output.
- **Target delta**: capture T3:15/65 as two sorted records; same/volatile-only diffs empty; changed steps names the record/field; added/removed names one record each; export/read is atomic and lossless; captured runs stay 13/6 steps with 1.0 reward.
- **Falsifier**: same battery diff is non-empty; a volatile field is reported; a real change is missed; export/read differs; adding/removing is not named; behavior/pins move.
- **Change**: snapshot.py adds `run_record`, `capture_snapshot`, `export_snapshot`, `read_snapshot` and `diff_records` (volatile-aware, sorted, summary). Capture unlinks per-case logs so repeated captures are fresh; export writes sorted JSONL atomically. tests/test_snapshot.py covers added/removed/changed, volatile-only unchanged, empty same diff, roundtrip, run fields and capture equality; evals/snapshot_diff.py measures same/changed/added/removed/volatile over T3:15/65. README and ADR-062 record the contract. No new dependencies; no policy change.
- **After** (same battery):
  - captured 2 records: `T3_navigate:15` 13 steps, `T3_navigate:65` 6 steps, both success/1.0; action prefixes and syn/phi present.
  - same: `{added:0, removed:0, changed:0, unchanged:2}`; volatile: same empty diff; changed steps: one `fields:["steps"]`; added: one record; removed: one record.
  - export/read roundtrip matches with no `.tmp`; behavior, standing 466/240/217, T1 0-99 1581, holdout 1581/800/738, fixed-rig syn 0.05411532 phi 0.0, trust 16/8/13/6, escape 19/18, dead-pool (7,5) 16, cold-start 16/8/13/6, keyed telemetry, prompt budget, Merkle, execution budget, resume identity, workspace binding and the 200k tail-read bound are unchanged; 241 tests OK; policy unchanged.
- **Ablation** (same battery):
  - without a snapshot/diff, changes are unmeasured prose; with it, same/volatile are empty and changed/added/removed are named. The property and its records die with the snapshot cut.
  - duplicate `(record_type,id)` records are last-wins; only declared volatile fields are ignored.
- **Verdict**: evidence-tooling extension. Behavior is unchanged; the measured deltas are the two run records and the deterministic diff summaries. No action or emergence claim.
- **Gates**: unittest 241/241 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_snapshot.TestSnapshotDiff.test_added_removed_changed_and_volatile -v` -> before: ModuleNotFoundError (`snapshot`); after: OK.
  - `python -m unittest tests.test_snapshot -v` -> 6 OK.
  - `python -m evals.snapshot_diff` -> same/volatile empty; changed/added/removed named; 13/6/1.0.
  - `python -m unittest discover -s tests -t .` -> 241 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 69**: unittest 241 OK; aikit 5/5; snapshots T3:15/65 13/6 both 1.0; same/volatile empty diff; changed steps/added/removed named; workspace same/cache stable/change/default null; episode same/resume/13, T3:65 new/6; generous budget 13/1.0, caps 4/3, 3/2, 10/8, seconds; Merkle 12-20/count 8 proof 3; prompt 63->52/13; synthetic 228->52; keyed 8/8 MACs; anchor journal 2 seq 11/16; single anchor 4/4; 200k head lookup <120 ms (0.764); standing 466/240/217; T1 0-99 1581; holdout 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; policy d097b97b...; multi 9/16/11/13/14 blind 9/200/200/200/200; three 15/12/10/13/19 blind 200/200/10/200/200; trust 16/8/13/6; escape 19/18; cold-start 16/8/13/6; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 69 - snapshot content-vs-graph digests and meta verification (research-engine transfer)

- **Baseline** (commit 7181635, cycle 68; same T3:15/65):
  - canonical gate: 241 tests OK; aikit check 5/5; policy d097b97b466264471c140abe3f9a1d116d7bdcda3c9e4a798413ddc38b09ba1e.
  - snapshots had a single representation but no exact-vs-semantic digest or self-contained meta verifier; a re-capture with a new timestamp was indistinguishable from a real evidence change.
- **Gap**: exact graph integrity and semantic content stability were conflated. `research-engine/engine/bundle.py:186-222` separates the two and verifies an export against its meta.
- **Target delta**: re-capturing the same battery changes `graph_sha256` (captured_at) but keeps `content_sha256`; changing a steps field changes both; a `.meta` sidecar verifies record count and both digests and names graph/content/missing findings.
- **Falsifier**: re-capture moves content; a real change leaves content unchanged; meta verification accepts a tampered digest or missing meta; behavior/pins move.
- **Change**: snapshot.py adds `graph_sha256`, `content_sha256`, `snapshot_digests`, `write_snapshot_meta` and `verify_snapshot`; `run_record` gains volatile `captured_at`; `export_snapshot(..., meta_path=...)` writes the meta atomically. Tests cover volatile-only vs real changes, digest shape, meta roundtrip/tamper/missing, changed-record verification and re-capture. The eval measures recapture/changed/meta-intact/meta-tampered/missing. README and ADR-063 record the contract. No new dependencies; existing export/read remains compatible.
- **After** (same battery):
  - re-capture: `graph_same=false`, `content_same=true`, 2 records, 13/6 steps, 1.0; changed steps: both false.
  - meta intact: `verify_ok=true`; tampered content: `content-mismatch`; missing: `missing-meta`; changed record: graph+content mismatch.
  - behavior, standing 466/240/217, T1 0-99 1581, holdout 1581/800/738, fixed-rig syn 0.05411532 phi 0.0, trust 16/8/13/6, escape 19/18, dead-pool (7,5) 16, cold-start 16/8/13/6, keyed telemetry, prompt budget, Merkle, execution budget, resume identity, workspace binding and the 200k tail-read bound are unchanged; 247 tests OK; policy unchanged.
- **Ablation** (same battery):
  - without the content projection, a volatile re-capture looks like a real change; with it, content is stable and graph changes.
  - without the meta, no graph/content/record-count verification exists; with it, tampered/missing cases are named. The property dies with the projection/meta cut.
- **Verdict**: evidence-tooling extension. Behavior is unchanged; the measured deltas are graph-vs-content digest stability and meta findings. No action or emergence claim.
- **Gates**: unittest 247/247 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_snapshot_digest.TestSnapshotDigest.test_graph_changes_content_stable_on_volatile -v` -> before: ImportError (`content_sha256`); after: OK.
  - `python -m unittest tests.test_snapshot_digest -v` -> 6 OK.
  - `python -m evals.snapshot_digest` -> recapture graph changes/content stable; changed both; meta intact/tampered/missing.
  - `python -m unittest discover -s tests -t .` -> 247 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 70**: unittest 247 OK; aikit 5/5; recapture graph-changed/content-stable; changed both; meta intact/tampered/missing; T3:15/65 13/6 both 1.0; snapshot diff same/volatile empty; workspace stable/change/default null; episode resume/new/ask; budget 13/1.0 and caps; Merkle 8-record proof 3; prompt 63->52/13; keyed 8/8 MACs; anchor journal 2 seq 11/16; single anchor 4/4; 200k head lookup <120 ms (0.764); standing 466/240/217; T1 0-99 1581; holdout 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; policy d097b97b...; multi 9/16/11/13/14 blind 9/200/200/200/200; three 15/12/10/13/19 blind 200/200/10/200/200; trust 16/8/13/6; escape 19/18; cold-start 16/8/13/6; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 70 - calibration scoring and SelfModel readout (research-engine transfer)

- **Baseline** (commit 9c5f0fa, cycle 69; same T3:15):
  - canonical gate: 247 tests OK; aikit check 5/5; policy d097b97b466264471c140abe3f9a1d116d7bdcda3c9e4a798413ddc38b09ba1e.
  - `SelfModel` recorded confidence and outcomes but never scored whether the confidence was calibrated; there was no Brier/log-loss/skill or reliability-bin readout.
- **Gap**: confidence was an uncalibrated number with no proper scoring rule. `research-engine/engine/calibration.py:38-159` provides Brier, log loss, base rate, skill, reliability bins and small-sample warnings.
- **Target delta**: perfect forecasts -> Brier 0, skill 1; inverted -> Brier 1, log loss 27.631, skill -3; calibrated fixture between; small/ignored warnings; a real T3:15 persistent SelfModel keeps 13/1.0 and reports 13 resolved forecasts with Brier 0.230769.
- **Falsifier**: perfect and inverted score the same; a real change does not move Brier; unresolved outcomes are counted as resolved; invalid inputs pass; behavior/pins move.
- **Change**: calibration.py adds `MIN_RESOLVED`, `BIN_EDGES`, probability clipping, validation and `summary(forecasts, min_resolved=10)` with counts/coverage/Brier/log loss/base rate/skill/five bins/warnings. SelfModel records `_outcomes` alongside `_confs`, exposes `calibration()`, and clears both on reset; `snapshot()` is unchanged. Tests cover perfect/inverted/calibrated/empty/small/ignored/invalid and the SelfModel readout; the eval adds the real T3 run. README and ADR-064 record the contract. No new dependencies beyond stdlib `math`.
- **After** (same fixtures and run):
  - perfect: Brier 0, log_loss 0, skill 1, 10 resolved; calibrated: Brier 0.166, skill 0.308; inverted: Brier 1, log_loss 27.631021, skill -3; small: 3 resolved with warning; ignored: coverage 0.6667, 1 ignored.
  - T3:15 persistent SelfModel: 13 steps, 1.0 reward, 13 resolved forecasts, Brier 0.230769; the 0.5-confidence bin is flagged overconfident.
  - behavior, standing 466/240/217, T1 0-99 1581, holdout 1581/800/738, fixed-rig syn 0.05411532 phi 0.0, trust 16/8/13/6, escape 19/18, dead-pool (7,5) 16, cold-start 16/8/13/6, keyed telemetry, prompt budget, Merkle, execution budget, resume identity, workspace binding, snapshot diff/digest and the 200k tail-read bound are unchanged; 254 tests OK; policy unchanged.
- **Ablation** (same fixtures):
  - without the scorer, confidence is an unlabeled number; with it, perfect/inverted/calibrated separate by Brier/log loss/skill. The property and its bins die with the scorer cut.
  - unresolved outcomes are ignored by the projection; small sets warn rather than pretending to be decisive.
- **Verdict**: measurement extension. Behavior is unchanged; the measured deltas are Brier/log loss/skill/bin warnings for fixtures and the persisted SelfModel confidence/outcome pairs. No action or emergence claim; confidence values are reward proxies, not learned probabilities.
- **Gates**: unittest 254/254 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_calibration.TestCalibration.test_perfect_forecast -v` -> before: ModuleNotFoundError (`calibration`); after: OK.
  - `python -m unittest tests.test_calibration -v` -> 7 OK.
  - `python -m evals.calibration` -> perfect 0/1, calibrated 0.166, inverted 1/-3, small/ignored warnings, T3 13/1.0 Brier 0.230769.
  - `python -m unittest discover -s tests -t .` -> 254 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 71**: unittest 254 OK; aikit 5/5; calibration perfect 0/1, calibrated 0.166, inverted 1/-3, small/ignored, T3 Brier 0.230769; recapture graph/content stable vs changed; meta intact/tampered/missing; snapshot diff same/volatile empty; workspace stable/change/default null; episode resume/new/ask; budget 13/1.0 and caps; Merkle 8-record proof 3; prompt 63->52/13; keyed 8/8 MACs; anchor journal 2 seq 11/16; single anchor 4/4; 200k head lookup <120 ms (0.764); standing 466/240/217; T1 0-99 1581; holdout 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; policy d097b97b...; multi 9/16/11/13/14 blind 9/200/200/200/200; three 15/12/10/13/19 blind 200/200/10/200/200; trust 16/8/13/6; escape 19/18; cold-start 16/8/13/6; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 71 - immutable claim, kill-test and verdict ledger (research-engine transfer)

- **Baseline** (commit 0f046d4, cycle 70; same T3:15/65):
  - canonical gate: 254 tests OK; aikit check 5/5; policy d097b97b466264471c140abe3f9a1d116d7bdcda3c9e4a798413ddc38b09ba1e.
  - Brain had calibration and snapshot evidence but no structured claim with a kill test, verdict status or verdict history.
- **Gap**: evidence statements were prose. A claim could not carry a kill test or an append-only supports/refutes/inconclusive verdict record, and a declared confidence could not be separated from the evidence-based status.
- **Target delta**: six T3 claims with kill tests; three supported, two refuted, one inconclusive; verdict history preserved; confidence independent of status; JSON roundtrip exact; T3:15/65 remain 13/6 steps with 1.0.
- **Falsifier**: a wrong claim is supported; a correct claim is refuted; confidence decides status; history is lost or mutable; roundtrip differs; behavior/pins move.
- **Change**: claims.py adds frozen `Verdict` and `Claim` dataclasses plus `ClaimLedger` (`add`, `record`, `get`, `claims`, `summary`, `to_dict`, `from_dict`) and `record_verdict`. Text/kill test/confidence/status/evidence are validated; `record` appends a verdict and returns a new claim without mutating the old one; ids are `C1`, `C2`, … with duplicates refused. tests/test_claims.py covers defaults, transitions, immutability, summary, invalid inputs, roundtrip and frozen records; evals/claims.py judges six T3 claims. README and ADR-065 record the contract. No new dependencies; no action or policy change.
- **After** (same T3 runs):
  - C1 T3:15 13 steps supported; C2 T3:65 13 steps refuted (actual 6); C3 T3:15 reward 1.0 supported; C4 T3:65 reward 0.0 refuted (actual 1.0); C5 T3:65 6 steps supported; C6 energy inconclusive.
  - summary: 6 claims, 3 supported/2 refuted/1 inconclusive/0 proposed, 6 verdicts; `to_dict`/`from_dict` roundtrip true; declared confidence 0.5-0.95 does not decide status.
  - behavior, standing 466/240/217, T1 0-99 1581, holdout 1581/800/738, fixed-rig syn 0.05411532 phi 0.0, trust 16/8/13/6, escape 19/18, dead-pool (7,5) 16, cold-start 16/8/13/6, keyed telemetry, prompt budget, Merkle, execution budget, resume identity, workspace binding, snapshot diff/digest, calibration and the 200k tail-read bound are unchanged; 261 tests OK; policy unchanged.
- **Ablation** (same claims):
  - without a verdict, a claim stays proposed; with supports/refutes/inconclusive it becomes supported/refuted/inconclusive. The status and history die with the verdict cut.
  - confidence alone does not flip a claim; the evidence-based verdict does.
- **Verdict**: evidence-structure extension. Behavior is unchanged; the measured deltas are claim statuses, verdict history and the 3/2/1 summary. No action or emergence claim.
- **Gates**: unittest 261/261 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_claims.TestClaims.test_add_claim_defaults_and_ids -v` -> before: ModuleNotFoundError (`claims`); after: OK.
  - `python -m unittest tests.test_claims -v` -> 7 OK.
  - `python -m evals.claims` -> 6 claims, 3 supported/2 refuted/1 inconclusive, roundtrip true, 13/6 steps.
  - `python -m unittest discover -s tests -t .` -> 261 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 72**: unittest 261 OK; aikit 5/5; claims 3 supported/2 refuted/1 inconclusive, roundtrip; calibration perfect 0/1, calibrated 0.166, inverted 1/-3, T3 Brier 0.230769; recapture graph/content stable vs changed; meta intact/tampered/missing; snapshot diff same/volatile empty; workspace stable/change/default null; episode resume/new/ask; budget 13/1.0 and caps; Merkle 8-record proof 3; prompt 63->52/13; keyed 8/8 MACs; anchor journal 2 seq 11/16; single anchor 4/4; 200k head lookup <120 ms (0.764); standing 466/240/217; T1 0-99 1581; holdout 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; policy d097b97b...; multi 9/16/11/13/14 blind 9/200/200/200/200; three 15/12/10/13/19 blind 200/200/10/200/200; trust 16/8/13/6; escape 19/18; cold-start 16/8/13/6; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 72 - single-target BFS progress guard for backend movement (fresh gap audit)

- **Baseline** (commit 199270f, cycle 71; same wrong-way backend and seeds):
  - canonical gate: 261 tests OK; aikit check 5/5; policy d097b97b466264471c140abe3f9a1d116d7bdcda3c9e4a798413ddc38b09ba1e.
  - the no-op guard rejected wait/premature collect/blocked movement, but a legal free-cell movement away from a fixed target was accepted until the 20-step trust window expired.
  - wrong-way baseline: T1:71 36 steps/3.0/22 calls; T2:3 34/1.0/21; T3:15 33/1.0/21; T3:65 26/1.0/21; planner fallbacks 1 after the stall, then skipped.
- **Gap**: a backend could burn the whole trust window walking away from a fixed target with legal moves. The existing guards did not compare movement direction against the task goal.
- **Target delta**: a strictly distance-increasing movement is rejected immediately as `no-progress`; T3:15 33 -> 13 steps and 21 -> 13 calls, T3:65 26 -> 6 and 21 -> 6, T2:3 34 -> 8 and 21 -> 8; T1 item tours remain 36/22; rule-only behavior and all standing/trace pins stay fixed.
- **Falsifier**: the guard rejects an equal-distance or distance-decreasing move; T1 or no-target states change; a rule-only run changes; the wrong-way cost does not fall; any standing/fixed-rig pin moves.
- **Change**: agent.py adds `_bfs_distance`, `Planner(progress_guard=True)`, the `progress_rejections` counter and `PLANNER_POLICY["backend_progress_guard"] = "single-target-bfs"`. The decision block rejects a legal movement when a fixed `target` exists, no `items_positions` remain, and the BFS distance after the proposal is strictly greater than after the rule action (a non-movement rule action uses its current distance); `reason="no-progress"` and `progress: {proposed, rule}` are recorded. Equal-distance moves are accepted; `progress_guard=False` restores accept-until-stall. tests/test_model_backend.py adds the wrong-way backend and five guard tests; test_random_floor.py disables the guard in its raw control; evals/progress_guard.py measures guard-off/on across T3:15, T3:65, T2:3 and T1:71. README and ADR-066 record the contract. No new dependencies; no schema change.
- **After** (same wrong-way backend and seeds):
  - guard on: T3:15 13 steps/1.0/13 calls/12 progress rejections; T3:65 6/1.0/6/5; T2:3 8/1.0/8/8; T1:71 36/3.0/22/0.
  - guard off: T3:15 33/1.0/21; T3:65 26/1.0/21; T2:3 34/1.0/21; T1:71 36/3.0/22; one stall fallback then skipped in each fixed-target case.
  - rule-only standing 466/240/217, T1 0-99 1581, holdout 1581/800/738, fixed-rig sym 0.05411532 syn_n 0.10814360 phi 0.0 with hub0/m0 0.0, trust 16/8/13/6, escape 19/18, dead-pool (7,5) 16, cold-start 16/8/13/6, goldens and the 200k tail-read bound are unchanged; 266 tests OK.
  - policy key added, so `policy_digest` is now 3c04d54a858a45abf62bde3ef9e9976302045bd50e2259db3ae38476029095c8 (was d097b97b...).
- **Ablation** (same backend and seeds):
  - `progress_guard=False`: the wrong-way proposals are accepted for the 20-step trust window and the fixed-target runs return to 33/26/34 steps with 21 calls; the guard-on costs are 13/6/8. The property dies with the guard cut.
  - T1:71 has no fixed `target` and keeps items, so the guard is skipped and both modes are identical at 36/3.0/22; the raw random control now disables `progress_guard` as well, preserving its backend-alone intent.
- **Verdict**: planner-safety and cost improvement. Rule-only behavior is unchanged; the measured delta is immediate rejection of legal wrong-way moves (T3:15 -20 steps/-8 calls, T3:65 -20/-15, T2:3 -26/-13) with equal-distance moves still accepted and T1 untouched. No emergence claim.
- **Gates**: unittest 266/266 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_model_backend.TestModelBackendSeam.test_progress_guard_rejects_wrong_way_backend -v` -> before: 33 != 13 (T3:15); after: OK.
  - `python -m unittest tests.test_model_backend -v` -> 20 OK.
  - `python -m evals.progress_guard` -> guard-off 33/26/34/36 with 21 calls; guard-on 13/6/8/36 with 13/6/8/22 calls; policy 3c04d54a....
  - `python -m unittest tests.test_random_floor tests.test_verdict tests.test_policy_binding -v` -> 9 OK.
  - `python -m unittest discover -s tests -t .` -> 266 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 73**: unittest 266 OK; aikit 5/5; progress guard T3:15 13/13/12, T3:65 6/6/5, T2:3 8/8/8, T1:71 36/22/0; guard-off T3:15 33/21, T3:65 26/21, T2:3 34/21, T1:71 36/22; policy 3c04d54a...; claims 3 supported/2 refuted/1 inconclusive; calibration perfect 0/1, calibrated 0.166, inverted 1/-3, T3 Brier 0.230769; recapture graph/content stable vs changed; meta intact/tampered/missing; snapshot diff same/volatile empty; workspace stable/change/default null; episode resume/new/ask; budget 13/1.0 and caps; Merkle 8-record proof 3; prompt 63->52/13; keyed 8/8 MACs; anchor journal 2 seq 11/16; single anchor 4/4; 200k head lookup <120 ms (0.764); standing 466/240/217; T1 0-99 1581; holdout 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; multi 9/16/11/13/14 blind 9/200/200/200/200; three 15/12/10/13/19 blind 200/200/10/200/200; trust 16/8/13/6; escape 19/18; cold-start 16/8/13/6; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 73 - append-only Merkle batch journal and retained historical proofs (fresh gap audit)

- **Baseline** (commit cde5c13, cycle 72; same 24+8-record log):
  - canonical gate: 266 tests OK; aikit check 5/5; policy 3c04d54a858a45abf62bde3ef9e9976302045bd50e2259db3ae38476029095c8.
  - `write_merkle_anchor` writes one `.merkle` sidecar; a second anchor overwrites the first. In the eval's single-anchor mode, the latest batch 24–32 verifies but record 20's proof fails with `record index is outside the merkle batch`.
- **Gap**: the cycle-64 Merkle anchor commits only the latest batch. Historical batch roots and inclusion proofs are lost when a newer anchor is written, so earlier evidence cannot be checked without replaying the log.
- **Target delta**: two batch anchors (16–24 and 24–32) chain by `prev`/`hash`; the journal and both roots verify; record 20 proves against batch 1 after batch 2 is written; truncation, deleted first anchor, tampered root and range rollback are named; the single-anchor API remains unchanged.
- **Falsifier**: the second anchor does not link to the first; an earlier proof is lost; truncation/tamper/rollback passes; the single-anchor path changes; any behavior/pin moves.
- **Change**: telemetry/merkle.py adds `GENESIS`, `_anchor_hash`, `_validate_journal_record`, `_scan_journal`, `_build_anchor` (shared with the single anchor), `append_merkle_anchor`, `verify_merkle_journal` and `merkle_proof_for_journal_record`; `Telemetry.append_merkle_anchor` wraps the writer. Journal records carry the anchor fields plus `prev`/`hash`; ranges must not roll back; appends are fsynced. `verify_merkle_journal` checks links and, when a log is supplied, every batch root/range; `log_path=None` validates links only. The proof function selects the latest batch containing the record. tests/test_merkle_journal.py covers chaining, historical proof, truncation, deleted anchor, resigned tampered root, tampered hash, rollback, missing/empty, link-only verification, out-of-range proof, the Telemetry wrapper and the unchanged single anchor; evals/merkle_journal.py measures intact/truncated/deleted/tampered/rollback/missing/single-anchor. README and ADR-067 record the contract. No new dependencies; no behavior or policy change.
- **After** (same 24+8-record log):
  - intact: 2 anchors, latest 24–32; journal `ok=true`; record 20 proof batch 1 `ok=true`; record 28 proof batch 2 `ok=true`.
  - truncated to 30: `ok=false`, `truncated-batch:2:32>30`; record 20 still proves against batch 1.
  - deleted first anchor: `ok=false`, `prev does not match the previous anchor`; tampered root (resigned): `root-mismatch:2`; rollback append: `merkle journal range rolls back from (16, 24)`; missing: `missing-journal`.
  - single-anchor ablation: latest anchor `ok=true`, earlier record 20 proof fails with `record index is outside the merkle batch`; this is the overwrite gap.
  - behavior, standing 466/240/217, T1 0-99 1581, holdout 1581/800/738, fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0, progress guard, trust 16/8/13/6, escape 19/18, dead-pool (7,5) 16, cold-start 16/8/13/6, keyed telemetry, prompt budget, execution budget, resume identity, workspace binding, snapshot diff/digest, calibration, claims and the 200k tail-read bound are unchanged; 277 tests OK; policy unchanged.
- **Ablation** (same log):
  - single `.merkle` anchor: only the latest batch survives, and record 20's proof is rejected; with the journal, both batches survive and record 20 proves against batch 1. The historical-membership property dies with the journal cut.
  - journal link-only verification (`log_path=None`) still detects prev/hash/order defects; root verification additionally needs the log.
- **Verdict**: trace-integrity extension. Behavior is unchanged; the measured deltas are the two chained batches, the retained batch-1 proof, and the named truncation/tamper/rollback/missing findings. No action or emergence claim.
- **Gates**: unittest 277/277 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_merkle_journal.TestMerkleJournal.test_two_batches_chain_and_historical_proof -v` -> before: ImportError (`append_merkle_anchor`); after: OK.
  - `python -m unittest tests.test_merkle_journal -v` -> 11 OK.
  - `python -m unittest tests.test_merkle tests.test_merkle_journal` -> 22 OK.
  - `python -m evals.merkle_journal` -> intact 2 anchors/24–32/both proofs; truncated `truncated-batch:2:32>30` with batch-1 proof; deleted prev error; tampered `root-mismatch:2`; rollback error; missing; single-anchor history proof fails.
  - `python -m unittest discover -s tests -t .` -> 277 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 74**: unittest 277 OK; aikit 5/5; Merkle journal 2 anchors 16–24/24–32, both proofs, truncated `truncated-batch:2:32>30`, deleted prev, tampered `root-mismatch:2`, rollback refused, missing, single-anchor history lost; policy 3c04d54a...; progress guard T3:15 13/13/12, T3:65 6/6/5, T2:3 8/8/8, T1:71 36/22/0; guard-off 33/21, 26/21, 34/21, 36/22; claims 3 supported/2 refuted/1 inconclusive; calibration perfect 0/1, calibrated 0.166, inverted 1/-3, T3 Brier 0.230769; recapture graph/content stable vs changed; meta intact/tampered/missing; snapshot diff same/volatile empty; workspace stable/change/default null; episode resume/new/ask; budget 13/1.0 and caps; Merkle anchor 8-record proof 3; prompt 63->52/13; keyed 8/8 MACs; anchor journal 2 seq 11/16; single anchor 4/4; 200k head lookup <120 ms (0.764); standing 466/240/217; T1 0-99 1581; holdout 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; multi 9/16/11/13/14 blind 9/200/200/200/200; three 15/12/10/13/19 blind 200/200/10/200/200; trust 16/8/13/6; escape 19/18; cold-start 16/8/13/6; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 74 - skip backend calls after a consecutive progress-rejection streak (fresh gap audit)

- **Baseline** (commit 71653ea, cycle 73; same wrong-way backend and seeds):
  - canonical gate: 277 tests OK; aikit check 5/5; policy 3c04d54a...
  - guard-on (skip None): T3:15 13 steps/13 calls/12 rejections, T3:65 6/6/5, T2:3 8/8/8, T1:71 36/22/0; guard-off 33/26/34/36 steps with 21/21/21/22 calls; the backend was still called every step after each rejection.
- **Gap**: repeated progress rejections still spent a model call every step. After three consecutive wrong-way proposals, further calls have no evidence of usefulness.
- **Target delta**: with `progress_skip_after=3`, T3:15/T3:65/T2:3 use 4/4/3 calls and 3 rejections, remain 13/6/8 steps with 1.0 reward, and end in `skipped-progress`; `progress_skip_after=None` keeps the guard-only 13/6/8 calls; T1 remains 36/22.
- **Falsifier**: the skip triggers before 3 consecutive progress rejections; a non-progress outcome does not reset the streak; calls/steps/rewards move in an unintended way; T1 or guard-off changes; any standing/pin moves.
- **Change**: agent.py adds `Planner(progress_skip_after=3)`, `_progress_distrusted`, `_progress_streak`, reset in `reset_trust`, a pre-call `skipped-progress` branch and decision fields `progress_skip_after/progress_streak/progress_distrusted`; `PLANNER_POLICY["backend_progress_skip"] = "streak>=3->match-only"`. tests/test_model_backend.py adds five tests; test_random_floor.py disables the skip in the raw control; evals/progress_guard.py adds `skip-on` alongside `guard-off`/`guard-on`. README and ADR-068 record the contract. No new dependencies.
- **After** (same backend and seeds):
  - skip-on: T3:15 13 steps/1.0/4 calls/3 rejections; T3:65 6/1.0/4/3; T2:3 8/1.0/3/3; T1:71 36/3.0/22/0; last reason `skipped-progress`, `progress_distrusted=true`, `distrusted=false`.
  - guard-on skip None: 13/6/8 steps, 13/6/8 calls, 12/5/8 rejections, `no-progress`.
  - guard-off: 33/26/34/36 steps, 21/21/21/22 calls, no progress rejections.
  - alternating wrong-way/wait: 13 calls, 6 rejections, `progress_distrusted=false` (streak resets); two episodes: 4 calls then 4 more (8 total), skip re-armed.
  - behavior, standing 466/240/217, T1 0-99 1581, holdout 1581/800/738, fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0, trust 16/8/13/6, escape 19/18, dead-pool (7,5) 16, cold-start 16/8/13/6, Merkle journal, keyed telemetry, prompt budget, execution budget, resume identity, workspace binding, snapshot diff/digest, calibration, claims and the 200k tail-read bound are unchanged; 282 tests OK.
  - policy key added: `policy_digest` is now 7812e53251f1711d9eb50104eacbef8e4223e65ee574cbb8c4e8e07773b5550f (was 3c04d54a...).
- **Ablation** (same backend and seeds):
  - `progress_skip_after=None`: the guard still rejects every wrong-way move but calls continue (13/6/8); `progress_guard=False`: accept-until-stall (21 calls, 33/26/34). The skip property dies with the threshold cut.
  - alternating backend never accumulates three consecutive progress rejections and is not skipped; the skip is consecutive-only, not a lifetime distrust.
- **Verdict**: runtime cost-control extension. Rule actions, steps and rewards are unchanged; the measured delta is model calls 13/6/8 -> 4/4/3 for the guard path (21 -> 4/4/3 from guard-off), with T1 untouched. No emergence claim.
- **Gates**: unittest 282/282 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_model_backend.TestModelBackendSeam.test_progress_skip_stops_calls_after_streak -v` -> before: calls 13 != 4; after: OK.
  - `python -m unittest tests.test_model_backend -v` -> 25 OK.
  - `python -m evals.progress_guard` -> guard-off 33/26/34/36 with 21 calls; guard-on 13/6/8 with 13/6/8 calls; skip-on 13/6/8 with 4/4/3 calls and 3 rejections; policy 7812e532....
  - `python -m unittest discover -s tests -t .` -> 282 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 75**: unittest 282 OK; aikit 5/5; progress skip-on T3:15 13/4/3, T3:65 6/4/3, T2:3 8/3/3, T1:71 36/22/0; guard-on 13/13/12, 6/6/5, 8/8/8, 36/22/0; guard-off 33/21, 26/21, 34/21, 36/22; alternating 13 calls/6 rejections; two episodes 8 calls; policy 7812e532...; Merkle journal 2 anchors 16-24/24-32, both proofs, truncated 2:32>30, deleted prev, tampered root-mismatch:2, rollback refused, missing, single-anchor history lost; claims 3 supported/2 refuted/1 inconclusive; calibration perfect 0/1, calibrated 0.166, inverted 1/-3, T3 Brier 0.230769; recapture graph/content stable vs changed; meta intact/tampered/missing; snapshot diff same/volatile empty; workspace stable/change/default null; episode resume/new/ask; budget 13/1.0 and caps; Merkle anchor 8-record proof 3; prompt 63->52/13; keyed 8/8 MACs; anchor journal 2 seq 11/16; single anchor 4/4; 200k head lookup <120 ms (0.764); standing 466/240/217; T1 0-99 1581; holdout 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; multi 9/16/11/13/14 blind 9/200/200/200/200; three 15/12/10/13/19 blind 200/200/10/200/200; trust 16/8/13/6; escape 19/18; cold-start 16/8/13/6; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 75 - durable checksummed claim-ledger store (fresh gap audit)

- **Baseline** (commit 8c311e8, cycle 74; same six T3 claims):
  - canonical gate: 282 tests OK; aikit check 5/5; policy 7812e53251f1711d9eb50104eacbef8e4223e65ee574cbb8c4e8e07773b5550f.
  - `ClaimLedger` had `to_dict`/`from_dict` but no file API: all claims and verdicts lived only in memory.
- **Gap**: evidence could not survive process exit. A durable store needs atomic replace, a previous-snapshot backup, writer serialisation and corrupt-primary quarantine.
- **Target delta**: save/load a 6-claim/6-verdict ledger with a matching checksum; a second save creates `.bak`; a corrupt primary is quarantined and the 3-claim backup is loaded; tamper/missing/schema defects are named; a stale lock is stolen and a fresh lock refuses the write; no temporary files remain.
- **Falsifier**: a roundtrip loses claims/verdicts; a checksum mismatch passes; a corrupt primary destroys the only good copy; a fresh lock is ignored or a stale lock hangs; temp files remain; behavior/pins move.
- **Change**: claims_store.py adds `STORE_SCHEMA`, `save_ledger`, `load_ledger` and `verify_ledger_file`. Snapshots carry `{schema, saved_at, claims, sha256}`; saves validate inputs, require 10 MiB free, take an `O_CREAT|O_EXCL` lock (30 s stale steal, bounded timeout), write temp+fsync, back up the previous primary through a temp file, replace with five retries and fsync the directory. Loads validate schema/checksum/claims, return an empty ledger when absent, quarantine a corrupt primary as `.corrupt` and try `.bak`; verification names `missing-primary`/`invalid-primary`. tests/test_claims_store.py covers roundtrip, missing, backup fallback, missing-primary backup load, tamper, schema, stale lock, fresh-lock timeout, no temp leftovers, deterministic checksum and invalid inputs; evals/claims_store.py measures in-memory/roundtrip/corrupt-primary/tampered/missing/stale-lock/fresh-lock. README and ADR-069 record the contract. No new dependencies; no agent behavior or policy change.
- **After** (same six claims):
  - in-memory: 6 claims/6 verdicts, `file_before=false`, then save/load 6/6, `file_after=true`; roundtrip verification `ok=true` with a 64-hex checksum.
  - corrupt primary after saves of 3 then 6 claims: verification false (`invalid-primary: claim store is not valid JSON`), quarantine true, load returns the 3-claim/3-verdict backup.
  - tampered claim without a checksum update: verification false (`claim store checksum does not match its payload`), quarantine true, load raises; missing: empty ledger + `missing-primary`; stale lock: save succeeds and the lock is removed; fresh lock with timeout 0: `TimeoutError`, no primary written.
  - 11 store tests; 293 tests total; behavior, standing 466/240/217, T1 0-99 1581, holdout 1581/800/738, fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0, progress guard/skip, Merkle journal, keyed telemetry, prompt budget, execution budget, resume identity, workspace binding, snapshot diff/digest, calibration, claims and the 200k tail-read bound unchanged; policy 7812e532... unchanged.
- **Ablation** (same six claims):
  - in-memory only: 6 claims/6 verdicts exist in the process, `file_before=false` and no snapshot survives; after save/load, 6/6 are restored and `file_after=true`. The durability property dies without the store.
  - corrupt primary with `.bak`: the primary is quarantined and the previous 3-claim snapshot is loaded; without a backup the load raises after quarantine.
- **Verdict**: evidence-durability extension. Behavior is unchanged; the measured deltas are persistent 6/6 evidence, backup recovery 3/3, and named checksum/schema/lock defects. No action or emergence claim.
- **Gates**: unittest 293/293 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_claims_store.TestClaimStore.test_roundtrip_preserves_claims_and_verdicts -v` -> before: ModuleNotFoundError (`claims_store`); after: OK.
  - `python -m unittest tests.test_claims_store -v` -> 11 OK.
  - `python -m evals.claims_store` -> in-memory file-before/after 6/6; roundtrip 6/6 ok; corrupt-primary 3/3 from backup + quarantine; tamper checksum; missing; stale-lock steal; fresh-lock timeout.
  - `python -m unittest discover -s tests -t .` -> 293 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 76**: unittest 293 OK; aikit 5/5; claim store roundtrip 6 claims/6 verdicts ok; corrupt-primary backup 3/3 + quarantine; tamper checksum; missing; stale lock stolen; fresh lock timeout; no temp files; policy 7812e532...; progress skip-on T3:15 13/4/3, T3:65 6/4/3, T2:3 8/3/3, T1:71 36/22/0; guard-on 13/13/12, 6/6/5, 8/8/8, 36/22/0; guard-off 33/21, 26/21, 34/21, 36/22; Merkle journal 2 anchors 16-24/24-32, both proofs, truncated 2:32>30, deleted prev, tampered root-mismatch:2, rollback refused, missing, single-anchor history lost; claims 3 supported/2 refuted/1 inconclusive; calibration perfect 0/1, calibrated 0.166, inverted 1/-3, T3 Brier 0.230769; recapture graph/content stable vs changed; meta intact/tampered/missing; snapshot diff same/volatile empty; workspace stable/change/default null; episode resume/new/ask; budget 13/1.0 and caps; Merkle anchor 8-record proof 3; prompt 63->52/13; keyed 8/8 MACs; anchor journal 2 seq 11/16; single anchor 4/4; 200k head lookup <120 ms (0.764); standing 466/240/217; T1 0-99 1581; holdout 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; multi 9/16/11/13/14 blind 9/200/200/200/200; three 15/12/10/13/19 blind 200/200/10/200/200; trust 16/8/13/6; escape 19/18; cold-start 16/8/13/6; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 76 - append-only checksummed calibration forecast journal (fresh gap audit)

- **Baseline** (commit 45214a8, cycle 75; same six-plus-four forecasts):
  - canonical gate: 293 tests OK; aikit check 5/5; policy 7812e53251f1711d9eb50104eacbef8e4223e65ee574cbb8c4e8e07773b5550f.
  - `calibration.summary` scored only the forecasts present in one process; `SelfModel.calibration()` read the current episode lists; forecasts vanished on exit.
- **Gap**: cross-run Brier/log-loss/skill could not be computed. Forecasts are immutable observations, so an append-only journal is the natural durability model.
- **Target delta**: append/load 6 forecasts (Brier 0.185, skill 0.26, descriptive warning); append 4 more and score 10 resolved (Brier 0.129, skill 0.484, no small-sample warning); duplicate ids refused; tamper/corrupt line/missing/lock defects named.
- **Falsifier**: a roundtrip loses or reorders forecasts; a duplicate is appended; a tampered checksum passes; the two-run aggregate changes the first six; a fresh lock is ignored; behavior/pins move.
- **Change**: calibration_store.py adds `RECORD_SCHEMA`, `append_forecasts`, `load_forecasts` and `verify_forecast_file`. Records carry `{schema,id,probability,outcome,at,sha256}`; the checksum covers the canonical record. Appends validate the whole batch first, require 10 MiB free, take an `O_CREAT|O_EXCL` lock (30 s stale steal, bounded timeout), refuse duplicate ids, append one fsynced line per record and fsync the directory. Loads raise on any defect; verification names corrupt/duplicate records and counts resolved/ignored. tests/test_calibration_store.py covers roundtrip, two-run aggregation, duplicate/reserved ids, invalid batch no-write, tamper, corrupt line, missing, unresolved outcome, stale/fresh lock, empty append and invalid inputs; evals/calibration_store.py measures in-memory/first-run/aggregated/duplicate/tampered/corrupt-line/missing/stale-lock/fresh-lock. README and ADR-070 record the contract. No new dependencies; no agent behavior or policy change.
- **After** (same forecasts):
  - in-memory: 6 resolved, Brier 0.185, skill 0.26, `file_before=false`; after append/load 6 records, `file_after=true`.
  - first-run: 6 records/6 resolved, verification ok; warnings include `6 resolved forecast(s); scores are descriptive below 10` and `bin 0.4-0.6 is overconfident by 0.45`.
  - aggregated: 10 records/10 resolved, first 0.185/0.26, combined Brier 0.129 / skill 0.484, no small-sample warning; bin 0.2-0.4 and 0.4-0.6 warnings remain.
  - duplicate: `duplicate forecast id(s): ['run1:0']`, file unchanged at 6 records; tampered: `line 1: checksum does not match the record`, load raises; corrupt-line: `line 7: invalid JSON`; missing: empty + ok; stale lock: save succeeds, lock removed; fresh lock timeout 0: `TimeoutError`, no file.
  - 13 store tests; 306 tests total; behavior, standing 466/240/217, T1 0-99 1581, holdout 1581/800/738, fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0, progress guard/skip, Merkle journal, claim store, keyed telemetry, prompt budget, execution budget, resume identity, workspace binding, snapshot diff/digest, calibration, claims and the 200k tail-read bound unchanged; policy 7812e532... unchanged.
- **Ablation** (same forecasts):
  - per-process only: 6 forecasts exist in memory, `file_before=false`, and no score survives the process; after append/load, 6/6 are restored and a second run aggregates to 10. The cross-run property dies without the journal.
  - duplicate refusal and per-record checksums: a repeated id cannot double-count, and an edited record is named rather than silently rescored.
- **Verdict**: evidence-durability extension. Behavior is unchanged; the measured deltas are restored 6/6 forecasts, a 10-resolved aggregate (Brier 0.129/skill 0.484), and named duplicate/tamper/corrupt/lock defects. No action or emergence claim.
- **Gates**: unittest 306/306 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_calibration_store.TestCalibrationStore.test_append_and_load_roundtrip -v` -> before: ModuleNotFoundError (`calibration_store`); after: OK.
  - `python -m unittest tests.test_calibration_store -v` -> 13 OK.
  - `python -m evals.calibration_store` -> in-memory/first-run 6/6 0.185/0.26; aggregated 10/10 0.129/0.484; duplicate/tamper/corrupt/missing/stale/fresh lock as above.
  - `python -m unittest discover -s tests -t .` -> 306 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 77**: unittest 306 OK; aikit 5/5; calibration journal first-run 6/6 Brier 0.185/skill 0.26; aggregated 10/10 Brier 0.129/skill 0.484; duplicate refused/file unchanged; tamper checksum; corrupt line 7; missing empty ok; stale lock stolen; fresh lock timeout; policy 7812e532...; claim store roundtrip 6/6, corrupt-primary backup 3/3; progress skip-on T3:15 13/4/3, T3:65 6/4/3, T2:3 8/3/3, T1:71 36/22/0; guard-on 13/13/12, 6/6/5, 8/8/8, 36/22/0; guard-off 33/21, 26/21, 34/21, 36/22; Merkle journal 2 anchors 16-24/24-32, both proofs, truncated 2:32>30, deleted prev, tampered root-mismatch:2, rollback refused, missing, single-anchor history lost; claims 3 supported/2 refuted/1 inconclusive; calibration perfect 0/1, calibrated 0.166, inverted 1/-3, T3 Brier 0.230769; recapture graph/content stable vs changed; meta intact/tampered/missing; snapshot diff same/volatile empty; workspace stable/change/default null; episode resume/new/ask; budget 13/1.0 and caps; Merkle anchor 8-record proof 3; prompt 63->52/13; keyed 8/8 MACs; anchor journal 2 seq 11/16; single anchor 4/4; 200k head lookup <120 ms (0.764); standing 466/240/217; T1 0-99 1581; holdout 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; multi 9/16/11/13/14 blind 9/200/200/200/200; three 15/12/10/13/19 blind 200/200/10/200/200; trust 16/8/13/6; escape 19/18; cold-start 16/8/13/6; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 77 - opt-in SelfModel forecast bridge into the calibration journal (fresh gap audit)

- **Baseline** (commit 82d0d10, cycle 76; same T3:15/65):
  - canonical gate: 306 tests OK; aikit check 5/5; policy 7812e53251f1711d9eb50104eacbef8e4223e65ee574cbb8c4e8e07773b5550f.
  - the calibration journal and the persistent SelfModel both existed, but nothing connected them: real runs recorded confidence/outcome pairs in memory and lost them on exit.
- **Gap**: cross-run calibration required hand-built forecast records. The evidence loop needed an opt-in bridge from a logged run to the journal.
- **Target delta**: a default T3:15 run keeps 13 forecasts in memory and writes no file; `calibration_path` persists exactly those 13 under the header-digest prefix with the same Brier; a second run appends only its 6 new forecasts (19 total, two prefixes); actions/rewards unchanged; missing self-model and corrupt journal fail loudly.
- **Falsifier**: a logged run persists earlier runs' forecasts twice; ids collide or lose the prefix; a default run writes a file; actions/rewards move; a missing self-model is ignored; a corrupt journal is silently accepted.
- **Change**: self_model/model.py adds `forecast_count()` and `forecasts(prefix="run", start=0)` (absolute-index ids, per-run slice). agent.py adds `run_task_logged(..., calibration_path=None)`: fail-fast when the persistent SelfModel or its forecast API is absent; capture `forecast_start` before the run and the header record; after the verdict append only that slice to calibration_store with a prefix from the header digest (fallback: episode digest). A store failure raises after the verdict. tests/test_calibration_bridge.py covers prefix/slice, per-run persistence (13 then 6), in-memory parity, default no-file, missing self-model/API, corrupt-store failure after a done verdict, and action parity; evals/calibration_bridge.py measures default/logged/two-runs/missing-self-model/corrupt-store/actions. README and ADR-071 record the contract. No new dependencies; no policy change.
- **After** (same T3:15/65):
  - default: 13 steps/1.0, 13 in-memory forecasts (Brier 0.230769), `file_before=false`, no journal.
  - logged: 13 steps/1.0, 13 persisted records/13 resolved, Brier 0.230769, skill -2.25, one prefix, ids unique and header-matched, verification ok.
  - two runs: first 13 + second 6 = 19 records/19 resolved, two prefixes, Brier 0.223684, skill -1.375, second run 6 steps/1.0; all ids unique and each slice matches its header prefix.
  - missing self-model: ValueError, no log and no journal; corrupt store: ValueError after a `done` verdict with `steps=13 reward=1.0`; actions: logged equals default, 13 steps/1.0.
  - behavior, standing 466/240/217, T1 0-99 1581, holdout 1581/800/738, fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0, progress guard/skip, Merkle journal, claim store, calibration journal, keyed telemetry, prompt budget, execution budget, resume identity, workspace binding, snapshot diff/digest, calibration, claims and the 200k tail-read bound unchanged; 314 tests OK; policy unchanged.
- **Ablation** (same T3:15):
  - `calibration_path=None`: the 13 forecasts exist only in memory, `file_before=false`/no file; the logged run persists 13/13. The cross-run evidence dies without the bridge.
  - per-run slicing: the same Agent/SelfModel runs T3:15 then T3:65; the second append contains only 6 records (19 total), not all 19 again.
- **Verdict**: evidence-integration extension. Actions and rewards are unchanged; the measured deltas are 13 persisted forecasts with in-memory-identical Brier, a 19-record two-run aggregate, and loud missing/corrupt failures. No action or emergence claim.
- **Gates**: unittest 314/314 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_calibration_bridge.TestCalibrationBridge.test_selfmodel_forecasts_prefix_and_slice -v` -> before: AttributeError (`forecast_count`); after: OK.
  - `python -m unittest tests.test_calibration_bridge -v` -> 8 OK.
  - `python -m evals.calibration_bridge` -> default 13 in-memory/no file; logged 13/13 Brier 0.230769; two runs 19/19 Brier 0.223684; missing/corrupt errors; actions match.
  - `python -m unittest discover -s tests -t .` -> 314 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 78**: unittest 314 OK; aikit 5/5; bridge default 13 in-memory/no file; logged 13/13 Brier 0.230769/skill -2.25; two runs 19/19 Brier 0.223684/skill -1.375, two prefixes; missing self-model no log/store; corrupt store done verdict + error; actions match; policy 7812e532...; calibration journal first-run 6/6 0.185/0.26; aggregated 10/10 0.129/0.484; duplicate refused; tamper/corrupt/missing/stale/fresh lock; claim store 6/6 + backup 3/3; progress skip-on T3:15 13/4/3, T3:65 6/4/3, T2:3 8/3/3, T1:71 36/22/0; guard-on 13/13/12, 6/6/5, 8/8/8, 36/22/0; guard-off 33/21, 26/21, 34/21, 36/22; Merkle journal 2 anchors 16-24/24-32, both proofs, truncated 2:32>30, deleted prev, tampered root-mismatch:2, rollback refused, missing, single-anchor history lost; claims 3 supported/2 refuted/1 inconclusive; calibration perfect 0/1, calibrated 0.166, inverted 1/-3, T3 Brier 0.230769; recapture graph/content stable vs changed; meta intact/tampered/missing; snapshot diff same/volatile empty; workspace stable/change/default null; episode resume/new/ask; budget 13/1.0 and caps; Merkle anchor 8-record proof 3; prompt 63->52/13; keyed 8/8 MACs; anchor journal 2 seq 11/16; single anchor 4/4; 200k head lookup <120 ms (0.764); standing 466/240/217; T1 0-99 1581; holdout 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; multi 9/16/11/13/14 blind 9/200/200/200/200; three 15/12/10/13/19 blind 200/200/10/200/200; trust 16/8/13/6; escape 19/18; cold-start 16/8/13/6; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 78 - Merkle journal compaction into a union-root anchor (fresh gap audit)

- **Baseline** (commit 87be3d5, cycle 77; same 24-record three-batch journal):
  - canonical gate: 314 tests OK; aikit check 5/5; policy 7812e53251f1711d9eb50104eacbef8e4223e65ee574cbb8c4e8e07773b5550f.
  - `.merkle.journal` appended one anchor per batch (0-8, 8-16, 16-24), so the journal grew without bound; deleting older anchors would lose their proofs.
- **Gap**: no bounded compaction that preserves membership. Merging all anchors into one union root keeps every record provable while reducing the journal to one line.
- **Target delta**: compact 3 anchors (0-24) to 1 anchor; proofs for records 0, 12 and 23 still verify; copy leaves the 3-anchor source untouched; replace leaves 1 live anchor plus a 3-anchor `.bak`; a 2-anchor 8-24 union rejects record 0; missing/truncated journals are refused.
- **Falsifier**: a proof that verified before compaction fails after it; the source is modified by copy; replace loses the original; the union range/root is wrong; a truncated journal is accepted; behavior/pins move.
- **Change**: telemetry/merkle.py adds `compact_merkle_journal(log_path, journal_path=None, output_path=None, replace=False, created_at=None)` plus atomic `_write_journal_record`/`_write_meta` helpers and a stdlib `shutil` import. The function validates the journal/anchors, computes one root over `min(start)..max(end)`, writes `<journal>.compact` by default, and with `replace=True` writes a temp compact line, copies the source to `.bak`, replaces the live journal and refuses a different `output_path`. A `.compaction` sidecar records source anchors/head, union range and compacted hash. tests/test_merkle_compaction.py covers copy, replace/backup, missing, truncated, same-output, invalid replace, outside-union proof and metadata; evals/merkle_compaction.py measures copy/replace/proofs/missing/truncated/outside. README and ADR-072 record the contract. No agent behavior or policy change.
- **After** (same 24-record journal):
  - copy: source 3 anchors/3 lines, compact 1 anchor/1 line, start 0/end 24/count 24, original still 3 anchors and verifies, proofs [0,12,23] all true, metadata present.
  - replace: live 1 anchor, `.bak` 3 anchors, both verify, replaced true, metadata present, no `.tmp`, live proof 12 true.
  - outside: 2 anchors 8-24 compact to 1; proof for record 0 raises `record index is outside every merkle batch`; compact verifies.
  - missing: `merkle journal is invalid: missing-journal`; truncated to 20: `truncated-batch:24>20`.
  - behavior, standing 466/240/217, T1 0-99 1581, holdout 1581/800/738, fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0, progress guard/skip, Merkle journal/anchor, claim store, calibration journal/bridge, keyed telemetry, prompt budget, execution budget, resume identity, workspace binding, snapshot diff/digest, calibration, claims and the 200k tail-read bound unchanged; 322 tests OK; policy unchanged.
- **Ablation** (same journal):
  - copy vs replace: copy proves the union without touching the source; replace proves it and keeps the original as `.bak`. Without compaction, the 3-anchor journal remains 3 lines.
  - union boundary: proofs inside 0-24 verify; a record outside the 8-24 union is rejected. Compaction proves membership in the union, not the original batch boundaries.
- **Verdict**: evidence-retention extension. Behavior is unchanged; the measured deltas are 3 anchors -> 1 union root with 3/3 proofs, a verified 3-anchor backup on replace, and named missing/truncated/outside findings. No action or emergence claim.
- **Gates**: unittest 322/322 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_merkle_compaction.TestMerkleCompaction.test_copy_merges_three_batches_and_keeps_original -v` -> before: ImportError (`compact_merkle_journal`); after: OK.
  - `python -m unittest tests.test_merkle_compaction -v` -> 8 OK.
  - `python -m evals.merkle_compaction` -> copy/replace 3->1 with 3/3 proofs, backup 3, outside 8-24 rejected, missing/truncated errors.
  - `python -m unittest discover -s tests -t .` -> 322 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 79**: unittest 322 OK; aikit 5/5; Merkle compaction copy 3->1 0-24 with 3/3 proofs, source 3; replace live 1/backup 3; outside 8-24 proof 0 rejected; missing/truncated errors; policy 7812e532...; bridge default 13 in-memory/no file; logged 13/13 Brier 0.230769/skill -2.25; two runs 19/19 Brier 0.223684 two prefixes; calibration journal first-run 6/6 0.185/0.26; aggregated 10/10 0.129/0.484; duplicate refused; tamper/corrupt/missing/stale/fresh lock; claim store 6/6 + backup 3/3; progress skip-on T3:15 13/4/3, T3:65 6/4/3, T2:3 8/3/3, T1:71 36/22/0; guard-on 13/13/12, 6/6/5, 8/8/8, 36/22/0; guard-off 33/21, 26/21, 34/21, 36/22; Merkle journal 2 anchors 16-24/24-32, both proofs, truncated 2:32>30, deleted prev, tampered root-mismatch:2, rollback refused, missing, single-anchor history lost; claims 3 supported/2 refuted/1 inconclusive; calibration perfect 0/1, calibrated 0.166, inverted 1/-3, T3 Brier 0.230769; recapture graph/content stable vs changed; meta intact/tampered/missing; snapshot diff same/volatile empty; workspace stable/change/default null; episode resume/new/ask; budget 13/1.0 and caps; Merkle anchor 8-record proof 3; prompt 63->52/13; keyed 8/8 MACs; anchor journal 2 seq 11/16; single anchor 4/4; 200k head lookup <120 ms (0.764); standing 466/240/217; T1 0-99 1581; holdout 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; multi 9/16/11/13/14 blind 9/200/200/200/200; three 15/12/10/13/19 blind 200/200/10/200/200; trust 16/8/13/6; escape 19/18; cold-start 16/8/13/6; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 79 - pure rule-path confidence readout from BFS move ties (fresh gap audit)

- **Baseline** (commit 4fa8b8d, cycle 78; same nine pin seeds):
  - canonical gate: 322 tests OK; aikit check 5/5; policy 7812e53251f1711d9eb50104eacbef8e4223e65ee574cbb8c4e8e07773b5550f.
  - the probe carried dead-pool/cycle facts but no statement of rule-action ambiguity; planning certainty was unmeasured.
- **Gap**: no per-step confidence/uncertainty readout. A pure count of equally best free moves gives local rule certainty without changing the action.
- **Target delta**: `probe.rule` carries goal/distance/ties/confidence/rule_distance/optimal; unique moves 1.0, two-way ties 0.5, collect at goal 1.0; `rule_readout=False` removes the field; on/off traces have identical actions/steps/rewards.
- **Falsifier**: the readout changes an action/step/reward; a unique move reads <1.0; a tie reads 1.0; collect at goal is not full confidence; the off switch leaves the field; policy/pins move.
- **Change**: agent.py adds `_rule_confidence(pos, goal, obstacles, action)`, `Planner(rule_readout=True)`, `probe["rule"]` and `PLANNER_POLICY["rule_readout"] = "bfs-move-ties"`. The readout uses the fixed target or the first tour cell; it records the best post-move BFS distance, ties, 1/ties, the rule action's distance and local optimality. `rule_readout=False` skips it; it never selects an action. tests/test_rule_confidence.py covers unique/tie/collect/item/no-goal/off/action-parity/invalid/policy; evals/rule_confidence.py measures on/off/seeds/unique/tie/collect. README and ADR-073 record the contract. No new dependencies.
- **After** (same nine pin seeds):
  - on: 89 steps/11.0 reward, actions match off, 89/89 readouts, 28 ambiguous (61 unique, 28 two-way ties), 0 non-optimal.
  - per-seed ambiguous: T1:71 5, T2:3 0, T3:15 6, T3:65 2, T3:74 5, T3:202 1, T3:272 7, T3:307 0, T3:479 2.
  - off: 89 steps/11.0, 0 readouts; unique reads 1.0; two-way tie reads 0.5/distance 3; collect reads 1.0/distance 0.
  - behavior, standing 466/240/217, T1 0-99 1581, holdout 1581/800/738, fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0, progress guard/skip, Merkle journal/compaction, claim store, calibration journal/bridge, keyed telemetry, prompt budget, execution budget, resume identity, workspace binding, snapshot diff/digest, calibration, claims and the 200k tail-read bound unchanged; 334 tests OK.
  - policy key added: `policy_digest` is now decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010 (was 7812e532...).
- **Ablation** (same seeds):
  - `rule_readout=False`: the traces are identical (89/11.0, same actions) and the `rule` field disappears; the readout property dies with the switch.
  - local-only boundary: `optimal` is local BFS minimality; a two-way tie is ambiguous even though both moves are optimal; T1 multi-item ordering ambiguity is not measured.
- **Verdict**: measurement extension. Behavior is unchanged; the measured delta is 89 readouts with 28 two-way ties and 0 non-optimal rule steps, plus exact synthetic fixtures. No action or emergence claim.
- **Gates**: unittest 334/334 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_rule_confidence.TestRuleConfidence.test_unique_move_has_full_confidence -v` -> before: KeyError ('rule'); after: OK.
  - `python -m unittest tests.test_rule_confidence -v` -> 12 OK.
  - `python -m evals.rule_confidence` -> on 89/89, 28 ties, off 0; actions match; unique/tie/collect fixtures.
  - `python -m unittest discover -s tests -t .` -> 334 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 80**: unittest 334 OK; aikit 5/5; rule readout on 89/89, 28 ambiguous, 0 non-optimal, ties 61/28; off 0 readouts with identical 89/11.0; unique 1.0, tie 0.5, collect 1.0; policy decbfce3...; Merkle compaction copy 3->1 0-24 with 3/3 proofs/replace backup 3; bridge default 13 in-memory/no file; logged 13/13 Brier 0.230769; two runs 19/19 0.223684; calibration journal 6/6 0.185/0.26 and 10/10 0.129/0.484; claim store 6/6 + backup 3/3; progress skip-on T3:15 13/4/3, T3:65 6/4/3, T2:3 8/3/3, T1:71 36/22/0; guard-on 13/13/12, 6/6/5, 8/8/8, 36/22/0; guard-off 33/21, 26/21, 34/21, 36/22; Merkle journal 2 anchors 16-24/24-32; claims 3/2/1; calibration perfect 0/1, calibrated 0.166, inverted 1/-3, T3 Brier 0.230769; recapture graph/content stable vs changed; meta intact/tampered/missing; snapshot diff same/volatile empty; workspace stable/change/default null; episode resume/new/ask; budget 13/1.0 and caps; Merkle anchor 8-record proof 3; prompt 63->52/13; keyed 8/8 MACs; anchor journal 2 seq 11/16; single anchor 4/4; 200k head lookup <120 ms (0.764); standing 466/240/217; T1 0-99 1581; holdout 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; multi 9/16/11/13/14 blind 9/200/200/200/200; three 15/12/10/13/19 blind 200/200/10/200/200; trust 16/8/13/6; escape 19/18; cold-start 16/8/13/6; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 80 - lossless calibration-journal rotation with archive and backup (fresh gap audit)

- **Baseline** (commit 4abc3ec, cycle 79; same 19-forecast journal):
  - canonical gate: 334 tests OK; aikit check 5/5; policy decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - the calibration journal appended one checksummed line per forecast with no retention; pruning would discard evidence.
- **Gap**: no bounded live journal that preserves older forecasts. Rotation can keep the newest N live, archive the older records and preserve the combined Brier/skill.
- **Target delta**: 19 records rotate to 10 live + 9 archived with identical Brier 0.181579/skill 0.255114; backup 19; second rotation 10 live + 15 archived = 25; short/missing no-op; conflicting ids, corrupt files and fresh locks refused.
- **Falsifier**: rotation changes the combined score or loses a record; a duplicate id is accepted; a short journal creates files; a backup is missing; conflict/corrupt/lock cases pass silently.
- **Change**: calibration_store.py adds `_write_records_atomic`, `_write_json_atomic`, `_backup_file`, `load_all_forecasts` and `rotate_forecast_journal`. Rotation validates live/archive, moves older records to `.archive` idempotently by id, keeps the newest N live, copies the pre-rotation journal to `.bak`, writes a `.rotation` sidecar with counts and last checksums, and holds the existing writer lock. `load_all_forecasts` concatenates archive+live and rejects duplicate ids, preserving order and score. tests/test_calibration_retention.py covers split/score, second rotation, no-op, conflict, corrupt, missing, invalid parameters, stale/fresh lock; evals/calibration_retention.py measures before/rotate/all/second/noop/conflict/missing/lock. README and ADR-074 record the contract. No agent behavior or policy change.
- **After** (same 19-forecast journal):
  - before: 19 live, 0 archive, Brier 0.181579/skill 0.255114.
  - rotate: 10 live/9 archive/19 total, same Brier/skill, 19-record backup, metadata present, unique ids, live/archive verify.
  - all: combined load 19, same score; second rotation after 6 new records: 16 -> 10 live/15 archive/25 total, backup 16, unique ids, combined Brier 0.198/skill 0.196429.
  - noop: 5 live/10 keep -> rotated false, no archive/backup/metadata; missing -> rotated false/0; conflict `archive id 'run1:0' conflicts with a different record`; fresh lock -> TimeoutError with live unchanged.
  - behavior, standing 466/240/217, T1 0-99 1581, holdout 1581/800/738, fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0, rule readout, progress guard/skip, Merkle journal/compaction, claim store, calibration journal/bridge, keyed telemetry, prompt budget, execution budget, resume identity, workspace binding, snapshot diff/digest, calibration, claims and the 200k tail-read bound unchanged; 343 tests OK; policy unchanged.
- **Ablation** (same journal):
  - before vs rotate: 19 live/0 archive vs 10 live/9 archive/19 total with identical Brier/skill; the live file is bounded without losing evidence.
  - short journal: 5 <= 10 is a no-op with no archive/backup/metadata, so retention never runs without a reason.
- **Verdict**: evidence-retention extension. Behavior and scores are unchanged; the measured deltas are a bounded live journal (19 -> 10), a lossless 9-record archive and 19-record backup, and named conflict/lock/missing cases. No action or emergence claim.
- **Gates**: unittest 343/343 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_calibration_retention.TestCalibrationRetention.test_rotate_splits_and_preserves_score -v` -> before: ImportError (`load_all_forecasts`); after: OK.
  - `python -m unittest tests.test_calibration_retention -v` -> 9 OK.
  - `python -m evals.calibration_retention` -> rotate 10/9/19 same 0.181579/0.255114; second 10/15/25; noop/conflict/missing/lock as above.
  - `python -m unittest discover -s tests -t .` -> 343 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 81**: unittest 343 OK; aikit 5/5; retention rotate 10 live/9 archive/19 total, same Brier 0.181579/skill 0.255114, backup 19; second 10/15/25 Brier 0.198; noop 5/0; conflict/lock/missing; policy decbfce3...; rule readout 89/89, 28 ambiguous; rule readout off 0; Merkle compaction 3->1 0-24 with 3/3 proofs; bridge default 13 in-memory/no file; logged 13/13 Brier 0.230769; two runs 19/19 0.223684; calibration journal 6/6 0.185/0.26 and 10/10 0.129/0.484; claim store 6/6 + backup 3/3; progress skip-on T3:15 13/4/3, T3:65 6/4/3, T2:3 8/3/3, T1:71 36/22/0; guard-on 13/13/12, 6/6/5, 8/8/8, 36/22/0; guard-off 33/21, 26/21, 34/21, 36/22; Merkle journal 2 anchors 16-24/24-32; claims 3/2/1; calibration perfect 0/1, calibrated 0.166, inverted 1/-3, T3 Brier 0.230769; recapture graph/content stable vs changed; meta intact/tampered/missing; snapshot diff same/volatile empty; workspace stable/change/default null; episode resume/new/ask; budget 13/1.0 and caps; Merkle anchor 8-record proof 3; prompt 63->52/13; keyed 8/8 MACs; anchor journal 2 seq 11/16; single anchor 4/4; 200k head lookup <120 ms (0.764); standing 466/240/217; T1 0-99 1581; holdout 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; multi 9/16/11/13/14 blind 9/200/200/200/200; three 15/12/10/13/19 blind 200/200/10/200/200; trust 16/8/13/6; escape 19/18; cold-start 16/8/13/6; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 81 - opt-in automatic calibration retention at the logged-run bridge (fresh gap audit)

- **Baseline** (commit 1c1bdf6, cycle 80; same T3:15/65 runs):
  - canonical gate: 343 tests OK; aikit check 5/5; policy decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - the bridge appended every run's forecasts and left retention to a separate manual rotation.
- **Gap**: no automatic per-run threshold. A logged run can bound the live journal immediately after its append by reusing the tested archive rotation.
- **Target delta**: `run_task_logged(calibration_path=..., calibration_keep_recent=10)` leaves T3:15 at 10 live/3 archived/13 total with the same Brier 0.230769; a second run reaches 10/9/19 with 0.223684; no threshold keeps 13 live; missing path/invalid threshold fail before the run; a corrupt archive fails after the done verdict with all forecasts live.
- **Falsifier**: the threshold changes actions/steps/rewards or the combined score; a missing path/invalid threshold creates a log; a corrupt archive loses the appended forecasts; no-threshold rotates; the backup/metadata are missing.
- **Change**: agent.py adds `calibration_keep_recent=None` to `run_task_logged`, validates it before the run, and after the forecast append calls `rotate_forecast_journal(calibration_path, keep_recent=...)`. The append happens first, so a rotation failure leaves all forecasts live and the verdict intact. tests/test_calibration_autoretention.py covers single/two-run/no-threshold/no-path/invalid/corrupt/actions/keep-one; evals/calibration_autoretention.py measures retained/two-run/unretained/missing-path/invalid/corrupt/actions. README and ADR-075 record the contract. No new dependencies; no policy change.
- **After** (same T3:15/65 runs):
  - retained T3:15: 13 steps/1.0, live 10/archive 3/total 13, Brier 0.230769/skill -2.25, backup 13, rotation metadata, one prefix, unique ids; actions match the rule trace.
  - retained two runs: 10 live/9 archive/19 total, Brier 0.223684/skill -1.375, backup 16, two prefixes; second run 6 steps/1.0.
  - unretained: 13 live/0 archive/13 total, Brier 0.230769, no backup/rotation; missing path and invalid threshold fail before the log; corrupt archive: `calibration archive is invalid: line 1: invalid JSON`, done verdict, live 13; action parity true.
  - behavior, standing 466/240/217, T1 0-99 1581, holdout 1581/800/738, fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0, rule readout, progress guard/skip, Merkle journal/compaction, claim store, calibration journal/bridge, keyed telemetry, prompt budget, execution budget, resume identity, workspace binding, snapshot diff/digest, calibration, claims and the 200k tail-read bound unchanged; 351 tests OK; policy unchanged.
- **Ablation** (same T3:15):
  - `calibration_keep_recent=None`: 13 live/0 archive, no backup/rotation, same Brier; the retained run bounds the live file to 10 with a 3-record archive. The automatic property dies with the threshold.
  - corrupt archive: the append succeeds first (13 live), then rotation raises; no forecast is lost, but the run reports the failure after the done verdict.
- **Verdict**: evidence-retention integration. Actions, steps, rewards and the combined score are unchanged; the measured deltas are 10 live/3 archived for one run, 10/9 for two, and named no-path/invalid/corrupt failures. No action or emergence claim.
- **Gates**: unittest 351/351 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_calibration_autoretention.TestCalibrationAutoRetention.test_single_run_retains_ten -v` -> before: TypeError (`calibration_keep_recent`); after: OK.
  - `python -m unittest tests.test_calibration_autoretention -v` -> 8 OK.
  - `python -m evals.calibration_autoretention` -> retained 10/3/13 0.230769; two 10/9/19 0.223684; unretained 13; errors and action parity.
  - `python -m unittest discover -s tests -t .` -> 351 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 82**: unittest 351 OK; aikit 5/5; auto-retention retained 10/3/13 Brier 0.230769, two 10/9/19 0.223684, unretained 13; policy decbfce3...; retention rotate 10/9/19 same 0.181579/0.255114; second 10/15/25; rule readout 89/89/28; readout off 0; Merkle compaction 3->1 0-24 3/3 proofs; bridge default 13 in-memory/no file, logged 13/13 0.230769; calibration journal 6/6 0.185/0.26 and 10/10 0.129/0.484; claim store 6/6 + backup 3/3; progress skip-on T3:15 13/4/3, T3:65 6/4/3, T2:3 8/3/3, T1:71 36/22/0; guard-on 13/13/12, 6/6/5, 8/8/8, 36/22/0; guard-off 33/21, 26/21, 34/21, 36/22; Merkle journal 2 anchors 16-24/24-32; claims 3/2/1; calibration perfect 0/1, calibrated 0.166, inverted 1/-3, T3 Brier 0.230769; recapture graph/content stable vs changed; meta intact/tampered/missing; snapshot diff same/volatile empty; workspace stable/change/default null; episode resume/new/ask; budget 13/1.0 and caps; Merkle anchor 8-record proof 3; prompt 63->52/13; keyed 8/8 MACs; anchor journal 2 seq 11/16; single anchor 4/4; 200k head lookup <120 ms (0.764); standing 466/240/217; T1 0-99 1581; holdout 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; multi 9/16/11/13/14 blind 9/200/200/200/200; three 15/12/10/13/19 blind 200/200/10/200/200; trust 16/8/13/6; escape 19/18; cold-start 16/8/13/6; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 82 - atomic append+retention threshold in the calibration store (fresh gap audit)

- **Baseline** (commit 4521d13, cycle 81; same 19-forecast journal):
  - canonical gate: 351 tests OK; aikit check 5/5; policy decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - the bridge appended forecasts and then called rotate_forecast_journal as two lock acquisitions, leaving the ADR-075 interleaving boundary.
- **Gap**: no store-level atomic append+retention. `append_forecasts(keep_recent=...)` can append and rotate under one lock, making retention available to every caller.
- **Target delta**: one append of 19 with keep_recent=10 leaves 10 live/9 archived/19 total with the same Brier 0.181579/skill 0.255114, a 19-record backup and rotation metadata; incremental 10+9 reaches the same state; 5 under the limit is a no-op; a corrupt archive keeps the appended 19 live and raises.
- **Falsifier**: the threshold changes the combined score or loses records; a short append creates archive/backup; a corrupt archive discards the new records; the bridge results/actions change.
- **Change**: calibration_store.py extracts `_rotate_locked(target, archive, keep_recent)` and keeps `rotate_forecast_journal` as the manual lock-taking wrapper. `append_forecasts` gains `keep_recent=None`; it validates the threshold before writing, appends under the writer lock, then calls `_rotate_locked` under the same lock when set, and reports `rotated/live/archived/backup/metadata` while keeping `records/resolved/appended` pre-rotation. agent.py passes `calibration_keep_recent` directly to append_forecasts instead of a second rotate call. tests/test_calibration_retention.py adds five store-level threshold tests; evals/calibration_retention.py adds append/append-noop. README and ADR-076 record the contract. No new dependencies; no policy change.
- **After** (same 19-forecast journal):
  - append keep 10: report rotated true, records 19, live 10, archived 9; live/archive/total 10/9/19; before/after Brier 0.181579/skill 0.255114; backup 19; metadata present; unique ids.
  - incremental 10 then 9 with keep 10: first no-op 10 live, second 10 live/9 archive/19 total; no duplicates.
  - append-noop 5: rotated false, records/live 5, no archive/backup/metadata.
  - corrupt archive: append writes 19 live, rotation raises; live 19, archive unchanged. Bridge retained 10/3/13 and two-run 10/9/19; actions unchanged.
  - behavior, standing 466/240/217, T1 0-99 1581, holdout 1581/800/738, fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0, rule readout, progress guard/skip, Merkle journal/compaction, claim store, calibration journal/bridge, keyed telemetry, prompt budget, execution budget, resume identity, workspace binding, snapshot diff/digest, calibration, claims and the 200k tail-read bound unchanged; 356 tests OK; policy unchanged.
- **Ablation** (same journal):
  - keep_recent=None: 19 live/0 archive, no backup/rotation; keep 10: 10 live/9 archive with the same score. The atomic retention dies with the threshold.
  - incremental vs one-shot: both reach 10/9/19 without duplicates; the threshold is idempotent across appends.
- **Verdict**: evidence-retention integration. Actions, steps, rewards and scores are unchanged; the measured deltas are the single-lock 10/9/19 state, a 19-record backup, and a no-op under the limit. No action or emergence claim.
- **Gates**: unittest 356/356 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_calibration_retention.TestCalibrationRetention.test_append_with_threshold_rotates -v` -> before: TypeError (`keep_recent`); after: OK.
  - `python -m unittest tests.test_calibration_retention tests.test_calibration_autoretention` -> 22 OK.
  - `python -m evals.calibration_retention` -> append 10/9/19 same 0.181579/0.255114, backup 19; append-noop 5; rotate/second/noop/conflict/missing/lock unchanged.
  - `python -m unittest discover -s tests -t .` -> 356 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 83**: unittest 356 OK; aikit 5/5; store append 10/9/19 Brier 0.181579/skill 0.255114, backup 19; append-noop 5; incremental 10+9; corrupt keeps 19; bridge retained 10/3/13 0.230769, two 10/9/19 0.223684; policy decbfce3...; rule readout 89/89/28; Merkle compaction 3->1 0-24 3/3 proofs; calibration journal 6/6 0.185/0.26 and 10/10 0.129/0.484; claim store 6/6 + backup 3/3; progress skip-on T3:15 13/4/3, T3:65 6/4/3, T2:3 8/3/3, T1:71 36/22/0; guard-on 13/13/12, 6/6/5, 8/8/8, 36/22/0; guard-off 33/21, 26/21, 34/21, 36/22; Merkle journal 2 anchors 16-24/24-32; claims 3/2/1; calibration perfect 0/1, calibrated 0.166, inverted 1/-3, T3 Brier 0.230769; recapture graph/content stable vs changed; meta intact/tampered/missing; snapshot diff same/volatile empty; workspace stable/change/default null; episode resume/new/ask; budget 13/1.0 and caps; Merkle anchor 8-record proof 3; prompt 63->52/13; keyed 8/8 MACs; anchor journal 2 seq 11/16; single anchor 4/4; 200k head lookup <120 ms (0.764); standing 466/240/217; T1 0-99 1581; holdout 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; multi 9/16/11/13/14 blind 9/200/200/200/200; three 15/12/10/13/19 blind 200/200/10/200/200; trust 16/8/13/6; escape 19/18; cold-start 16/8/13/6; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 83 - readout-only tie-break audit via alternatives and visit counts (fresh gap audit)

- **Baseline** (commit ab156df, cycle 82; same nine pin seeds):
  - canonical gate: 356 tests OK; aikit check 5/5; policy decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - the rule readout reported tie count/confidence but not which moves were tied or how visits influenced the choice; a behavior-changing tie-break experiment had no evidence base.
- **Gap**: no per-step listing of tied alternatives/visits. Extend the readout, not the action, and measure whether the current tie-break is already least-visited.
- **Target delta**: `probe.rule.alternatives` lists each best move with distance/visits; 89/89 readouts, 113 alternatives, 28 tie steps, 1 visit-spread tie, 28 least-visited, 0 non-least/non-alternative; unique/tie/collect fixtures; on/off actions unchanged.
- **Falsifier**: alternatives change an action/step/reward; a unique move lists >1; a tie lists the wrong moves; visits are wrong; the audit finds a non-least choice it cannot explain; policy/pins move.
- **Change**: agent.py extends `_rule_confidence(pos, goal, obstacles, action, visits=None)` with `alternatives` (action/distance/visits) and passes the planner's `visits` dict; collect/wait read an empty list. Action selection is untouched; `rule_readout=False` removes the field. tests/test_rule_confidence.py adds five alternatives tests; evals/rule_confidence.py adds alternatives/tie/spread/least/not-least/not-in counts per seed and aggregate. README and ADR-077 record the audit. No new dependencies; no policy key or digest change.
- **After** (same nine pin seeds):
  - on: 89 steps/11.0, actions match off, 89/89 readouts, 113 alternatives, 28 tie steps, 1 visit-spread step, 28 chosen least-visited, 0 not-least, 0 not-in.
  - per-seed ties: T1:71 5 (1 spread), T2:3 0, T3:15 6, T3:65 2, T3:74 5, T3:202 1, T3:272 7, T3:307 0, T3:479 2; all chosen alternatives are least-visited.
  - fixtures: unique one alternative distance 1; [0,0]->[2,2] tie alternatives down/right at distance 3/visits 0; collect empty.
  - off: 89/11.0, 0 readouts/alternatives; behavior, standing 466/240/217, T1 0-99 1581, holdout 1581/800/738, fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0, progress guard/skip, Merkle journal/compaction, claim store, calibration journal/bridge/retention, keyed telemetry, prompt budget, execution budget, resume identity, workspace binding, snapshot diff/digest, calibration, claims and the 200k tail-read bound unchanged; 361 tests OK; policy unchanged.
- **Ablation** (same seeds):
  - `rule_readout=False`: 0 alternatives/readouts with identical 89/11.0 traces; the audit property dies with the switch.
  - no tie-break change was made: with 27/28 ties at equal visits, the axis order decides; the single visit-spread case already chooses least-visited. A behavior change is not justified by this audit.
- **Verdict**: measurement/audit extension. Behavior is unchanged; the measured deltas are the alternatives/visit facts and the finding that the current tie-break is already least-visited in every observed tie. No action or emergence claim.
- **Gates**: unittest 361/361 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_rule_confidence.TestRuleConfidence.test_tie_alternatives_are_listed -v` -> before: KeyError ('alternatives'); after: OK.
  - `python -m unittest tests.test_rule_confidence -v` -> 17 OK.
  - `python -m evals.rule_confidence` -> on 89/89, alts 113, ties 28, spread 1, least 28, not-least 0; off 0; fixtures.
  - `python -m unittest discover -s tests -t .` -> 361 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 84**: unittest 361 OK; aikit 5/5; tie audit on 89/89, alts 113, ties 28, spread 1, least 28, not-least 0; off 0; unique 1/tie 2/collect 0; policy decbfce3...; store append 10/9/19 0.181579/0.255114; bridge retained 10/3/13 0.230769 and two 10/9/19 0.223684; calibration journal 6/6 0.185/0.26 and 10/10 0.129/0.484; claim store 6/6 + backup 3/3; progress skip-on T3:15 13/4/3, T3:65 6/4/3, T2:3 8/3/3, T1:71 36/22/0; guard-on 13/13/12, 6/6/5, 8/8/8, 36/22/0; guard-off 33/21, 26/21, 34/21, 36/22; Merkle journal 2 anchors 16-24/24-32; Merkle compaction 3->1 0-24 3/3 proofs; claims 3/2/1; calibration perfect 0/1, calibrated 0.166, inverted 1/-3, T3 Brier 0.230769; recapture graph/content stable vs changed; meta intact/tampered/missing; snapshot diff same/volatile empty; workspace stable/change/default null; episode resume/new/ask; budget 13/1.0 and caps; Merkle anchor 8-record proof 3; prompt 63->52/13; keyed 8/8 MACs; anchor journal 2 seq 11/16; single anchor 4/4; 200k head lookup <120 ms (0.764); standing 466/240/217; T1 0-99 1581; holdout 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; multi 9/16/11/13/14 blind 9/200/200/200/200; three 15/12/10/13/19 blind 200/200/10/200/200; trust 16/8/13/6; escape 19/18; cold-start 16/8/13/6; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 84 - readout-only multi-item tour-order audit (fresh gap audit)

- **Baseline** (commit 5bc6384, cycle 83; same nine pin seeds):
  - canonical gate: 361 tests OK; aikit check 5/5; policy decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - `_first_of_best_tour` exhaustively picked a shortest Manhattan item tour with lexicographic ties, but the probe did not expose tied first items or tour optimality; the cycle-83 audit covered move ties only.
- **Gap**: no multi-item tour-order readout. Add a readout-only audit of first-item ties so a future item-order experiment has evidence without changing actions.
- **Target delta**: `probe.tour` lists sorted items/chosen/best_length/chosen_length/tied_firsts/tie_count/optimal on T1 movement; T1:71 has 13 tour steps, 0 first-item ties and 13 optimal; a synthetic two-item tie has two tied firsts and still chooses a shortest tour; `rule_readout=False` removes the field.
- **Falsifier**: the audit changes an action/step/reward; a first-item tie is missed; a non-optimal choice is reported optimal; T3/collect gets a tour field; policy/pins move.
- **Change**: agent.py adds `_tour_audit(pos, cells)` and attaches `probe["tour"]` on T1 movement steps under `rule_readout`. The audit reuses the exhaustive Manhattan permutation semantics: per-first minimum length, global best, tied firsts, chosen/optimal. Action selection is untouched. tests/test_rule_confidence.py adds eight tour tests; evals/rule_confidence.py adds a `tour` fixture and per-seed/aggregate tour counts. README and ADR-078 record the audit. No new dependencies; no policy key or digest change.
- **After** (same nine pin seeds):
  - on: 89 steps/11.0, actions match off; 13 T1:71 tour steps, 0 tour ties, 13/13 optimal, 0 extra tied firsts.
  - synthetic tour `[0,0]` with items `[1,0]`/`[0,1]`: chosen `[0,1]`, best/chosen length 3, tied firsts `[[0,1],[1,0]]`, tie_count 2, optimal true.
  - off: 0 tour fields/readouts; unique/tie/collect fixtures unchanged; actions match.
  - behavior, standing 466/240/217, T1 0-99 1581, holdout 1581/800/738, fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0, progress guard/skip, Merkle journal/compaction, claim store, calibration journal/bridge/retention, keyed telemetry, prompt budget, execution budget, resume identity, workspace binding, snapshot diff/digest, calibration, claims and the 200k tail-read bound unchanged; 369 tests OK; policy unchanged.
- **Ablation** (same seeds):
  - `rule_readout=False`: the 13 tour fields disappear and actions/steps/rewards are unchanged; the audit property dies with the switch.
  - no item-order change was made: T1:71 has no first-item ties, so the pin seed provides no evidence for a behavior change; the synthetic tie documents the lexicographic rule.
- **Verdict**: measurement/audit extension. Behavior is unchanged; the measured delta is the 13-step tour audit with zero ties/13 optimal plus the synthetic tie fixture. No action or emergence claim.
- **Gates**: unittest 369/369 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_rule_confidence.TestRuleConfidence.test_tour_audit_two_way_tie -v` -> before: KeyError ('tour'); after: OK.
  - `python -m unittest tests.test_rule_confidence -v` -> 25 OK.
  - `python -m evals.rule_confidence` -> on 89/89, 113 alts, 28 move ties, 13 tour steps/0 ties/13 optimal; off 0; tour fixture tie 2.
  - `python -m unittest discover -s tests -t .` -> 369 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 85**: unittest 369 OK; aikit 5/5; tour audit T1:71 13 steps/0 ties/13 optimal; synthetic tie 2; move audit 89/89, 113 alts, 28 ties, 1 spread, 28 least; off 0; policy decbfce3...; store append 10/9/19 0.181579/0.255114; bridge retained 10/3/13 0.230769 and two 10/9/19 0.223684; calibration journal 6/6 0.185/0.26 and 10/10 0.129/0.484; claim store 6/6 + backup 3/3; progress skip-on T3:15 13/4/3, T3:65 6/4/3, T2:3 8/3/3, T1:71 36/22/0; guard-on 13/13/12, 6/6/5, 8/8/8, 36/22/0; guard-off 33/21, 26/21, 34/21, 36/22; Merkle journal 2 anchors 16-24/24-32; Merkle compaction 3->1 0-24 3/3 proofs; claims 3/2/1; calibration perfect 0/1, calibrated 0.166, inverted 1/-3, T3 Brier 0.230769; recapture graph/content stable vs changed; meta intact/tampered/missing; snapshot diff same/volatile empty; workspace stable/change/default null; episode resume/new/ask; budget 13/1.0 and caps; Merkle anchor 8-record proof 3; prompt 63->52/13; keyed 8/8 MACs; anchor journal 2 seq 11/16; single anchor 4/4; 200k head lookup <120 ms (0.764); standing 466/240/217; T1 0-99 1581; holdout 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; multi 9/16/11/13/14 blind 9/200/200/200/200; three 15/12/10/13/19 blind 200/200/10/200/200; trust 16/8/13/6; escape 19/18; cold-start 16/8/13/6; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 85 - optional verdict ref cross-linking claims to logged episode evidence (fresh gap audit)

- **Baseline** (commit 7e28ac2, cycle 84; same T3:15/65 runs):
  - canonical gate: 369 tests OK; aikit check 5/5; policy decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - claims and verdicts carried free-text evidence only; a verdict could not cite the logged run/episode that produced it, although the header already stores episode_sha256.
- **Gap**: no claim/evidence cross-link. Add an optional verdict ref carrying the header episode digest, backward-compatibly.
- **Target delta**: a T3:15 supports verdict with the header episode ref survives claim-store save/load and matches the header; a second run keeps a distinct ref with two claims/verdicts; legacy payloads load ref None; invalid refs leave history unchanged.
- **Falsifier**: the ref is lost or altered by to_dict/from_dict or the store; legacy payloads fail; an invalid ref is accepted or mutates history; two runs share a ref; claim status changes.
- **Change**: claims.py adds `ref: str = None` to frozen `Verdict`, `_validate_ref`, ref handling in `record_verdict`/`ClaimLedger.record`, list-normalized `to_dict`, ref-aware `from_dict`, and verdict-ref validation. tests/test_claims.py adds five ref tests; tests/test_claims_store.py adds a store-ref roundtrip; tests/test_claim_evidence.py covers a logged episode ref, two distinct refs, legacy None and invalid refs; evals/claim_evidence.py measures single/two-runs/legacy/invalid. README and ADR-079 record the contract. No new dependencies; no agent behavior or policy change.
- **After** (same runs):
  - single: T3:15 13 steps, episode f934305889d4..., ref matches header, 1 claim/1 verdict, status supported, store ok.
  - two-runs: T3:65 episode 3622529ae9b8..., refs distinct, 2 claims/2 verdicts, store ok.
  - legacy: ref None, status supported; invalid: `verdict ref must be a non-empty string or None`, 0 verdicts, status proposed.
  - behavior, standing 466/240/217, T1 0-99 1581, holdout 1581/800/738, fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0, rule readout/tie/tour audits, progress guard/skip, Merkle journal/compaction, claim store, calibration journal/bridge/retention, keyed telemetry, prompt budget, execution budget, resume identity, workspace binding, snapshot diff/digest, calibration and the 200k tail-read bound unchanged; 379 tests OK; policy unchanged.
- **Ablation** (same claims):
  - no ref: the legacy verdict loads with ref None; adding the ref records the episode and survives the store. The provenance property dies without the ref.
  - invalid ref: rejected before the verdict is appended; the history stays unchanged.
- **Verdict**: evidence-traceability extension. Behavior and claim statuses are unchanged; the measured delta is a 64-hex episode ref that roundtrips through the frozen verdict, JSON and claim store, with two runs distinct and legacy None. No action or emergence claim.
- **Gates**: unittest 379/379 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_claims.TestClaims.test_verdict_ref_roundtrip -v` -> before: TypeError (`ref`); after: OK.
  - `python -m unittest tests.test_claims tests.test_claims_store tests.test_claim_evidence` -> 28 OK.
  - `python -m evals.claim_evidence` -> single ref match/1-1/store ok; two distinct refs/2-2; legacy None; invalid error.
  - `python -m unittest discover -s tests -t .` -> 379 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 86**: unittest 379 OK; aikit 5/5; claim ref T3:15 f9343058... match, two runs 3622529a... distinct, legacy None, invalid rejected; policy decbfce3...; tour audit 13/0/13; move audit 89/89/113/28/1/28; store append 10/9/19; bridge 10/3/13 and 10/9/19; calibration journal 6/6 0.185/0.26 and 10/10 0.129/0.484; claim store 6/6 + backup 3/3; progress skip-on T3:15 13/4/3, T3:65 6/4/3, T2:3 8/3/3, T1:71 36/22/0; guard-on 13/13/12, 6/6/5, 8/8/8, 36/22/0; guard-off 33/21, 26/21, 34/21, 36/22; Merkle journal 2 anchors 16-24/24-32; Merkle compaction 3->1 0-24 3/3 proofs; claims 3/2/1; calibration perfect 0/1, calibrated 0.166, inverted 1/-3, T3 Brier 0.230769; recapture graph/content stable vs changed; meta intact/tampered/missing; snapshot diff same/volatile empty; workspace stable/change/default null; episode resume/new/ask; budget 13/1.0 and caps; Merkle anchor 8-record proof 3; prompt 63->52/13; keyed 8/8 MACs; anchor journal 2 seq 11/16; single anchor 4/4; 200k head lookup <120 ms (0.764); standing 466/240/217; T1 0-99 1581; holdout 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; multi 9/16/11/13/14 blind 9/200/200/200/200; three 15/12/10/13/19 blind 200/200/10/200/200; trust 16/8/13/6; escape 19/18; cold-start 16/8/13/6; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 86 - read-only claim-ref verification against live log headers (fresh gap audit)

- **Baseline** (commit 2636170, cycle 85; same T3:15/65 runs):
  - canonical gate: 379 tests OK; aikit check 5/5; policy decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - verdict refs were caller-provided and unverified; nothing matched them to a real log header.
- **Gap**: no live-ref verifier. A read-only check can union header episode_sha256 values and report verified/unverified/unreferenced refs without touching claims.
- **Target delta**: two logs verify 2/2; one log leaves C2 unverified with an unknown-episode finding; a fabricated ref is 0/1; an unreferenced verdict is reported; the claim store verifies 2/2; no-header/missing-file logs fail clearly.
- **Falsifier**: a verified ref is rejected; a fabricated/missing ref passes; a headerless/missing log is accepted; the verifier writes or changes claims; any behavior/pin moves.
- **Change**: claims_verify.py adds `verify_claim_refs(ledger, log_paths)` and `verify_claim_store(store_path, log_paths)`. It normalizes one/many paths, requires each log to exist and carry at least one non-empty episode_sha256 header, unions episodes across logs and multiple headers, counts verified/unverified/unreferenced verdicts, and names unknown-episode findings. It writes nothing. tests/test_claim_ref_verify.py covers 2-log verification, missing-log, fabricated, unreferenced, missing path, no-header, malformed, multiple headers, store and invalid inputs; evals/claim_ref_verify.py measures verified/missing-log/fabricated/unreferenced/store/no-header/missing-file. README and ADR-080 record the contract. No new dependencies; no agent behavior or policy change.
- **After** (same runs):
  - verified: 2 claims/2 verdicts, 2 verified/0 unverified/0 unreferenced, 2 episodes, ok true.
  - missing-log: 1 verified/1 unverified, finding C2 verdict 0 reason unknown-episode; fabricated: 0/1 unverified; unreferenced: 0/0/1 ok true; store: 2/2 ok; no-header/missing-file: clear ValueErrors.
  - behavior, standing 466/240/217, T1 0-99 1581, holdout 1581/800/738, fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0, rule readout/tie/tour audits, progress guard/skip, Merkle journal/compaction, claim store, calibration journal/bridge/retention, keyed telemetry, prompt budget, execution budget, resume identity, workspace binding, snapshot diff/digest, calibration and the 200k tail-read bound unchanged; 389 tests OK; policy unchanged.
- **Ablation** (same claims):
  - one log vs two: the second run's ref is unverified when its log is omitted; adding the log verifies it. Unreferenced verdicts are counted but do not fail.
  - no signature check: a copied episode digest in a caller-supplied log would pass; the verifier proves membership in header episodes only.
- **Verdict**: evidence-traceability extension. Behavior is unchanged; the measured deltas are 2/2 verified refs, named missing/fabricated cases, and the store path. No action or emergence claim.
- **Gates**: unittest 389/389 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_claim_ref_verify.TestClaimRefVerifier.test_two_logs_verify_both_refs -v` -> before: ModuleNotFoundError (`claims_verify`); after: OK.
  - `python -m unittest tests.test_claim_ref_verify -v` -> 10 OK.
  - `python -m evals.claim_ref_verify` -> verified 2/2, missing-log 1/1, fabricated 0/1, unreferenced 1, store 2/2, no-header/missing-file errors.
  - `python -m unittest discover -s tests -t .` -> 389 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 87**: unittest 389 OK; aikit 5/5; ref verify 2/2, missing-log 1/1, fabricated 0/1, unreferenced 1, store 2/2, no-header/missing-file errors; policy decbfce3...; claim ref T3:15 f9343058... match, two runs 3622529a... distinct; tour audit 13/0/13; move audit 89/89/113/28/1/28; store append 10/9/19; bridge 10/3/13 and 10/9/19; claims 3/2/1; calibration journal 10/10 0.129/0.484; Merkle compaction 3->1; progress/guard pins unchanged; standing 466/240/217; T1 0-99 1581; holdout 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; multi 9/16/11/13/14 blind 9/200/200/200/200; three 15/12/10/13/19 blind 200/200/10/200/200; trust 16/8/13/6; escape 19/18; cold-start 16/8/13/6; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 87 - chain/HMAC integrity checks for claim-ref verification (fresh gap audit)

- **Baseline** (commit 76b6c1c, cycle 86; same T3:15/65 runs):
  - canonical gate: 389 tests OK; aikit check 5/5; policy decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - the verifier checked header episode membership only; a tampered or caller-supplied log with a copied digest could pass.
- **Gap**: claim refs were not tied to log integrity. `verify_chain` detects edited/deleted/reordered/unchained logs, and an optional HMAC can verify keyed records.
- **Target delta**: default verification rejects a tampered log with its findings; the membership-only mode still passes 1/1 for the ablation; a keyed log verifies with the correct key and fails with a wrong key; intact 2/2 and store/missing/no-header cases unchanged.
- **Falsifier**: a tampered log is accepted by default; a correct keyed log is rejected; a wrong key passes; the ablation/keyed options are ignored; any behavior/pin moves.
- **Change**: claims_verify.py adds optional `hmac_key` and `verify_logs` arguments to `verify_claim_refs`/`verify_claim_store`, validates the options, and runs `verify_chain(path, hmac_key=...)` before trusting each log's header. A non-ok chain raises with the findings; `verify_logs=False` is membership-only and rejects an hmac_key. Results gain `verify_logs`/`hmac`. tests/test_claim_ref_verify.py adds tampered/membership/keyed/wrong-key/store-chain tests; evals/claim_ref_verify.py adds tampered/tampered-off/keyed/keyed-wrong. README and ADR-081 record the contract. No new dependencies; no claim/store schema or policy change.
- **After** (same runs):
  - intact: 2/2 verified, verify_logs true, hmac false; tampered: default ValueError `failed chain verification: edited-record:1, broken-link:...`, membership-only verified 1; tampered-off: 1 verified/ok true.
  - keyed: 1 verified/ok true/hmac true; keyed-wrong: ValueError `bad-mac:0, bad-mac:1`; unkeyed keyed log: chain passes, MAC ignored (documented).
  - missing-log 1/1, fabricated 0/1, unreferenced 1, store 2/2, no-header/missing-file errors unchanged.
  - behavior, standing 466/240/217, T1 0-99 1581, holdout 1581/800/738, fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0, rule readout/tie/tour audits, progress guard/skip, Merkle journal/compaction, claim store, calibration journal/bridge/retention, keyed telemetry, prompt budget, execution budget, resume identity, workspace binding, snapshot diff/digest, calibration and the 200k tail-read bound unchanged; 393 tests OK; policy unchanged.
- **Ablation** (same tampered log):
  - `verify_logs=True`: rejected (`edited-record:1`, broken links); `verify_logs=False`: membership-only verified 1. The integrity property dies with the flag.
  - keyed correct vs wrong: correct verifies 1/1, wrong `bad-mac`; a chain-only rewrite remains undetected without an external witness.
- **Verdict**: evidence-integrity extension. Behavior is unchanged; the measured deltas are tamper rejection, the membership-only ablation, and keyed correct/wrong outcomes. No action or emergence claim.
- **Gates**: unittest 393/393 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_claim_ref_verify.TestClaimRefVerifier.test_tampered_log_rejected_by_default -v` -> before: ValueError not raised; after: OK.
  - `python -m unittest tests.test_claim_ref_verify -v` -> 14 OK.
  - `python -m evals.claim_ref_verify` -> intact 2/2; tampered error/membership 1; tampered-off 1; keyed 1/ok; keyed-wrong bad-mac; missing/no-header unchanged.
  - `python -m unittest discover -s tests -t .` -> 393 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 88**: unittest 393 OK; aikit 5/5; ref verify intact 2/2, tampered rejected/membership 1, keyed 1/ok, wrong key bad-mac, missing-log 1/1, fabricated 0/1, unreferenced 1, store 2/2; policy decbfce3...; claim ref T3:15 f9343058... match, two runs 3622529a... distinct; tour audit 13/0/13; move audit 89/89/113/28/1/28; store append 10/9/19; bridge 10/3/13 and 10/9/19; claims 3/2/1; calibration journal 10/10 0.129/0.484; Merkle compaction 3->1; progress/guard pins unchanged; standing 466/240/217; T1 0-99 1581; holdout 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; multi 9/16/11/13/14 blind 9/200/200/200/200; three 15/12/10/13/19 blind 200/200/10/200/200; trust 16/8/13/6; escape 19/18; cold-start 16/8/13/6; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 88 - optional anchor-journal witness in claim-ref verification (fresh gap audit)

- **Baseline** (commit f32556b, cycle 87; same T3:15/65 logs):
  - canonical gate: 393 tests OK; aikit check 5/5; policy decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - the verifier checked the log hash chain but not an external witness; a valid truncated prefix or a fully rewritten chain still passed.
- **Gap**: no anchor-journal comparison in claim verification. `verify_chain(path, journal_path=...)` can compare the log count/head with the latest journal anchor.
- **Target delta**: two anchored logs verify 2/2 with two journals; a 28->26 truncated log passes chain-only 1/1 but fails journaled with `truncated-tail:26<28`; missing/tampered journals and bad mappings are named; the store path passes journals.
- **Falsifier**: a journaled intact log fails; a truncated prefix passes with the journal; a missing/tampered journal is ignored; a wrong mapping is accepted; behavior/pins move.
- **Change**: claims_verify.py adds `journal_paths=None` to `verify_claim_refs`/`verify_claim_store`, normalizes one path for one log or a per-log mapping, rejects unknown keys/non-path values, requires `verify_logs=True`, and passes the journal to `verify_chain`. Results gain `journals`. tests/test_claim_ref_verify.py adds nine journal tests; evals/claim_ref_verify.py adds journaled/truncated/journal-missing/journal-tampered. README and ADR-082 record the contract. No new dependencies; no claim/store schema or policy change.
- **After** (same runs):
  - journaled: 2 claims/2 verdicts, 2 verified, 2 journals, ok true; truncated: chain-only ok 1, journaled ValueError `truncated-tail:26<28`; journal-missing: `anchor-journal:missing-journal`; journal-tampered: `anchor 1 hash does not match its payload`.
  - existing intact/tampered/keyed/missing-log/fabricated/unreferenced/store/no-header/missing-file cases unchanged.
  - behavior, standing 466/240/217, T1 0-99 1581, holdout 1581/800/738, fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0, rule readout/tie/tour audits, progress guard/skip, Merkle journal/compaction, claim store, calibration journal/bridge/retention, keyed telemetry, prompt budget, execution budget, resume identity, workspace binding, snapshot diff/digest, calibration and the 200k tail-read bound unchanged; 402 tests OK; policy unchanged.
- **Ablation** (same truncated log):
  - chain-only: 1/1 verified (valid prefix); with the journal: `truncated-tail:26<28`. The external-witness property dies with the journal cut.
  - the journal can itself be rewritten; it is a witness, not a signature, and an unanchored tail fails.
- **Verdict**: evidence-integrity extension. Behavior is unchanged; the measured delta is chain-only vs journaled truncation detection plus named journal failures. No action or emergence claim.
- **Gates**: unittest 402/402 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_claim_ref_verify.TestClaimRefVerifier.test_anchored_journal_verifies -v` -> before: TypeError (`journal_paths`); after: OK.
  - `python -m unittest tests.test_claim_ref_verify -v` -> 23 OK.
  - `python -m evals.claim_ref_verify` -> journaled 2/2, truncated chain-only 1 / journal error, missing/tampered journal errors, existing modes unchanged.
  - `python -m unittest discover -s tests -t .` -> 402 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 89**: unittest 402 OK; aikit 5/5; ref verify journaled 2/2, truncated chain-only 1/journal `26<28`, missing/tampered journals; intact 2/2, tampered rejected, keyed 1/ok, wrong bad-mac, missing-log 1/1, fabricated 0/1, store 2/2; policy decbfce3...; claim refs T3:15 f9343058..., T3:65 3622529a...; tour 13/0/13; move audit 89/89/113/28/1/28; store append 10/9/19; bridge 10/3/13 and 10/9/19; claims 3/2/1; calibration 10/10 0.129/0.484; Merkle compaction 3->1; progress/guard pins; standing 466/240/217; T1 0-99 1581; holdout 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; multi 9/16/11/13/14 blind 9/200/200/200/200; three 15/12/10/13/19 blind 200/200/10/200/200; trust 16/8/13/6; escape 19/18; cold-start 16/8/13/6; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 89 - header seed and independent episode-digest verification (fresh gap audit)

- **Baseline** (commit 0f366eb, cycle 88; same T3:15 run):
  - canonical gate: 402 tests OK; aikit check 5/5; policy decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - the header bound episode_sha256 but omitted seed, so the digest could not be rebuilt from the deterministic world; claim refs trusted an unverified episode binding.
- **Gap**: no independent episode verifier. Adding seed to the header and recomputing input_digest from the stored task/seed/budget/policy closes it.
- **Target delta**: T3:15 seed 15/episode f9343058... recomputes identically; wrong seed/episode are `episode-mismatch`; missing seed/header are named; `verify_claim_refs(verify_episodes=True)` verifies 1/1 and rejects a tampered header while membership-only still passes.
- **Falsifier**: the logged seed/episode does not recompute; a wrong seed/episode passes; missing seed is ignored; the opt-in check changes membership or actions; policy/pins move.
- **Change**: telemetry/log.py adds `seed=None` to `write_header` and stores it; agent.py passes its seed. episode_verify.py rebuilds `GridWorld(task, seed).reset()` and `input_digest` from the header fields, naming missing/malformed/mismatch findings. claims_verify.py adds `verify_episodes=False` to `verify_claim_refs`/`verify_claim_store`; when true, each log's header is verified first. tests/test_episode_verify.py covers intact/wrong-seed/wrong-episode/missing-seed/missing-header/malformed/claims/opt-in; evals/episode_header.py measures intact/wrong-seed/wrong-episode/missing-seed/missing-header/claims/claims-tampered. README and ADR-083 record the contract. No new dependencies; no policy change.
- **After** (same T3:15 run):
  - intact: seed 15, episode f934305889d4..., recomputed f934305889d4..., ok true; wrong seed 16: recomputed 7be0905c0dff..., episode-mismatch; wrong episode: episode-mismatch; missing seed/header: missing-seed/missing-header.
  - claims: 1 verified/ok with verify_episodes true; claims-tampered: `failed episode verification: episode-mismatch`, membership-only 1 verified.
  - behavior, standing 466/240/217, T1 0-99 1581, holdout 1581/800/738, fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0, rule readout/tie/tour audits, progress guard/skip, Merkle journal/compaction, claim store/ref verifier, calibration journal/bridge/retention, keyed telemetry, prompt budget, execution budget, resume identity, workspace binding, snapshot diff/digest, calibration and the 200k tail-read bound unchanged; 410 tests OK; policy unchanged.
- **Ablation** (same tampered header):
  - membership-only (`verify_episodes=False`, `verify_logs=False`): the claim ref verifies 1/1; with `verify_episodes=True`: `episode-mismatch`. The recomputation property dies with the opt-in.
  - the verifier trusts the stored task/seed/budget/policy; it proves internal consistency, not execution.
- **Verdict**: evidence-integrity extension. Behavior is unchanged; the measured delta is a reproducible episode digest from the seed, named wrong/missing cases, and the claim-ref opt-in. No action or emergence claim.
- **Gates**: unittest 410/410 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_episode_verify.TestEpisodeVerify.test_logged_header_has_seed_and_verifies -v` -> before: ModuleNotFoundError (`episode_verify`); after: OK.
  - `python -m unittest tests.test_episode_verify -v` -> 8 OK.
  - `python -m evals.episode_header` -> intact f9343058...; wrong seed 7be0905c... mismatch; wrong episode/missing; claims 1; claims-tampered error/membership 1.
  - `python -m unittest discover -s tests -t .` -> 410 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 90**: unittest 410 OK; aikit 5/5; episode header seed 15, episode f9343058..., wrong seed 7be0905c..., claims 1/ok, claims-tampered episode-mismatch; policy decbfce3...; ref verify journaled 2/2, truncated 26<28, keyed/tampered cases; claim refs f9343058.../3622529a...; tour 13/0/13; move audit 89/89/113/28/1/28; store append 10/9/19; bridge 10/3/13 and 10/9/19; claims 3/2/1; calibration 10/10 0.129/0.484; Merkle compaction 3->1; progress/guard pins; standing 466/240/217; T1 0-99 1581; holdout 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; multi 9/16/11/13/14 blind 9/200/200/200/200; three 15/12/10/13/19 blind 200/200/10/200/200; trust 16/8/13/6; escape 19/18; cold-start 16/8/13/6; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 90 - optional expected-policy pin for episode and claim verification (fresh gap audit)

- **Baseline** (commit 64618ce, cycle 89; same T3:15 run):
  - canonical gate: 410 tests OK; aikit check 5/5; policy decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - `verify_episode_header` recomputed from the header's own policy_sha256, so a forged policy paired with a matching episode digest passed internally.
- **Gap**: no external policy expectation. An optional pin (the current policy_digest) can reject a header claiming a different policy even when its episode digest is self-consistent.
- **Target delta**: the current policy pin verifies; a wrong pin reports policy-mismatch; a forged policy `f`*64 plus a matching episode passes internally but fails the pin; claim refs accept the pin with verify_episodes=True and refuse it without.
- **Falsifier**: the current pin rejects an intact header; a wrong policy passes; the forged header passes the pin; a pin without episode verification is silently ignored; behavior/pins move.
- **Change**: episode_verify.py adds `expected_policy_sha256=None` (validated 64-hex) and appends `policy-mismatch` when the stored policy differs while still returning the recomputation. claims_verify.py adds `expected_policy_sha256=None` to verify_claim_refs/verify_claim_store, requires verify_episodes=True when set, and passes it per log; results carry the pin. tests/test_episode_verify.py adds five policy tests; evals/episode_header.py adds policy-current/policy-wrong/policy-forged/claims-policy. README and ADR-084 record the contract. No new dependencies; no policy or behavior change.
- **After** (same T3:15 run):
  - policy-current: ok true, findings []; policy-wrong: ok false, policy-mismatch, episode still recomputed f9343058...
  - policy-forged: fake policy `f`*64 + episode 7a428fdb... passes internal (true) but pinned ok false with policy-mismatch.
  - claims-policy: 1 verified with the current pin; wrong pin raises `failed episode verification: policy-mismatch`; pin without verify_episodes raises.
  - existing intact/wrong-seed/wrong-episode/missing-seed/missing-header/claims/claims-tampered cases unchanged; behavior, standing 466/240/217, T1 0-99 1581, holdout 1581/800/738, fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0, rule readout/tie/tour audits, progress guard/skip, Merkle journal/compaction, claim store/ref verifier, calibration journal/bridge/retention, keyed telemetry, prompt budget, execution budget, resume identity, workspace binding, snapshot diff/digest, calibration and the 200k tail-read bound unchanged; 415 tests OK; policy unchanged.
- **Ablation** (same forged header):
  - without the pin: internal verification passes (episode = recomputation under the fake policy); with the current-policy pin: policy-mismatch. The external-expectation property dies with the pin.
  - the pin compares the stored policy digest only; a forger who knows the expected digest still needs chain/journal/HMAC checks.
- **Verdict**: evidence-integrity extension. Behavior is unchanged; the measured delta is the forged-header catch by the external policy pin and the claims opt-in. No action or emergence claim.
- **Gates**: unittest 415/415 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_episode_verify.TestEpisodeVerify.test_expected_policy_matches -v` -> before: TypeError (`expected_policy_sha256`); after: OK.
  - `python -m unittest tests.test_episode_verify -v` -> 13 OK.
  - `python -m evals.episode_header` -> current ok, wrong/forged policy-mismatch, claims 1, claims-policy wrong raises.
  - `python -m unittest discover -s tests -t .` -> 415 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 91**: unittest 415 OK; aikit 5/5; episode header intact f9343058..., wrong seed 7be0905c..., policy-current ok, policy-wrong/forged policy-mismatch, claims-policy 1 and wrong pin rejected; policy decbfce3...; ref verify journaled 2/2, truncated 26<28, keyed/tampered cases; claim refs f9343058.../3622529a...; tour 13/0/13; move audit 89/89/113/28/1/28; store append 10/9/19; bridge 10/3/13 and 10/9/19; claims 3/2/1; calibration 10/10 0.129/0.484; Merkle compaction 3->1; progress/guard pins; standing 466/240/217; T1 0-99 1581; holdout 1581/800/738; ranges 683/732/800/1646; fixed syn 0.05411532 syn_n 0.10814360 phi 0.0; multi 9/16/11/13/14 blind 9/200/200/200/200; three 15/12/10/13/19 blind 200/200/10/200/200; trust 16/8/13/6; escape 19/18; cold-start 16/8/13/6; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 91 - zero-finding audit and loop stop

- **Scope**: audit the remaining named candidate space for any safe, measurable improvement. No rule, policy, or behavior change is made.
- **Candidates measured/reviewed**:
  - **Rule confidence as the SelfModel forecast**: rejected by measurement. The current SelfModel records `1.0` on rewarded steps and `0.5` otherwise (Brier 0.219101 over the 89 pin-seed steps). Using `probe.rule.confidence` as the probability gives Brier 0.640449, 0.421348 worse; the 28 ambiguous steps are move-tie ambiguity, not outcome probability, so this is a category mismatch.
  - **Retention-policy default**: rejected as an arbitrary policy choice. `calibration_keep_recent` is already opt-in per logged run (10/3/13 and 10/9/19 with unchanged scores); choosing a global default (or auto-rotating by file size) has no evidence and changes caller data without a request.
  - **Claims-side policy-pin report**: no-op. The pin already propagates through `verify_claim_refs`/`verify_claim_store` (claims-policy 1/1, wrong pin `policy-mismatch`); reporting the pin again on the claim object would be cosmetic.
  - **Header-policy cross-check**: implemented in cycle 90 (forged policy passes internally, fails the pin).
  - **Tie-break / tour-order behavior changes**: rejected by the cycle-83/84 audits (28/28 least-visited choices; 13/13 optimal tours, 0 ties on the pin seed). No evidence supports a behavior change.
  - **Merkle journal pruning, calibration pruning, destructive retention**: rejected; archive/compaction already preserve evidence losslessly and pruning would discard it.
- **Verdict**: zero-finding audit. The last 31 cycles are evidence/readout/digest extensions with unchanged actions, steps, rewards, scores and `policy_digest` (decbfce3...). No safe measurable gap remains that would not be an arbitrary policy choice, a semantic mismatch, or a re-measurement of an already-audited decision.
- **State**: unittest 415 OK; aikit check brain 5/5; tree clean at commit 648d960 before this record; no push made.

## Cycle 92 (Push 1) - claim status must match verdict history

- **Audit finding**: `ClaimLedger.from_dict`/`_validate_claim` accepted a `status` that contradicted the verdict history (`supported` with no verdicts, or with only refuting verdicts) and did not validate verdict evidence/timestamps. A rewritten claim-store snapshot with a recomputed checksum could assert an unsupported status.
- **Failing-first**: `Claim("C1","text","kill", status="supported")` and the mismatched-verdict variants raised nothing; forged store status with recomputed SHA-256 verified `ok=true`.
- **Change**: `Verdict.__post_init__` validates status/evidence/at/ref; `Claim.__post_init__` validates the claim; `_validate_claim` derives the expected status from the last verdict and rejects mismatches, and re-validates verdict texts/refs. `from_dict` and the claim store inherit the invariant. Four tests in `tests/test_claims.py`; one forged-checksum store test.
- **After**: 420 tests OK. A consistent supports/refutes history loads (`refuted`); `supported` with no verdicts, `supported`+refutes, `proposed`+supports, empty evidence and empty timestamps all raise; a status rewrite with a valid checksum fails `verify_ledger_file` (`claim store claims are invalid`) and `load_ledger`. Existing claim refs (f9343058.../3622529a...), claim store 6/6 + backup 3/3, claim/evidence and claim-ref batteries unchanged; policy decbfce3... unchanged.
- **Ablation**: without the invariant the forged snapshot verifies; with it the same checksum-valid snapshot is rejected. The checksum detects accidental edits; consistency blocks a self-consistent status lie (but not a fully fabricated history).
- **Gates**: unittest 420/420 OK; aikit check brain 5/5 PASS.

## Cycle 93 (Push 2) - lock release owns only its own lock

- **Audit finding**: telemetry/claim/calibration locks wrote `pid:timestamp` and release unconditionally unlinked the path. A writer holding a lock past the 30 s stale window could have it stolen; after a successor acquired the same path, the original writer's release deleted the successor's lock and admitted a third writer.
- **Failing-first**: `tests/test_file_locks.py` simulates acquire -> steal by rename -> successor writes a new token -> context exit. All three locks deleted the successor's file before the fix.
- **Change**: each acquisition writes a unique `pid:time_ns:random` token; release reads the file and unlinks only if the token matches. Applied to `telemetry.log._append_lock`, `claims_store._locked`, `calibration_store._locked`. Normal release still removes the lock.
- **After**: 423 tests OK. Normal acquire/release leaves no lock; the stolen-lock case leaves the successor token/file intact for all three locks. Stale steal, fresh timeout, telemetry multi-writer, claim/calibration store suites pass; behavior and policy unchanged.
- **Ablation**: without the token check the successor file is deleted; with it the file and token survive. The residual read-then-unlink window is documented, not claimed eliminated.
- **Gates**: unittest 423/423 OK; aikit check brain 5/5 PASS.

## Cycle 94 (Push 3) - stored policy/workspace digest validation and workspace pin

- **Audit finding**: the episode verifier accepted any non-empty stored `policy_sha256` and ignored `workspace_sha256`; a malformed policy could be recomputed under that string, and the source-tree digest was never cross-checked.
- **Failing-first**: `abc` policy reported only `episode-mismatch`; an `abc` workspace passed; `expected_workspace_sha256` was not accepted.
- **Change**: `verify_episode_header` requires stored policy/workspace digests to be 64-hex (`invalid-policy`/`invalid-workspace`) and accepts `expected_workspace_sha256` (`missing-workspace`/`workspace-mismatch`). `verify_claim_refs`/`verify_claim_store` pass the workspace pin through and require `verify_episodes=True` for either pin. Seven tests; six battery modes.
- **After**: 430 tests OK. Workspace-current (3bca20f2142a...) ok; wrong pin workspace-mismatch; missing pin missing-workspace; invalid stored workspace/policy named; claims-workspace 1/1 and wrong pin rejected; all prior episode/policy modes unchanged; behavior and policy unchanged.
- **Ablation**: without the workspace pin the stored tree digest is ignored; with it a wrong/missing tree is rejected. Policy validation rejects malformed strings before recomputation.
- **Gates**: unittest 430/430 OK; aikit check brain 5/5 PASS.

## Cycle 95 (Push 4) - optional HMAC-SHA256 for claim-store snapshots

- **Audit finding**: the claim-store boundary was "checksum only, no keyed signature"; a rewritten claims payload with a recomputed checksum passed.
- **Failing-first**: `hmac_key` was not accepted by save/load/verify.
- **Change**: optional `hmac_key` on save/load/verify; a keyed save adds an HMAC over the canonical payload (including the checksum); readers with a key require it. `ClaimStoreMacError` prevents a wrong/missing MAC from quarantining a valid primary.
- **After**: 434 tests OK. Keyed roundtrip verifies and loads unkeyed; wrong key, missing MAC and recomputed-checksum tamper all fail with the primary intact and no `.corrupt`; the correct key still loads after a wrong-key attempt. Unkeyed modes unchanged; behavior and policy unchanged.
- **Ablation**: unkeyed snapshot + same tamper passes the checksum but fails the MAC when a key is supplied; wrong key leaves evidence intact.
- **Gates**: unittest 434/434 OK; aikit check brain 5/5 PASS.

## Cycle 96 (Push 5) - authenticate a keyed claim store through the combined verifier

- **Audit finding**: Push 4 added a claim-store HMAC, but `verify_claim_store` loaded the snapshot without a key, silently bypassing authentication in the combined verifier.
- **Failing-first**: `store_hmac_key` was an unexpected keyword; a wrong store key was not rejected.
- **Change**: `verify_claim_store` takes `store_hmac_key` (separate from the telemetry `hmac_key`) and passes it to `load_ledger`; results carry `store_hmac`. One test and a `store-keyed` battery mode.
- **After**: 435 tests OK. Keyed store verifies 2/2 with `store_hmac=true`; wrong key raises `claim store MAC does not match its payload`; unkeyed store still verifies; all other claim-ref modes unchanged; behavior and policy unchanged.
- **Ablation**: omitting `store_hmac_key` loads the keyed store unauthenticated (backward compatible); supplying it enforces the MAC.
- **Gates**: unittest 435/435 OK; aikit check brain 5/5 PASS.

## Cycle 97 (Push 6) - stream header-only reads for verification

- **Audit finding**: episode/claim verification decoded and retained every action record just to find headers; a 100k-record log cost 124.2 MB peak.
- **Change**: `Telemetry.read_headers()` streams the JSONL and retains only header records, with `read_all`-compatible errors; used by `verify_episode_header` and `claims_verify._log_episodes`. Three tests and `evals/header_reader.py`.
- **After**: 438 tests OK. On 100,001 lines the header is identical; `read_all` peak 124.2 MB/5.715 s, `read_headers` 0.1 MB/4.019 s (~1240x less peak memory, 30% faster). Missing/malformed behavior matches; episode/claim-ref modes unchanged; behavior and policy unchanged.
- **Ablation**: `read_all` retains all 100k records; `read_headers` retains one. Time stays O(n); the win is memory/allocation.
- **Gates**: unittest 438/438 OK; aikit check brain 5/5 PASS.

## Cycle 98 (Push 7) - optional per-record HMAC for the calibration journal

- **Audit finding**: calibration records were checksum-only; a rewritten record with a recomputed checksum passed, and keyed rotation was undefined.
- **Change**: optional `hmac_key` on append/load/load-all/verify/rotate; each keyed record carries a MAC over the record including its checksum; `_record_digest` excludes both `sha256` and `mac` so unkeyed checksums stay exact.
- **After**: 443 tests OK. Keyed journal verifies and loads unkeyed; wrong key and missing MAC fail with per-line findings; a rewritten probability with recomputed checksum fails the MAC; keyed rotation keeps 10 records at Brier 0.129/skill 0.484 and a wrong-key rotation leaves the file byte-identical. Unkeyed modes and behavior/policy unchanged.
- **Ablation**: without a key the checksum-only journal accepts the recomputed tamper; with the key the MAC rejects it. Rotation without a key cannot read a keyed journal (it raises), preventing silent MAC loss.
- **Gates**: unittest 443/443 OK; aikit check brain 5/5 PASS.

## Cycle 98b (Push 8, recorded after Push 9) - pass a calibration HMAC key through the logged-run bridge

- **Audit finding**: the bridge could not pass the calibration journal's HMAC key, so a keyed journal could not be appended through a real run.
- **Failing-first**: `calibration_hmac_key` was an unexpected keyword.
- **Change**: `run_task_logged` takes `calibration_hmac_key` (non-empty bytes, requires `calibration_path`, validated before the run) and passes it to `append_forecasts`; three tests and a keyed bridge-battery mode.
- **After**: keyed T3:15 appends 13 records/13 resolved with Brier 0.230769 and `hmac=true`; a wrong key is rejected; a key without a path or an invalid key fails before the log; default/two-run/actions modes unchanged.
- **Gates**: 11 bridge tests pass; final cumulative suite 449 OK; AIKit 5/5; no behavior or policy change.

## Cycle 99 (Push 9) - refuse unkeyed writes over keyed evidence

- **Audit finding**: an unkeyed calibration append over a keyed journal created a mixed journal that keyed loads reject; an unkeyed rotation moved keyed records unauthenticated; an unkeyed claim-store save replaced a keyed primary with an unkeyed snapshot.
- **Failing-first**: all three downgrade attempts succeeded and changed the file.
- **Change**: `append_forecasts` refuses an unkeyed append when existing records carry `mac`; `_rotate_locked` refuses an unkeyed rotation when live/archive records carry `mac`; `save_ledger` refuses an unkeyed overwrite of a keyed payload. Errors leave the file untouched.
- **After**: 449 tests OK. All three attempts raise and the file is byte-identical; keyed reads still load; keyed append/rotation/save and all unkeyed-existing paths are unchanged; behavior and policy unchanged.
- **Ablation**: without the guard the file is downgraded/mixed; with it the write is refused before any byte changes.
- **Gates**: unittest 449/449 OK; aikit check brain 5/5 PASS.

## Push-series review 1 to 9 and loop-back to the beginning

- **Baseline**: branch `master` at `bfe3ba6` (98 commits, no remote configured). A "push" here is a verified local conventional commit; `git push` has no destination, so no network push was possible or made.
- **Review 1 -> 3** (`b6bbe55`, `7059769`, `7d55146`): 3 commits, 15 files, 608 insertions. Claim status/verdict consistency, lock ownership tokens, episode workspace/policy pins. Cumulative gates: 430 tests OK; AIKit 5/5; claim store/evidence and episode batteries clean; `policy_digest` unchanged.
- **Review 1 -> 6** (`+fc623c8`, `4ae5aca`, `2aa67a3`): 6 commits, 20 files, 1036 insertions. Keyed claim store, keyed store authentication through the ref verifier, streamed header reads (100k records: 124.2 MB -> 0.1 MB peak). Cumulative gates: 438 tests OK; AIKit 5/5; keyed/wrong/missing/tampered and workspace modes clean.
- **Review 1 -> 9** (`+cb7fcb2`, `c6829bc`, `e2cd251`, docs `f1a2a75`): 9 feature pushes, 25 files, 1487 insertions. Keyed calibration journal/rotation, keyed bridge pass-through, unkeyed-downgrade guards. Cumulative gates: 449 tests OK; AIKit 5/5; keyed claim store (correct/wrong/missing/tampered/downgrade), keyed calibration (correct/wrong/missing/rotation/mixed), keyed bridge 13/13 at Brier 0.230769, episode workspace pins, and `policy_digest` decbfce3... all clean.
- **Loop-back to Push 1**: re-ran `tests.test_claims`, `tests.test_claims_store`, `tests.test_file_locks`, `tests.test_episode_verify` at HEAD: 57 tests OK; the Push 1 `Claim(status="supported")` inconsistency is still rejected; the full suite is 449 OK and AIKit 5/5. The beginning behavior survives all later pushes.
- **Findings fixed**: claim status could contradict verdict history (Push 1); a stolen lock's successor could be deleted (Push 2); malformed policy/workspace digests were accepted and workspace was unverified (Push 3); claim snapshots were checksum-only (Push 4); the combined verifier bypassed a keyed store (Push 5); verification retained every action record (Push 6); calibration records were checksum-only (Push 7); the bridge could not pass a calibration key (Push 8); unkeyed writes could downgrade keyed evidence (Push 9).
- **Result**: no regressions, no behavior/action/reward changes, no policy change. The reviewed range now starts and ends at the same verified state class: full tests green, AIKit 5/5, clean tree.

## Cycle 100 - world-geometry fingerprint for persisted layouts

- **Baseline** (commit 7e424cf, cycle 99; same probe worlds and store):
  - canonical gate: 449 tests OK; aikit check 5/5; policy decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - standing behavior: 30-seed T1 466 / T2 240 / T3 217; fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0.
  - collision probe (two `GridWorld` subclasses sharing task T3_navigate seed 0): warm A (target [6,7], obstacle [6,1]) 13 steps/1.0; warm B (target [3,3], obstacle [3,2]) 6 steps/1.0, but the stored layout still read `target [6,7]`; cold B with hidden goal fields 200 steps/0.0.
- **Gap**: layouts are keyed only by `(task, seed)` and first-write-wins keeps the first complete row. A second distinct world reusing the same task id and seed therefore never persists, and its cold run recalls the first world's target — recovery silently targets the wrong geometry.
- **Target delta**: cold B 200/0.0 -> 6/1.0 with B's geometry stored; built-in warm-cold, cold-first, standing and `policy_digest` unchanged.
- **Falsifier**: cold B stays 200/0; any built-in cold-start, standing or fixed-rig pin moves; or the blind-fingerprint ablation does not restore the 200/0 collision.
- **Change**: `worlds/grid.py` adds deterministic `layout_fingerprint()` (SHA-256 over size/task/target/obstacles/initial items/cue); `agent.py` adds `world_fingerprint(world)` and passes it to `get_layout`/`save_layout` in `_persistent_layout`/`_remember_layout`; `memory/store.py` adds the nullable `fingerprint` column (in-place `ALTER TABLE` for older stores), replace-on-known-mismatch in `save_layout`, a fingerprint-aware `get_layout`, and `layout_fingerprint(task, seed)`; `tests/test_layout_fingerprint.py` adds three tests. No new dependencies; no policy or built-in behavior change. ADR-094; README cold-start contract.
- **After** (same probe worlds and store):
  - collision fixed: warm A 13/1.0, warm B 6/1.0, stored layout `target [3,3]` / `obstacles [[3,2]]`, cold B 6/1.0.
  - built-in warm-cold unchanged: 16/8/13/6 steps with 3/1/1/1, probe `store_reads` 1 cold / 0 warm; cold-first unchanged: cold1 200, warm 16/8/13/6, cold2 16/8/13/6 with 3/1/1/1.
  - standing 466/240/217; fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0; `policy_digest` decbfce3... unchanged.
- **Ablation** (patch `agent.world_fingerprint` to return None, same probe worlds and store):
  - warm A 13/1.0; warm B cannot replace A's complete row; cold B 200/0.0 (exactly the baseline). The collision fix dies with the fingerprint cut and returns with the restore.
  - Fingerprint stability is also pinned: two resets of `GridWorld("T3_navigate", 15)` agree, and seeds 15/65 differ.
- **Verdict**: recovery-correctness integration. Built-in worlds and all behavior/trace pins are unchanged; the measured delta is custom-world cold recovery 200/0.0 -> 6/1.0 with the correct persisted geometry. No emergence claim: the fingerprint identifies geometry, not memory coupling.
- **Gates**: unittest 452/452 OK; aikit check brain 5/5 PASS (after regenerating `.aikit/codebase_map.md` for the new test file).
- **Commands run**:
  - `python -m unittest tests.test_layout_fingerprint -v` -> before: 1 failure (200 != 6), 2 errors (missing `world_fingerprint`/`layout_fingerprint`); after: 3 OK.
  - `python -m unittest discover -s tests -t .` -> 452 OK.
  - `python -m evals.coldstart --capture` -> 16/8/13/6 with store_reads 1; `--scenario cold-first --capture` -> 200 then 16/8/13/6.
  - `python -m unittest tests.test_coldstart_recovery tests.test_memory tests.test_substrate_errors tests.test_store_recovery tests.test_wiring` -> 20 OK.
  - `python scripts/update_knowledge_base.py --workspace .../projects/brain` -> map updated; `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 101**: unittest 452 OK; aikit 5/5; custom-world collision fixed (cold B 6/1.0, stored B geometry); blind-fingerprint ablation 200/0.0; built-in cold-start 16/8/13/6 with 3/1/1/1; cold-first 200 then 16/8/13/6; standing 466/240/217; T1 0-99 1581; holdout 500-599 1581/800/738; ranges 683/732/800/1646; fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0; policy decbfce3...; multi 9/16/11/13/14; three 15/12/10/13/19; trust 16/8/13/6; escape 19/18; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 101 - backfill layout fingerprints onto legacy rows

- **Baseline** (commit 84d1091, cycle 100; same probe worlds and store):
  - canonical gate: 452 tests OK; aikit check 5/5; policy decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - legacy-row probe (simulate a pre-ADR-094 row with `save_layout(..., fingerprint=None)`): the row's fingerprint is NULL; warm A, warm B then hidden cold B still produced 200 steps/0.0, because `_remember_layout` returned early for the complete legacy row and never wrote a fingerprint.
  - `_remember_layout` therefore left the cycle-100 collision guard inert on every store created before the upgrade.
- **Gap**: an upgraded store never gains a fingerprint, so distinct worlds sharing `(task, seed)` still collide there. The guard must activate on the first complete run over a legacy row.
- **Target delta**: legacy row gains a fingerprint on the first warm run; warm A / warm B / cold B recovers B at 6 steps/1.0; built-in pins unchanged.
- **Falsifier**: the legacy row's fingerprint stays NULL; cold B stays 200/0; any built-in cold-start, standing or fixed-rig pin moves.
- **Change**: `agent.py` `_remember_layout` treats a complete row with a NULL stored fingerprint (and a world fingerprint available) as a backfill target and rewrites the current complete state plus fingerprint with `replace=True`; stores without the accessor and worlds without a fingerprint keep the old logic. `tests/test_layout_fingerprint.py` adds the legacy-row test. No new dependencies; no built-in behavior or policy change. ADR-095.
- **After** (same probe worlds and store):
  - legacy row backfilled: fingerprint non-NULL after the first warm run; warm A 13/1.0, warm B 6/1.0, cold B 6/1.0.
  - built-in warm-cold still 16/8/13/6 with 3/1/1/1; standing 466/240/217; fixed-rig and `policy_digest` unchanged.
- **Ablation / sensitivity**:
  - removing the backfill (the pre-change behavior measured above) restores the 200/0.0 collision on the legacy store; the same test fails. The backfill is the load-bearing cut.
  - the blind-fingerprint ablation from cycle 100 still restores the collision on a fresh store, so both the source channel and the upgrade path are pinned.
- **Verdict**: recovery-correctness completion. The measured delta is legacy-store cold recovery 200/0.0 -> 6/1.0 after the first warm run backfills the fingerprint. No emergence claim.
- **Gates**: unittest 453/453 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_layout_fingerprint.TestLayoutFingerprint.test_legacy_row_gains_fingerprint_and_stops_colliding -v` -> before: FAIL (fingerprint None), after: OK.
  - `python -m unittest tests.test_layout_fingerprint -v` -> 4 OK.
  - `python -m unittest discover -s tests -t .` -> 453 OK.
  - `python -m evals.coldstart --capture` -> 16/8/13/6 unchanged.
- **Pinned regression baselines for cycle 102**: unittest 453 OK; aikit 5/5; legacy row backfilled (cold B 6/1.0); fresh-world collision fixed; blind-fingerprint ablation 200/0.0; built-in cold-start 16/8/13/6 with 3/1/1/1; cold-first 200 then 16/8/13/6; standing 466/240/217; T1 0-99 1581; holdout 500-599 1581/800/738; ranges 683/732/800/1646; fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0; policy decbfce3...; multi 9/16/11/13/14; three 15/12/10/13/19; trust 16/8/13/6; escape 19/18; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 102 - hoist the per-row discretization in the synergy estimator

- **Baseline** (commit c66b325, cycle 101; same synthetic input):
  - canonical gate: 453 tests OK; aikit check 5/5; policy decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - `evals.estimators.synergy` on 4000 rows: 8.056 s (`syn` 0.000005, `syn_n` 0.739649); `_discretize` call count on 50 rows is 56.
- **Gap**: the joint code is built with `_discretize(c1, 8)[i]` inside a per-row comprehension, so the second column is discretized once per row — quadratic in the trace length. `recompute` runs this per captured log, so evidence/ablation cost scales badly.
- **Target delta**: hoist the column discretization; outputs byte-identical; `_discretize` calls 56 -> 7 on 50 rows; 4000-row time 8.056 s -> well under a second.
- **Falsifier**: any estimator reference or fixed-rig pin moves; the call count stays `n + 6`; or the returned `syn`/`syn_n` differ.
- **Change**: `evals/estimators.py` `synergy` computes `c1_bins = _discretize(c1, 8)` once before the comprehension; `tests/test_synergy_cost.py` counts calls under `mock.patch` and checks value equality plus the XOR synergy. No new dependencies; no behavior or policy change. ADR-096.
- **After** (same input):
  - 4000 rows: 0.0123 s (about 655x faster) with `syn` 0.000005 and `syn_n` 0.739649 unchanged; `_discretize` calls 7 on 50 rows.
  - estimator references and fixed-rig integration pins unchanged; standing 466/240/217; `policy_digest` unchanged.
- **Ablation / sensitivity**:
  - restoring the inline expression (the pre-change code measured above) reproduces the 56 calls and the 8.056 s cost; the call-count test fails. The hoist is the load-bearing cut.
  - values are unchanged by construction (same function and input), confirmed by comparing patched and unpatched results and by the existing XOR/independent-target assertions.
- **Verdict**: harness performance win with identical measurement output. No behavior or emergence claim.
- **Gates**: unittest 455/455 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_synergy_cost -v` -> before: 1 failure (56 > 10); after: 2 OK.
  - `python -m unittest tests.test_synergy_cost tests.test_estimators tests.test_integration_differentials -v` -> 12 OK.
  - timing probe n=4000 -> 8.056 s before, 0.0123 s after, identical syn/syn_n.
  - `python -m unittest discover -s tests -t .` -> 455 OK.
- **Pinned regression baselines for cycle 103**: unittest 455 OK; aikit 5/5; synergy 4000 rows 0.0123 s with `_discretize` calls 7; legacy layout row backfilled (cold B 6/1.0); blind-fingerprint ablation 200/0.0; built-in cold-start 16/8/13/6 with 3/1/1/1; cold-first 200 then 16/8/13/6; standing 466/240/217; T1 0-99 1581; holdout 500-599 1581/800/738; ranges 683/732/800/1646; fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0; policy decbfce3...; multi 9/16/11/13/14; three 15/12/10/13/19; trust 16/8/13/6; escape 19/18; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 103 - declare the layouts fingerprint column in the base schema

- **Baseline** (commit 7249d3e, cycle 102):
  - canonical gate: 455 tests OK; aikit check 5/5; policy decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - declared schema: `_SCHEMA_LAYOUT` has no `fingerprint` column; a fresh store therefore runs `_ensure_layout_fingerprint` -> `ALTER TABLE` on every open and `_ensure_layout_fingerprint` returns `None`.
  - probe: `tests/test_store_schema.py` -> 3 failures on the intact tree (declaration missing the column, fresh store reports no boolean, legacy assertion path unreachable).
- **Gap**: the declared table shape and the live/migrated table shape disagree. A fresh database pays a hidden migration on every open, and anyone reading the schema (developer or agent) is misled about the store it describes.
- **Target delta**: declaration includes `fingerprint`; a fresh store creates it directly and reports `_ensure_layout_fingerprint(...) is False`; a legacy file is migrated once, keeps its row, and reports no further migration.
- **Falsifier**: a fresh store still alters the schema; the legacy row is lost; any existing store/cold-start/standing pin moves.
- **Change**: `memory/store.py` `_SCHEMA_LAYOUT` gains `fingerprint TEXT`; `_ensure_layout_fingerprint` returns `True` on migration and `False` when the column is already declared; `tests/test_store_schema.py` adds the declaration, fresh-store and legacy-migration pins. No API, format or behavior change. ADR-097.
- **After** (same store paths):
  - fresh store: `fingerprint` column present from `CREATE TABLE`; `_ensure_layout_fingerprint` returns `False` (no `ALTER`).
  - legacy store (old five-column table plus one row): opens, column added once, `_ensure_layout_fingerprint` returns `False` afterwards, row content preserved, `layout_fingerprint` initially `None`.
  - cold-start 16/8/13/6 with 3/1/1/1; standing 466/240/217; `policy_digest` unchanged.
- **Ablation / sensitivity**:
  - restoring the old declaration (the measured baseline above) makes all three schema tests fail and reintroduces the hidden `ALTER` on every fresh open; the migration return value is the load-bearing cut.
  - the legacy fixture proves the migration path still works, so the fix removes the redundant migration without removing the upgrade.
- **Verdict**: schema/DX alignment with a deterministic before/after. No behavior or emergence claim.
- **Gates**: unittest 458/458 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_store_schema -v` -> before: 3 failures; after: 3 OK.
  - `python -m unittest tests.test_store_schema tests.test_store_recovery tests.test_memory tests.test_layout_fingerprint -v` -> 14 OK.
  - `python -m unittest discover -s tests -t .` -> 458 OK.
  - `python -m evals.coldstart --capture` -> 16/8/13/6 unchanged.
- **Pinned regression baselines for cycle 104**: unittest 458 OK; aikit 5/5; fresh store no migration; legacy store migrated once with row preserved; synergy 4000 rows 0.0123 s with `_discretize` calls 7; legacy layout row backfilled (cold B 6/1.0); blind-fingerprint ablation 200/0.0; built-in cold-start 16/8/13/6 with 3/1/1/1; cold-first 200 then 16/8/13/6; standing 466/240/217; T1 0-99 1581; holdout 500-599 1581/800/738; ranges 683/732/800/1646; fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0; policy decbfce3...; multi 9/16/11/13/14; three 15/12/10/13/19; trust 16/8/13/6; escape 19/18; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 104 - explicit read-only state-machine registry

- **Baseline** (commit 4b3a6ce, cycle 103):
  - canonical gate: 458 tests OK; aikit check 5/5; policy decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - the tree had no registry: states lived in JSON fields, verdict words, reason strings and file presence across `agent.py`, `telemetry/`, `claims*`, `calibration_store.py`, `identity.py`, `planner/` and `budget.py`; `python state_machines.py` did not exist.
- **Gap**: 21 lifecycles were implicit. A developer or agent had to infer states and legal moves from code, and the `claim`/`verdict`/`resume-policy` vocabularies could drift without any check. This is the "find all implicit state machines" deliverable for Brain.
- **Target delta**: one read-only registry with 21 machines, a CLI for listing/inspecting/checking transitions, a live-vocabulary drift check, an inventory doc and a scored proposal doc; zero behavior change.
- **Falsifier**: an inconsistent transition table; a declared state set that disagrees with its live constant; any standing/cold-start/trace/policy pin moves.
- **Change**: `state_machines.py` (frozen `Machine` data + read-only CLI: `--list`, `--json`, `--machine`, `--from/--to`, `--check-status`, `--check`); `tests/test_state_machines.py` (consistency, every machine/state, every declared and one disallowed transition, list/JSON, misuse exit 2, live vocabularies); `.aikit/state_machines.md` (inventory) and `.aikit/state_machine_proposals.md` (UX/DX/AX-scored proposals); README quick-reference row and tree line. No product module imports the registry. ADR-098. The working tree also carried a completed `synergy_scope` readout (7 tests) from a parallel edit; it was committed immediately before this cycle so the tree and codebase map stay consistent, and it is not part of the registry change.
- **After** (same tree):
  - `python state_machines.py --list` -> 21 machines; `--json` -> 21 records; `--machine model-decision` renders 9 states and the known gap.
  - `python state_machines.py --check` -> `claim-status`, `resume-policy`, `verdict-event` all `ok`, exit 0.
  - `python state_machines.py --machine claim-status --from proposed --to supported` -> allowed; `--from supported --to proposed` would be refused (declared false in the transition table).
  - behavior/standing/cold-start/fixed-rig/`policy_digest` unchanged.
- **Ablation / sensitivity**:
  - deleting `state_machines.py` makes the test module unimportable and every CLI mode absent; no product path references it, so behavior is identical with or without it (documentation-only integration).
  - changing a declared live-vocabulary state (for example adding a claim status to the registry only) makes `--check` exit 1, so drift is detectable rather than silent.
- **Verdict**: documentation/DX/AX integration with a read-only registry and a live drift check. No behavior or emergence claim. Proposals P3/P6 deferred and P4/P5 rejected with reasons in `.aikit/state_machine_proposals.md`.
- **Gates**: unittest 471/471 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_state_machines -v` -> 6 OK.
  - `python state_machines.py --list` -> 21 machines; `--check` -> 3/3 ok; representative transition allowed.
  - `python -m unittest discover -s tests -t .` -> 471 OK.
  - `python -m evals.coldstart --capture` -> 16/8/13/6 unchanged.
- **Pinned regression baselines for cycle 105**: unittest 471 OK; aikit 5/5; registry 21 machines with 3/3 live checks ok; fresh store no migration; legacy store migrated once with row preserved; synergy 4000 rows 0.0123 s with `_discretize` calls 7; legacy layout row backfilled (cold B 6/1.0); blind-fingerprint ablation 200/0.0; built-in cold-start 16/8/13/6 with 3/1/1/1; cold-first 200 then 16/8/13/6; standing 466/240/217; T1 0-99 1581; holdout 500-599 1581/800/738; ranges 683/732/800/1646; fixed-rig syn 0.05411532 syn_n 0.10814360 phi 0.0; policy decbfce3...; multi 9/16/11/13/14; three 15/12/10/13/19; trust 16/8/13/6; escape 19/18; goldens 9/9 + multi 5/5 + three 5/5.

## Cycle 105 - the synergy estimate carries its column scope

- **Baseline** (commit 4b3a6ce, then a35a409; same probe traces):
  - canonical gate: 471 tests OK; aikit check 5/5; `policy_digest` decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - `synergy` reads `trace[0]` and `trace[1]` only: 2-column and 3-column calls on the same leading pair both return 0.11181316771575098.
  - cold-start T3:15: `syn` 0.0 while column 0 has 1 unique value and column 7 carries MI 0.271189; the battery prints `syn 0.0` with no scope qualifier.
  - `hub_zero_rows` reaches `syn` 0.0 because hub[2] is the target column; swapping hub x/y with the reward kept leaves `syn` at 0.05411532090976823, identical to baseline.
- **Gap**: the reported number is unfalsifiable at the read site. `0.0` conflates "these two columns carry nothing about the target" with "the criterion cannot see the signal", so the integration and emergence readouts can neither claim nor refute integration outside columns 0-1. `lesion_p`/`lesion_s` "change nothing" follows from the same blindness rather than from a measured invariant.
- **Target delta**: every `syn` is accompanied by a machine-checkable statement of what it measured and whether that scope could decide; no estimate changes; no pinned value moves.
- **Falsifier**: any pinned `syn`/`syn_n`/`phi`/step/reward/`policy_digest` moves; a trailing column changes the estimate; a constant scope column is reported `sufficient`.
- **Killed candidates** (by measurement, before writing code):
  - Joint code over all 8 scope columns: 8 bins^8 at n=15 puts nearly every row in its own cell and inflates MI instead of measuring it.
  - Pairwise block interaction (M/P/S/hub) versus a permutation null: 0 of 6 pairs beat the null at n=15 (best obs -0.038304 vs null +0.031462), and 0 of 5 seeds beat it at n in 6..14. Not reproducible at these sample sizes, so not shipped as a criterion.
- **Change**: `evals/estimators.py` adds `SYNERGY_COLUMNS = (0, 1)` and `synergy_scope(trace, target)` returning `columns`, `ignored_columns`, `n_rows`, `n_columns`, `constant_columns`, `sufficient`, `reason`; `evals/recompute.py` adds `syn_scope` beside `syn`; `tests/test_synergy_scope.py` adds 7 tests. `synergy` itself is untouched. ADR-099.
- **After** (same traces):
  - fixed rig: `syn` 0.054115320909768228 and `syn_n` 0.10814360275702875 bit-identical to their pins; `syn_scope` = `{columns: [0,1], ignored_columns: [2..7], n_rows: 30, n_columns: 8, constant_columns: [], sufficient: true, reason: null}`.
  - all four cold-start cases: `sufficient: false`, `reason: constant-scope-column`, `constant_columns: [0]`; the same 0.0 is now labelled insufficient instead of being read as absence.
- **Ablation** (same cold log, two readers): reading `syn == 0.0` as an integration verdict yields "no integration"; reading the shipped `syn_scope.sufficient` yields "insufficient: constant-scope-column". The false-negative property dies with the scope field and returns with it. The estimate is unchanged either way, so the field is the only difference.
- **Verdict**: telemetry-honesty extension. The measured delta is a false "no integration" read replaced by an explicit insufficiency on the exact traces where the criterion is blind; no behavior, estimate, standing, cold-start or `policy_digest` change. Boundary recorded: `syn` stays a two-column statistic, so `sufficient: true` with 0.0 still only means those two columns carry nothing, and a wider criterion needs samples these traces do not supply (`phi` remains the cross-column readout).
- **Gates**: unittest 471/471 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_synergy_scope -v` -> before: ImportError (`SYNERGY_COLUMNS` absent); after: 6 OK, then 7 OK with the recompute case.
  - `python -m unittest tests.test_synergy_scope tests.test_estimators tests.test_recompute tests.test_wiring tests.test_integration_differentials tests.test_synergy_cost` -> 23 OK.
  - `python ..\..\scratch\ablate_103.py` -> pinned `syn`/`syn_n` identical; cold scope `constant-scope-column`; ablation old-read "no integration" vs scoped "insufficient".
  - `python -m unittest discover -s tests -t .` -> 471 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 106**: unittest 471 OK; aikit 5/5; `syn_scope` present on every `recompute` result and JSON-serialisable; fixed-rig `syn` 0.054115320909768228 `syn_n` 0.10814360275702875 `phi` 0.0 with `sufficient: true`; cold-start cases `sufficient: false` / `constant-scope-column`; registry 21 machines 3/3 ok; built-in cold-start 16/8/13/6 with 3/1/1/1; cold-first 200 then 16/8/13/6; standing 466/240/217; policy decbfce3...; all other cycle-104 pins unchanged.

## Cycle 106 - measure whether a lesion can be detected at all

- **Baseline** (commit 942771d; fixed T1:7 rig, 15 steps, 9 block columns):
  - canonical gate: 471 tests OK; aikit check 5/5; `policy_digest` decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - `test_planner_and_selfmodel_lesions_change_nothing` passes; `lesion_p`/`lesion_s` leave `syn` at 0.05411532090976823.
  - replacing P and S with pseudo-random floats of the same shape leaves `syn` at 0.05411532090976823, byte-identical to the lesion result.
  - per-module substitution moves `syn` only for M (-0.315563) and hub (+0.226725); P and S do not move it.
- **Gap**: the differential's assertion cannot fail for the reason its name states. `synergy` reads columns 0-1, so "zero P/S and the score holds" is satisfied by any P/S content, including noise — a control that cannot fail (EVID-009). The suite therefore recorded a readout property as a module finding. `phi` has the mirror problem: 0.0 on all four substitutions because M/P/S are exact counters, so it carries no per-module information on this rig either.
- **Target delta**: the detectable surface becomes a measured, machine-readable fact per readout and module, so a vacuous lesion is named rather than read as absent integration; no estimate, behavior or pin changes.
- **Falsifier**: any pinned value moves; `syn` responds to a P or S substitution; or `detectability` reports a module visible that the substitution probe cannot move.
- **Killed candidate**: an interaction criterion over all module blocks. Already rejected in cycle 105 by measurement (0 of 6 pairs beat the permutation null at n=15; 0 of 5 seeds at n in 6..14), and `phi` shows the same floor here.
- **Change**: `evals/lesion_audit.py` adds `MODULE_SPANS`, `module_columns`, `substitute_module(rows, module, seed)` (seeded uniform noise in `[0, 16)`, shape and other columns preserved) and `detectability(rows)` (per readout: `detectable`, `invisible`, `all_detectable`, `baseline`); `tests/test_lesion_detectability.py` adds 7 tests; `tests/test_integration_differentials.py` gains `test_planner_and_selfmodel_are_invisible_to_synergy` and a corrected docstring; README section. ADR-100.
- **After** (same rig):
  - `synergy`: detectable `[M, hub]`, invisible `[P, S]`, `all_detectable: false`.
  - `phi`: detectable `[]`, invisible `[M, P, S, hub]`; the estimator still responds to genuinely autocorrelated input, so the floor is the counters, not a broken estimator.
  - fixed-rig `syn` 0.05411532090976823, `phi` 0.0, steps 15, standing 466/240/217 and `policy_digest` unchanged.
- **Ablation**: without `detectability` the suite reads "P/S lesions change nothing" as "P/S are not integrated"; with it the same run reports `synergy.invisible [P, S]`, so the sentence is a readout property. Removing the module deletes the measurement and restores the unfalsifiable reading; restoring it returns the per-module verdict.
- **Verdict**: ablation-honesty extension. The measured delta is a vacuous control converted into a pinned, per-module detectability report; no behavior, estimate, standing, cold-start or `policy_digest` change. Boundary: noise is uniform in `[0, 16)`, so a module whose real values sit far outside that range could read invisible for a scale reason; the report names module lists, it does not rank effect sizes, and `invisible` is a property of the readout, not evidence that the module is unintegrated.
- **Gates**: unittest 479/479 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_lesion_detectability -v` -> before: ModuleNotFoundError (`evals.lesion_audit`); after: 7 OK.
  - `python -m unittest tests.test_integration_differentials tests.test_lesion_detectability -v` -> 11 OK.
  - `python ..\..\scratch\ablate_106.py` -> synergy `[M, hub]` / `[P, S]`; phi `[]` / all four; ablation text recorded.
  - `python -m unittest discover -s tests -t .` -> 479 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 107**: unittest 479 OK; aikit 5/5; `detectability` fixed-rig `synergy` detectable `[M, hub]` invisible `[P, S]`, `phi` detectable `[]`; `syn_scope` unchanged; fixed-rig `syn` 0.054115320909768228 `syn_n` 0.10814360275702875 `phi` 0.0; cold-start 16/8/13/6 with 3/1/1/1; cold-first 200 then 16/8/13/6; standing 466/240/217; policy decbfce3...; registry 21 machines 3/3; all earlier pins unchanged.

## Cycle 107 - one-level recall copies instead of a per-step history deepcopy

- **Baseline** (commit 37f61e1; same pinned rigs):
  - canonical gate: 479 tests OK; aikit check 5/5; `policy_digest` decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - `Memory.recall(limit=None)` deep-copies every stored state on every call; the loop calls it once per step, so the work is O(n) per step inside an O(n) loop.
  - realistic nested states, 60 calls: n=60 0.047677 s; n=200 0.163636 s.
- **Gap**: the copy buys nothing. `Planner.plan` reads only `list(memories)[-4:]`; `_step_vectors` reads `len(memories)`; the `_recall` probe walks the list read-only. No consumer mutates the argument, so a recursive copy of the whole history is pure per-step cost that grows with episode length.
- **Target delta**: per-step recall drops to a one-level dict copy with identical actions, steps, rewards and store isolation; no pin moves.
- **Falsifier**: any pinned step/reward/range/holdout/cold-start/`policy_digest` value moves; a returned dict mutation reaches the store; or the planner's argument changes.
- **Change**: `agent.py` `Memory.recall` returns `[dict(item) for item in ...]` on both paths and documents the contract; `Memory.save` still stores a deepcopy. `tests/test_recall_cost.py` adds 4 tests (store isolation under a rebind, a measured cost comparison against `copy.deepcopy` at n=60/200, the pinned action quadruple, planner non-mutation). ADR-101. No README section: the change is internal, behavior-preserving and adds no caller-visible contract, and README.md sits at its 32,500-char cap (32,492), so a new section would force an unrelated deletion.
- **After** (same rigs):
  - standing 89 steps / 11.0 reward; T1 0-99 1581; holdout 500-599 738 (min 1, max 14); cold-start 16/8/13/6 with rewards 3/1/1/1 and `store_reads` 1 per case; `policy_digest` unchanged.
  - 60 calls at n=200: 0.001850 s (was 0.163636 s); at n=60: 0.000571 s (was 0.047677 s).
- **Ablation** (same states, same call count, `copy.deepcopy(m._items)` reinstated as the cut): 0.222778 s versus 0.001850 s, 120.4x slower. The cost returns with the cut and disappears with the one-level copy, and every behavioral pin is identical either way, so the delta is the copy and nothing else.
- **Verdict**: behavior-preserving substrate cost win on the hot path. No telemetry or emergence claim; the measured delta is per-step recall time and it moves no behavioral pin. Boundary: nested values in a returned state are shared with the store, so an in-place mutation of a nested field would corrupt history; the planner does not do this and the contract is documented rather than enforced.
- **Gates**: unittest 483/483 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_recall_cost -v` -> before: 1 failure (40x cost scaling); after: 4 OK.
  - `python ..\..\scratch\ablate_107.py` -> standing 89/11.0, T1 1581, holdout 738, cold-start 16/8/13/6, policy unchanged; ablation 120.4x.
  - `python -m unittest discover -s tests -t .` -> 483 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 108**: unittest 483 OK; aikit 5/5; recall cost n=200 x60 ~0.002 s versus 0.223 s for deepcopy; standing 89 steps / 11.0 reward; T1 0-99 1581; holdout 500-599 738 (min 1, max 14); cold-start 16/8/13/6 with 3/1/1/1 and `store_reads` 1; `detectability` `[M, hub]` / `[P, S]`; `syn` 0.054115320909768228 `syn_n` 0.10814360275702875 `phi` 0.0; policy decbfce3...; all earlier pins unchanged.

## Cycle 108 - read the self-model's recorded size in O(1)

- **Baseline** (commit 8144577; same pinned rigs):
  - canonical gate: 483 tests OK; aikit check 5/5; `policy_digest` decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - `Agent._step_vectors` `else` branch calls `len(self.selfmodel.history())`, and `SelfModel.history()` returns `copy.deepcopy(self._history)`: O(n) work per step for an O(1) answer.
  - measured: `T3:15` (13 steps) made 13 `history()` calls with the default `Agent()`; with a persistent `self_model` the count was 0, so the branch is live and unskipped. n=200, 60 calls: 0.261550 s versus 0.000013 s for the length alone.
- **Gap**: the loop deep-copies the entire self-model record once per step on the default path, purely to read an integer. Nothing about the S vector needs the copy: `len()` of the record is available in O(1), and no caller in the loop inspects the copied contents.
- **Target delta**: the S vector's second component stays identical while the per-step read becomes O(1); every behavioral pin unchanged.
- **Falsifier**: any pinned step/reward/range/holdout/cold-start/`policy_digest` value moves; the S vector changes; or the default path still calls `history()`.
- **Change**: `agent.py` `SelfModel` gains `size()` returning `len(self._history)` with a docstring naming the O(n)/O(1) distinction; `_step_vectors` calls `selfmodel.size()`. `history()` keeps its deepcopy for callers that need the record. `tests/test_selfmodel_size.py` adds 5 tests (length parity, zero `deepcopy` calls under an instrumented `copy.deepcopy`, the measured gap, the default-Agent call counts, the pinned quadruple). ADR-102. No README section: internal, behavior-preserving, and README.md is at its 32,500-char cap.
- **After** (same rigs):
  - per-call at n=200, 60 calls: 0.000013 s (was 0.261550 s), ~20000x.
  - default `Agent()` run: 0 `history()` calls, 13 `size()` calls on a 13-step episode; the S vector and every action identical.
  - standing 89 steps / 11.0 reward; T1 0-99 1581; holdout 500-599 738 (min 1, max 14); `policy_digest` unchanged.
- **Ablation** (restore `len(self.selfmodel.history())` as the cut, same calls): 0.261550 s versus 0.000013 s with identical actions and rewards, so the cost returns with the cut and the read is the only difference.
- **Verdict**: behavior-preserving hot-path cost win, second instance of the ADR-101 defect class. The measured delta is the per-step size read; no telemetry or emergence claim and no pinned value moves. Boundary: this fixes the length read only. `history()` remains O(n) with a deepcopy, so a future caller inspecting the record per step reintroduces the cost.
- **Gates**: unittest 488/488 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_selfmodel_size` -> before: 4 errors (`SelfModel` has no `size`); after: 5 OK.
  - `python ..\..\scratch\probe_branch_live.py` -> default Agent 13 `history()` calls on T3:15; persistent self-model 0.
  - `python ..\..\scratch\ablate_108.py` -> 0.000013 s vs 0.261550 s; standing 89/11.0; T1 1581; holdout 738; policy unchanged.
  - `python -m unittest discover -s tests -t .` -> 488 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 109**: unittest 488 OK; aikit 5/5; `SelfModel.size()` O(1) and default Agent makes 0 `history()` calls; recall cost n=200 x60 ~0.002 s; standing 89 steps / 11.0 reward; T1 0-99 1581; holdout 500-599 738 (min 1, max 14); cold-start 16/8/13/6 with 3/1/1/1 and `store_reads` 1; `detectability` `[M, hub]` / `[P, S]`; `syn` 0.054115320909768228 `syn_n` 0.10814360275702875 `phi` 0.0; policy decbfce3...; all earlier pins unchanged.

## Cycle 109 - audit the telemetry vector matrix for degenerate columns

- **Baseline** (commit 3aaeb4c; `T1_forage:71`, 16 steps):
  - canonical gate: 488 tests OK; aikit check 5/5; `policy_digest` decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - default `Agent(memory_store=...)`: constant columns `[P0, P1, S0]`; duplicate pairs `M0==M1==S1` and `P0==P1==S0`; the only varying content is the step counter.
  - full wiring (store + tracker + persistent self-model): no constants, but `M0==M1==P0==S1`, leaving 6 distinct columns of 9.
- **Gap**: the M/P/S block is presented as three module readouts (memory, planner, self-model). One save, one record and one mark happen per loop step, so those counters are the step index by construction; the matrix cannot express memory, planner and self-model activity as three independent signals. Cross-module numbers computed from it (including the `syn` this repo reports) are therefore not evidence of module coupling, and nothing in the tree said so.
- **Target delta**: the degeneracy becomes a measured, machine-readable fact with a pinned live value; no vector, estimate or behavior change.
- **Falsifier**: any pinned value moves; the audit reports no duplicate pairs on the real matrix; or a "distinct" count above the true number of independent columns.
- **Change**: `evals/vector_audit.py` adds `BLOCK_LABELS`, `column_report`, `duplicate_pairs`, `distinct_columns`, `degenerate_columns`, `audit_rows`, `audit_vectors` and `MIN_DISTINCT = 3`; `tests/test_vector_audit.py` adds 7 pure tests and 2 live-substrate pins (default-path constants/pairs, full-wiring `M0==M1==P0==S1`). ADR-103. No README section: README.md is at its 32,500-char cap and this is an evidence addition, not a caller contract.
- **After** (same matrix):
  - default path: `constant [P0, P1, S0]`, `distinct` 4 including hub, `sufficient: true`.
  - full wiring: `duplicates [(M0,M1), (M0,P0), (M0,S1), (M1,P0), (M1,S1), (P0,S1)]`, `distinct` 6 of 9.
  - fixed-rig `syn` 0.054115320909768228, `syn_n` 0.10814360275702875, `phi` 0.0, standing 89/11.0, T1 1581, holdout 738 and `policy_digest` unchanged.
- **Ablation**: without `evals/vector_audit.py` the matrix is read as three module blocks; with it the same rows report the duplicate pairs, and deleting the module restores the unfalsifiable reading. The audit reports the rows it is given, so the property dies with the module and returns with it.
- **Verdict**: telemetry-honesty extension on the substrate's own instrumentation. The measured delta is the disclosure that 3 of 9 components are one counter; no behavior, estimate or pin moves. Boundary recorded: the audit makes the degeneracy visible, it does not fix it; making the counters independent would change the vectors and therefore the pinned `syn`, which is a separate decision needing its own re-baseline.
- **Gates**: unittest 497/497 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_vector_audit` -> before: ModuleNotFoundError (`evals.vector_audit`); after: 9 OK.
  - `python ..\..\scratch\probe_full_wiring.py` -> default path 0 distinct non-constant columns before hub; full wiring `M0==M1==P0==S1`.
  - `python ..\..\scratch\ablate_109.py` -> pins hold; audit duplicate pairs; ablation recorded.
  - `python -m unittest discover -s tests -t .` -> 497 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 110**: unittest 497 OK; aikit 5/5; `vector_audit` default path `constant [P0,P1,S0]` and `M0==M1==S1`; full wiring `M0==M1==P0==S1` and `distinct` 6; `SelfModel.size()` O(1); recall cost n=200 x60 ~0.002 s; standing 89 steps / 11.0 reward; T1 0-99 1581; holdout 500-599 738 (min 1, max 14); cold-start 16/8/13/6 with 3/1/1/1; `detectability` `[M, hub]` / `[P, S]`; `syn` 0.054115320909768228 `syn_n` 0.10814360275702875 `phi` 0.0; policy decbfce3...; all earlier pins unchanged.

## Cycle 110 - replay a log's actions through the world its header names

- **Baseline** (commit e4ea7c2):
  - canonical gate: 497 tests OK; aikit check 5/5; `policy_digest` decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - `verify_chain` proves the recorded bytes were not edited; `verify_episode_header` proves the header config. Neither reads the actions.
  - measured: a `T3_navigate:15` log whose every step action was replaced by `wait` and re-emitted through `Telemetry` (chain recomputed honestly) returned `verify_chain ok: True` and `verify_episode_header ok: True`, while replaying those actions leaves the world at `(0, 0)` with no reward.
- **Gap**: the trajectory was unverified. A log could claim a solved episode it never ran, and every shipped verifier accepted it, because chain and header checks are about bytes and config, not about what the actions do in the world the header names.
- **Target delta**: a third independent check that replays the logged actions through `GridWorld(task, seed)` and names the first divergence; the same forgery must fail it.
- **Falsifier**: the honest log fails replay; the forged log passes replay; or a pinned behavior/`policy_digest` value moves.
- **Change**: `episode_replay.py` adds `logged_steps`, `replay_actions` and `verify_action_replay` (per-step reward comparison against the world's own value, terminal `done` comparison, length comparison, named findings); `tests/test_episode_replay.py` adds 6 tests including the chain-valid forgery. ADR-104.
- **After** (same logs):
  - honest log: `chain=True header=True replay=True`, `steps=13`, `replayed=13`, terminal `(6, 7)`.
  - forged log: `chain=True header=True replay=False`, findings `['reward-mismatch:12', 'done-mismatch']`.
  - standing 89 steps / 11.0 reward and `policy_digest` unchanged.
- **Ablation**: without `episode_replay` the forgery is accepted by both shipped verifiers; with it the same bytes report the first divergent step and the terminal mismatch. Deleting the module restores acceptance, restoring it returns the rejection.
- **Verdict**: evidence-integrity extension. The measured delta is a chain-valid trajectory forgery that passed every prior check and now fails with named findings; no behavior, estimator or pin moves. Boundary: replay proves the actions are consistent with the named world and seed, not that a model produced them; a forger who computes a different winning trajectory the world accepts would still verify, so this raises the cost of a trajectory lie without making logs unforgeable.
- **Gates**: unittest 503/503 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_episode_replay -v` -> 6 OK.
  - `python ..\..\scratch\probe_forge.py` -> forged chain valid, header valid, world ends at (0,0).
  - `python ..\..\scratch\ablate_110.py` -> honest True/True/True; forged True/True/False with named findings; standing 89/11.0.
  - `python -m unittest discover -s tests -t .` -> 503 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 111**: unittest 503 OK; aikit 5/5; `verify_action_replay` honest True (13/13, terminal 6,7) and chain-valid forgery False (`reward-mismatch:12`, `done-mismatch`); `vector_audit` default `[P0,P1,S0]` / `M0==M1==S1`, full wiring `M0==M1==P0==S1`; `SelfModel.size()` O(1); recall cost n=200 x60 ~0.002 s; standing 89 steps / 11.0 reward; T1 0-99 1581; holdout 500-599 738 (min 1, max 14); cold-start 16/8/13/6 with 3/1/1/1; `detectability` `[M, hub]` / `[P, S]`; `syn` 0.054115320909768228 `syn_n` 0.10814360275702875 `phi` 0.0; policy decbfce3...; all earlier pins unchanged.

## Cycle 111 - compose action replay into claim-ref verification

- **Baseline** (commit 263fb96):
  - canonical gate: 503 tests OK; aikit check 5/5; `policy_digest` decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - `verify_claim_refs` matches a verdict ref against header `episode_sha256` values only; ADR-104's `verify_action_replay` existed but no caller in the claim layer used it.
  - measured: a `T3_navigate:15` log re-emitted with `wait` for every action, with a claim citing its original episode digest, returned `verified=1 unverified=0 ok=True`, while `verify_action_replay` on the same bytes returned `reward-mismatch:12, done-mismatch`.
- **Gap**: a verdict could cite an episode the agent never ran. The replay check was shipped in cycle 110 but never composed into the verifier that actually guards claims, so the evidence layer still trusted a false trajectory whose header was intact.
- **Target delta**: an opt-in ref verification that replays the actions before trusting any ref, so the same forgery is rejected; default behavior byte-identical.
- **Falsifier**: the honest log is rejected; the forgery passes with the flag; or an existing claim-ref/claims/claim-evidence pin moves.
- **Change**: `claims_verify.py` adds `verify_replay=False` to `verify_claim_refs` and `verify_claim_store`, raises on a failed replay with the named findings, requires `verify_logs=True`, validates the bool, and reports `replay` in the result. `tests/test_claim_replay.py` adds 5 tests. ADR-105. No README section: README.md sits at its 32,500-char cap after cycle 110's action-replay section, which already states the replay contract this option composes.
- **After** (same logs):
  - honest log, `verify_replay=True`: `ok=True`, `verified=1`, `replay=True`.
  - forged log, default: `ok=True`, `verified=1` (previous behavior preserved).
  - forged log, `verify_replay=True`: raises `failed replay verification: reward-mismatch:12, done-mismatch`.
  - claim-ref/claims/claim-evidence suites 49 tests OK; standing 89/11.0 and `policy_digest` unchanged.
- **Ablation**: the same forged bytes verify without the flag and are refused with it, with identical headers and refs, so the guard is the flag and nothing else. Removing the check restores the false acceptance; restoring it returns the rejection.
- **Verdict**: evidence-integrity composition. The measured delta is a claim that verified against a provably false trajectory now being refused when replay is requested; no behavior, estimator or pin moves. Boundary: replay still proves only that the actions fit the named world; a forger who computes a different winning trajectory the world accepts is not caught, and this composes the existing check rather than strengthening it.
- **Gates**: unittest 508/508 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_claim_replay` -> before: 5 errors (`verify_replay` unexpected); after: 5 OK.
  - `python -m unittest tests.test_claim_ref_verify tests.test_claim_evidence tests.test_claims tests.test_claim_replay` -> 49 OK.
  - `python ..\..\scratch\ablate_111.py` -> honest True; forged default accepted; forged with replay rejected; standing 89/11.0.
  - `python -m unittest discover -s tests -t .` -> 508 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 112**: unittest 508 OK; aikit 5/5; `verify_claim_refs(verify_replay=True)` honest True and chain-valid forgery rejected; default `verify_replay=False` preserves `ok=True` on the forgery; `verify_action_replay` 13/13 terminal (6,7); `vector_audit` default `[P0,P1,S0]`; `SelfModel.size()` O(1); recall cost n=200 x60 ~0.002 s; standing 89 steps / 11.0 reward; T1 0-99 1581; holdout 500-599 738 (min 1, max 14); cold-start 16/8/13/6 with 3/1/1/1; `detectability` `[M, hub]` / `[P, S]`; `syn` 0.054115320909768228 `syn_n` 0.10814360275702875 `phi` 0.0; policy decbfce3...; all earlier pins unchanged.

## Cycle 112 - check a verdict's machine claim against the replay

- **Baseline** (commit 06c72e9):
  - canonical gate: 508 tests OK; aikit check 5/5; `policy_digest` decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - `Agent._episode_verdict` writes the verdict reason as `"steps=%d reward=%.1f"`; `verify_action_replay` compared step records against the world but never read that claim.
  - measured: a `T3_navigate:15` log re-emitted with its verdict reason rewritten to `"steps=1 reward=99.0 success=true"` kept a valid chain and passed `verify_action_replay` (`ok: True`), because only the summary was false.
- **Gap**: the verdict's own claim was unverified. A log could report steps and reward the run never produced, and even the replay-enabled claim check accepted it, so the last self-reported number in the evidence chain was the one nobody checked.
- **Target delta**: an opt-in verdict check that parses the machine claim and rejects a step count or reward the replay does not support; default behavior unchanged.
- **Falsifier**: the honest log fails the verdict check; an inflated claim passes with it enabled; or a pinned value moves.
- **Change**: `episode_replay.py` adds `parse_verdict_reason` and `verify_action_replay(..., check_verdict=False)` naming `missing-verdict`, `unparsable-verdict-reason`, `verdict-steps-mismatch`, `verdict-reward-mismatch`, and reporting `claimed`; `claims_verify.py` passes `check_verdict=True` under `verify_replay`; `tests/test_verdict_claim.py` adds 7 tests. ADR-106.
- **After** (same logs):
  - honest log: `chain=True`, `replay-verdict=True`, `claimed {'steps': 13, 'reward': 1.0}`.
  - forged verdict: `chain=True`, default replay `True` (unchanged), verdict check `False` with `['verdict-steps-mismatch', 'verdict-reward-mismatch']`, `claimed {'steps': 1, 'reward': 99.0}`.
  - `verify_claim_refs(verify_replay=True)` on the forged log raises with those two findings.
  - standing 89/11.0 and `policy_digest` unchanged.
- **Ablation**: with `check_verdict` off the claim is unread and the forged log is accepted; with it on the same bytes are rejected. The trajectory is identical in both readings, so the delta is the read.
- **Verdict**: evidence-integrity extension covering the last self-reported number. The measured delta is an inflated verdict claim that every prior check accepted and the verdict check refuses; no behavior, estimator or pin moves. Boundary: the check compares claim against replay, so a forger who rewrites both consistently still passes; the one-decimal reason format bounds reward resolution to 0.05, which is the tolerance used.
- **Gates**: unittest 515/515 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_verdict_claim` -> before: 1 error (`parse_verdict_reason` absent); after: 7 OK.
  - `python ..\..\scratch\ablate_112.py` -> honest True/True; forged chain True, default replay True, verdict False with two findings; claim refused; standing 89/11.0.
  - `python -m unittest discover -s tests -t .` -> 515 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 113**: unittest 515 OK; aikit 5/5; `parse_verdict_reason` round-trips `"steps=13 reward=1.0"`; honest verdict check True with `claimed {13, 1.0}`; inflated claim yields `verdict-steps-mismatch` + `verdict-reward-mismatch`; default `check_verdict=False` unchanged; `verify_claim_refs(verify_replay=True)` rejects it; `verify_action_replay` 13/13 terminal (6,7); `vector_audit` default `[P0,P1,S0]`; `SelfModel.size()` O(1); recall cost n=200 x60 ~0.002 s; standing 89 steps / 11.0 reward; T1 0-99 1581; holdout 500-599 738 (min 1, max 14); cold-start 16/8/13/6 with 3/1/1/1; `detectability` `[M, hub]` / `[P, S]`; `syn` 0.054115320909768228 `syn_n` 0.10814360275702875 `phi` 0.0; policy decbfce3...; all earlier pins unchanged.

## Cycle 113 - name circular confidence in the self-model's calibration readout

- **Baseline** (commit aeaaf12):
  - canonical gate: 515 tests OK; aikit check 5/5; `policy_digest` decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - `Agent` records `conf = 1.0 if reward > 0 else 0.5` and `ok = reward > 0`, so the stored probability is the outcome by construction.
  - measured `SelfModel.calibration()`: T1:71 brier 0.203125 skill -0.333333; T3:15 0.230769 / -2.25; T3:74 0.222222 / -1.25 — reported as ordinary calibration with no qualifier.
- **Gap**: the calibration readout presented a property of how the record is built as a measurement of forecasting. Because the confidence is a function of the outcome in every real run (perfect separation, distinct confidences `[0.5, 1.0]`), Brier restates the base rate and the skill term compares that restatement with itself. Nothing said so.
- **Target delta**: the circularity is named at the read site with its numbers unchanged; a genuine perfect forecast must stay unflagged.
- **Falsifier**: a real run is not flagged; a perfect forecast IS flagged (a false positive would make the warning useless); or any pinned value moves.
- **Killed candidate**: putting the warning in `calibration.summary`. A genuinely perfect forecast also separates the classes (Brier 0.0), so the scorer would flag valid input and break 6 existing assertions; the diagnosis belongs where the confidence's provenance is known.
- **Change**: `calibration.py` adds `confidence_is_outcome(forecasts)` (two circular shapes: one confidence per class with no sharing, or one confidence across both classes); `self_model/model.py` `calibration()` appends a `confidence-is-outcome` warning with its docstring corrected to say the pair is recorded after the outcome; `tests/test_degenerate_confidence.py` adds 9 tests. ADR-107.
- **After** (same runs):
  - T1:71, T3:15 and T3:74 keep their brier/skill values and now carry `confidence-is-outcome` alongside; T3:74 also keeps its small-sample warning.
  - perfect forecast: brier 0.0, warned False (the control holds).
  - calibration/self-model/store/bridge/retention suites 72 tests OK; standing 89/11.0 and `policy_digest` unchanged.
- **Ablation**: without the diagnosis the same numbers read as a score; with it they are qualified, and the numbers are byte-identical either way, so the delta is the disclosure and nothing else.
- **Verdict**: telemetry-honesty extension on the self-model's own readout. The measured delta is a circular calibration score that now names itself; no action, reward, estimate or pin moves. Boundary: this labels the record, it does not fix it. An informative confidence needs recording before the outcome, which changes what the self-model stores and every calibration pin — a separate decision.
- **Gates**: unittest 524/524 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_degenerate_confidence` -> before: 4 failures (no warning); after: 9 OK.
  - `python -m unittest tests.test_degenerate_confidence tests.test_calibration tests.test_selfmodel tests.test_calibration_store tests.test_calibration_bridge tests.test_calibration_retention tests.test_calibration_autoretention` -> 72 OK.
  - `python ..\..\scratch\ablate_113.py` -> all three runs flagged, numbers unchanged; perfect forecast not flagged; standing 89/11.0.
  - `python -m unittest discover -s tests -t .` -> 524 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 114**: unittest 524 OK; aikit 5/5; `confidence_is_outcome` True for perfect separation and constant-across-classes, False for spread/single-class/partial; `SelfModel.calibration()` flags real runs and not a spread record; `summary` never flags a perfect forecast; `parse_verdict_reason` round-trip; `verify_action_replay` verdict check; `vector_audit` default `[P0,P1,S0]`; `SelfModel.size()` O(1); recall cost n=200 x60 ~0.002 s; standing 89 steps / 11.0 reward; T1 0-99 1581; holdout 500-599 738 (min 1, max 14); cold-start 16/8/13/6 with 3/1/1/1; `detectability` `[M, hub]` / `[P, S]`; `syn` 0.054115320909768228 `syn_n` 0.10814360275702875 `phi` 0.0; policy decbfce3...; all earlier pins unchanged.

## Cycle 114 - carry the integrity evidence into snapshot records

- **Baseline** (commit e87eab3):
  - canonical gate: 524 tests OK; aikit check 5/5; `policy_digest` decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - `snapshot.run_record` emitted only steps/reward/success/action hash/syn/phi; `diff_records` is the gate that names a behavioral change.
  - measured: a record with `replay_ok` `True` -> `False`, and one with `syn_scope.sufficient` `True` -> `False`, both diffed `{'changed': 0, 'unchanged': 1}` — the gate could not see either.
- **Gap**: cycles 110-113 added three evidence readouts, but the snapshot gate that decides whether anything changed was blind to all of them. An integrity regression that left behavior identical would pass the diff as `unchanged`, so the evidence work could silently rot.
- **Target delta**: a snapshot record carries the scope, the replay verdict and the parsed claim, so a regression in any of them is named by `diff_records`; behavior fields and identical-capture behavior unchanged.
- **Falsifier**: an integrity regression still diffs `unchanged`; an identical capture diffs `changed`; or an existing snapshot/digest pin moves.
- **Change**: `snapshot.py` `run_record` gains `syn_scope`, `replay_ok`, `verdict_claimed` (each `None` when no evidence is supplied); `capture_snapshot` fills them from the log it wrote via `recompute(...)` and `verify_action_replay(..., check_verdict=True)`; `tests/test_snapshot_evidence.py` adds 6 tests. ADR-108. `diff_records` needs no change.
- **After** (same pairs):
  - captured records: `T3_navigate:15` steps 13 / reward 1.0, `T3_navigate:65` steps 6 / reward 1.0, both `syn_scope.sufficient True`, `replay_ok True`, claim `{steps, 1.0}`.
  - `replay_ok` True->False: diff `changed 1`, fields `['replay_ok']`; `syn_scope.sufficient` True->False: diff `changed 1`, fields `['syn_scope']`; identical: `changed 0`.
  - snapshot/digest/new suites 18 tests OK; standing 89/11.0 and `policy_digest` unchanged.
- **Ablation**: without the fields both integrity regressions diff `unchanged`; with them each is named, while every behavior field is byte-identical in both readings, so the delta is the visibility.
- **Verdict**: evidence-plumbing extension so the diff gate covers the evidence it is supposed to guard. The measured delta is two integrity regressions that were invisible and are now named; no behavior, estimator or pin moves. Boundary: this widens what the gate sees, it does not strengthen the evidence; a run broken in behavior and evidence together still diffs consistently, and `verdict_claimed` inherits the one-decimal resolution of the verdict reason.
- **Gates**: unittest 530/530 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_snapshot_evidence` -> before: 2 failures + 1 error (no fields); after: 6 OK.
  - `python -m unittest tests.test_snapshot tests.test_snapshot_digest tests.test_snapshot_evidence` -> 18 OK.
  - `python ..\..\scratch\ablate_114.py` -> both regressions named, identical diffs clean, behavior unchanged.
  - `python -m unittest discover -s tests -t .` -> 530 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 115**: unittest 530 OK; aikit 5/5; snapshot record carries `syn_scope`/`replay_ok`/`verdict_claimed`; `T3:15` 13/1.0 and `T3:65` 6/1.0 with `sufficient True` and `replay_ok True`; integrity regressions diff `changed`; identical captures clean; `confidence_is_outcome` diagnoses; `parse_verdict_reason` round-trip; `vector_audit` default `[P0,P1,S0]`; `SelfModel.size()` O(1); recall cost n=200 x60 ~0.002 s; standing 89 steps / 11.0 reward; T1 0-99 1581; holdout 500-599 738 (min 1, max 14); cold-start 16/8/13/6 with 3/1/1/1; `detectability` `[M, hub]` / `[P, S]`; `syn` 0.054115320909768228 `syn_n` 0.10814360275702875 `phi` 0.0; policy decbfce3...; all earlier pins unchanged.

## Cycle 115 - pair each result record with the step it describes

- **Baseline** (commit bbd004a):
  - canonical gate: 530 tests OK; aikit check 5/5; `policy_digest` decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - the loop writes one `type == "result"` record per step with `ok`, `output` (the action) and `cost`; `verify_action_replay` reads the action records only.
  - measured: a `T3_navigate:15` log re-emitted with every result rewritten to `(ok=True, output='TELEPORT', cost=999.0)` kept a valid chain and passed `verify_action_replay(..., check_verdict=True)`.
- **Gap**: the result records were the last unchecked self-report in the evidence chain. An inventory of every number the log asserts about itself showed chain (verified), header/episode (recomputed), verdict reason (recomputed), step action/reward/done (replayed) — and result `ok`/`output`/`cost` checked by nothing.
- **Target delta**: each result is compared with the step it describes, naming any contradiction; the honest log stays clean and every existing default unchanged.
- **Falsifier**: the honest log fails pairing; the rewritten result passes; or a pinned value moves.
- **Change**: `episode_replay.py` adds `verify_result_records` naming `output-mismatch:<n>`, `ok-mismatch:<n>`, `cost-mismatch:<n>`, `unpaired-step:<n>`, `extra-result:<n>` and `missing-header`; `verify_action_replay` composes it under `check_verdict=True`; `tests/test_result_records.py` adds 6 tests and the cycle-112 test's expectation is updated (the forgery now fails replay as intended). ADR-109.
- **After** (same logs):
  - honest: pairing True, 13/13 pairs.
  - rewritten results: pairing False with `output-mismatch:0, cost-mismatch:0, output-mismatch:1, ...`; chain True, composed replay False.
  - standing 89/11.0 and `policy_digest` unchanged; `check_verdict=False` unchanged.
- **Ablation**: without the pairing check `output='TELEPORT'` and `cost=999.0` pass every verifier; with it they are named, and the action records are byte-identical in both readings, so the delta is the pairing.
- **Verdict**: evidence-integrity extension closing the last self-report. The measured delta is a result record that contradicted its step and passed every prior check; no behavior, estimator or pin moves. Boundary: this catches a result contradicting its step; a forger who rewrites both consistently still passes, and `expected_cost=1.0` encodes the current charge.
- **Gates**: unittest 536/536 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_result_records` -> before: 1 error (`verify_result_records` absent); after: 6 OK.
  - `python -m unittest tests.test_result_records tests.test_verdict_claim tests.test_episode_replay tests.test_claim_replay tests.test_snapshot_evidence` -> 30 OK.
  - `python ..\..\scratch\ablate_115.py` -> honest 13/13 clean; forged named; chain True, replay False; standing 89/11.0.
  - `python -m unittest discover -s tests -t .` -> 536 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 116**: unittest 536 OK; aikit 5/5; `verify_result_records` honest 13/13 True and rewritten False with `output-mismatch`/`cost-mismatch`; composed replay rejects it while chain stays True; `check_verdict=False` unchanged; snapshot evidence fields; `confidence_is_outcome`; `parse_verdict_reason`; `vector_audit` default `[P0,P1,S0]`; `SelfModel.size()` O(1); recall cost n=200 x60 ~0.002 s; standing 89 steps / 11.0 reward; T1 0-99 1581; holdout 500-599 738 (min 1, max 14); cold-start 16/8/13/6 with 3/1/1/1; `detectability` `[M, hub]` / `[P, S]`; `syn` 0.054115320909768228 `syn_n` 0.10814360275702875 `phi` 0.0; policy decbfce3...; all earlier pins unchanged.

## Cycle 116 - recompute the verdict word from the trajectory and the budget

- **Baseline** (commit e3d4f22):
  - canonical gate: 536 tests OK; aikit check 5/5; `policy_digest` decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - `Agent._episode_verdict` writes `done` only for a pre-cap completion; a full-budget run is `truncated` even though the world sets its `done` flag at the cap.
  - measured: `T3_navigate:15` capped at 5, 8 and 10 steps each wrote `truncated` with reason `steps=<n> reward=0.0`; rewriting **only** the word to `done` and keeping that honest reason returned `ok: True` with no findings at all three caps.
- **Gap**: the verdict word — the field a reader scans first — was the one part of the verdict nothing checked. Cycles 112 and 115 covered the reason's numbers and the result records, but a truncated run could still be labelled `done` and pass every verifier.
- **Target delta**: the word is recomputed from the replayed trajectory and the header budget and compared; honest logs at every cap stay clean.
- **Falsifier**: an honest capped run is rejected; a relabelled word passes; or a pinned value moves.
- **Change**: `episode_replay.py` adds `VERDICT_WORDS` and `expected_verdict_word(replay, budget)` and checks the word under `check_verdict=True` as `verdict-word-mismatch` (unknown word or disagreement with the recomputation; header `budget` when valid, else `max_steps`); `tests/test_verdict_word.py` adds 5 tests. ADR-110.
- **After** (same caps):
  - honest: cap 5/8/10 → `truncated`, `replay_ok True`; cap 200 → `done` at 13 steps, `replay_ok True`.
  - forged word `done`: `chain_ok True`, `replay_ok False`, findings `['verdict-word-mismatch']` at every cap.
  - replay/verdict/result/snapshot/wiring suites 37 tests OK; standing 89/11.0 and `policy_digest` unchanged.
- **Ablation**: without the word check a truncated run relabelled `done` passes; with it the same bytes are named, and the trajectory and reason are byte-identical in both readings, so the delta is the word read.
- **Verdict**: evidence-integrity extension completing the verdict layer. The measured delta is a verdict word that contradicted its own trajectory and passed every prior check; no behavior, estimator or pin moves. Boundary: the rule is recomputed from the header's declared budget, so a forged budget plus a matching word still agrees; this catches an inconsistent word, not a fully consistent relabelling of budget, trajectory and word together.
- **Gates**: unittest 541/541 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_verdict_word` -> before: 3 failures (word unchecked); after: 5 OK.
  - `python -m unittest tests.test_verdict_word tests.test_verdict_claim tests.test_episode_replay tests.test_result_records tests.test_claim_replay tests.test_snapshot_evidence tests.test_wiring` -> 37 OK.
  - `python ..\..\scratch\ablate_116.py` -> honest clean at 5/8/10/200; forged named at every cap; standing 89/11.0.
  - `python -m unittest discover -s tests -t .` -> 541 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 117**: unittest 541 OK; aikit 5/5; `expected_verdict_word` done iff ended and under budget; honest caps 5/8/10 truncated and 200 done; relabelled word yields `verdict-word-mismatch` with chain valid; `verify_result_records` 13/13; snapshot evidence; `confidence_is_outcome`; `parse_verdict_reason`; `vector_audit` default `[P0,P1,S0]`; `SelfModel.size()` O(1); recall cost n=200 x60 ~0.002 s; standing 89 steps / 11.0 reward; T1 0-99 1581; holdout 500-599 738 (min 1, max 14); cold-start 16/8/13/6 with 3/1/1/1; `detectability` `[M, hub]` / `[P, S]`; `syn` 0.054115320909768228 `syn_n` 0.10814360275702875 `phi` 0.0; policy decbfce3...; all earlier pins unchanged.

## Cycle 117 - pin the header's model label

- **Baseline** (commit e10fe38):
  - canonical gate: 541 tests OK; aikit check 5/5; `policy_digest` decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - `verify_episode_header` validated task/seed/budget/policy/episode digests and supported external policy and workspace pins; the header's `model` field was stored verbatim and compared with nothing.
  - measured: a `T3_navigate:15` log whose header `model` was rewritten from `rule` to `totally-different-model-99b` passed `verify_chain`, `verify_episode_header` and `verify_action_replay(check_verdict=True)`.
- **Gap**: a log could attribute an episode to any backend. The episode digest covers the initial state and config, so no existing check could catch a swapped model label — the same structural hole the policy and workspace pins had before ADR-084/094.
- **Target delta**: an external model pin names a swapped or missing label; omitting it changes nothing.
- **Falsifier**: the honest log fails with a matching pin; the relabelled log passes with a pin; or a pinned value moves.
- **Change**: `episode_verify.py` adds `expected_model=None` (non-empty string, `model-mismatch`/`missing-model`, echoed in the result); `claims_verify.py` threads it through `verify_claim_refs`/`verify_claim_store` with the same `verify_episodes=True` requirement; `tests/test_model_pin.py` adds 5 tests. ADR-111.
- **After** (same logs):
  - honest: unpinned True, pinned True.
  - relabelled `totally-different-model-99b`: chain True, replay True, unpinned True (unchanged), pinned False with `['model-mismatch']` and the digest still recomputing.
  - `verify_claim_refs(verify_episodes=True, expected_model='rule')` on the relabelled log raises `failed episode verification: model-mismatch`.
  - episode/claim-ref/replay suites 54 tests OK; standing 89/11.0 and `policy_digest` unchanged.
- **Ablation**: without the pin any label passes all three verifiers; with it the swap is named, and the trajectory and digest are byte-identical in both readings, so the delta is the pin.
- **Verdict**: evidence-integrity extension closing the last unpinned header field. The measured delta is a model label that could be rewritten freely and now cannot be when the caller pins it; no behavior, estimator or pin moves. Boundary: a pin only works when the caller knows the expected label; the header still stores the label verbatim, and this does not bind the label to the weights — the manifest digest in `model_decision` records remains the weight-level binding.
- **Gates**: unittest 546/546 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_model_pin` -> before: 5 errors (`expected_model` unexpected); after: 5 OK.
  - `python -m unittest tests.test_episode_verify tests.test_claim_ref_verify tests.test_claim_replay tests.test_model_pin` -> 54 OK.
  - `python ..\..\scratch\ablate_117.py` -> unpinned accepts, pinned names `model-mismatch`, claim refused; standing 89/11.0.
  - `python -m unittest discover -s tests -t .` -> 546 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 118**: unittest 546 OK; aikit 5/5; `expected_model` matching True, wrong `model-mismatch`, missing `missing-model`, omitted unchanged, invalid raises; claim-ref pin refuses a relabelled log; `expected_verdict_word`; `verify_result_records` 13/13; snapshot evidence; `confidence_is_outcome`; `parse_verdict_reason`; `vector_audit` default `[P0,P1,S0]`; `SelfModel.size()` O(1); recall cost n=200 x60 ~0.002 s; standing 89 steps / 11.0 reward; T1 0-99 1581; holdout 500-599 738 (min 1, max 14); cold-start 16/8/13/6 with 3/1/1/1; `detectability` `[M, hub]` / `[P, S]`; `syn` 0.054115320909768228 `syn_n` 0.10814360275702875 `phi` 0.0; policy decbfce3...; all earlier pins unchanged.

## Cycle 118 - give the batteries one exit-code contract

- **Baseline** (commit 71a57a4):
  - canonical gate: 546 tests OK; aikit check 5/5; `policy_digest` decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - a static survey of `evals/*.py` found ten batteries with no `assert`, no `raise` and no non-zero exit: `calibration`, `estimators`, `execution_budget`, `header_reader`, `progress_guard`, `prompt_budget`, `recompute`, `resume_identity`, `telemetry_lock`, `vector_audit`.
  - measured: `python -m evals.telemetry_lock` exited 0 intact and 0 with `--ablate` (the deliberately broken case), so a scripted gate could not tell a pass from a regression.
- **Gap**: ten batteries could regress silently. The repo's evidence discipline assumed a human reads each JSON payload; no gate consumed the batteries' own verdicts, and the audit that could name the gap did not exist.
- **Target delta**: one shared exit-code contract, adopted in the battery proved silent, plus an audit that keeps naming the rest.
- **Falsifier**: an intact run exits non-zero; a regressed run exits 0; or a pinned value moves.
- **Change**: `evals/battery_check.py` adds `EXIT_OK`/`EXIT_FINDING`, `exit_code_for`, `battery_result`, `format_findings` and `audit_batteries`; `evals/telemetry_lock.py` adds `checks(report)` naming `worker-errors`, `record-count:<n>!=<m>`, `chain-broken:<findings>` and `ablation-did-not-break-the-chain`, and exits through the contract; `tests/test_battery_contract.py` adds 9 tests. ADR-112.
- **After** (same battery):
  - intact: exit 0; `--ablate`: exit 0 (the chain is broken as designed, and a *clean* chain under the cut is now the failure).
  - forced regressions: broken chain, short count, worker error and vacuous ablation each return exit 1 with a named finding.
  - audit: `telemetry_lock` moves to `with_contract`; the remaining nine are still listed in `without_contract`.
  - standing 89/11.0 and `policy_digest` unchanged.
- **Ablation**: with `checks`, a broken chain or a vacuous ablation exits 1; without it the same payload exits 0, and the JSON output is byte-identical in both readings, so the delta is the exit code.
- **Verdict**: harness-honesty extension. The measured delta is a battery that printed a broken chain and exited 0, now exiting 1, plus a standing audit of the nine batteries still uncovered. No behavior, estimator or pin moves. Boundary: the contract is established and adopted in one battery; the other nine still only print, and the audit's coverage test is syntactic (a name reference or a `raise`), not proof that a battery's assertions are correct.
- **Gates**: unittest 556/556 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_battery_contract` -> before: 1 error (`evals.battery_check` absent); after: 9 OK.
  - `python -m evals.telemetry_lock` -> exit 0; `--ablate` -> exit 0; forced regressions -> exit 1 each.
  - `python ..\..\scratch\ablate_118.py` -> good 0, broken-chain 1, short 1, worker-error 1, vacuous-ablation 1.
  - `python -m unittest discover -s tests -t .` -> 556 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 119**: unittest 556 OK; aikit 5/5; `exit_code_for` 0/1 rules; `telemetry_lock` intact 0, ablate 0, forced regressions 1; `audit_batteries` lists `telemetry_lock` as covered and names `calibration`/`estimators`/`recompute` as uncovered; `expected_model` pin; `expected_verdict_word`; `verify_result_records` 13/13; snapshot evidence; `confidence_is_outcome`; `parse_verdict_reason`; `vector_audit` default `[P0,P1,S0]`; `SelfModel.size()` O(1); recall cost n=200 x60 ~0.002 s; standing 89 steps / 11.0 reward; T1 0-99 1581; holdout 500-599 738 (min 1, max 14); cold-start 16/8/13/6 with 3/1/1/1; `detectability` `[M, hub]` / `[P, S]`; `syn` 0.054115320909768228 `syn_n` 0.10814360275702875 `phi` 0.0; policy decbfce3...; all earlier pins unchanged.

## Cycle 119 - make the progress-guard battery check its own numbers

- **Baseline** (commit fda470b):
  - canonical gate: 556 tests OK; aikit check 5/5; `policy_digest` decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - `evals/progress_guard.py` printed its numbers and exited 0; its docstring states twelve exact claims (guard cuts T3:15 33→13, T3:65 26→6, T2:3 34→8; calls 21→13/6/8 and 4/4/3 under skip; T1 36/22).
  - re-measured: all twelve numbers match the docstring exactly, so the claims were true but unenforced.
- **Gap**: the battery's own documented claims were not checked. A planner regression that changed any of the twelve numbers would only change the printed JSON; the exit code stayed 0, so no scripted gate could see it.
- **Target delta**: the twelve claims are pre-registered in code and compared on every run; each disagreement is named and exits 1.
- **Falsifier**: the real run reports a finding; a mutated claim still exits 0; or a pinned value moves.
- **Change**: `evals/progress_guard.py` adds `EXPECTED` (all 12 `(mode, task, seed) -> (steps, calls)` pairs), `checks(report)` naming `steps:`, `calls:`, `reward:`, `missing-case:`, `reward-varies:`, `guard-inert:` and `guard-no-saving:`, and exits through the ADR-112 contract; `tests/test_progress_guard_checks.py` adds 9 tests. ADR-113. The audit test now expects `progress_guard` among the covered batteries.
- **After** (same battery):
  - real run: findings `[]`, exit 0.
  - guard stops rejecting: 3 findings, exit 1; guard loses its saving: 2, exit 1; skip stops saving calls: 1, exit 1; a reward disappears: 2, exit 1; a case vanishes: 1, exit 1.
  - standing 89/11.0 and `policy_digest` unchanged.
- **Ablation**: without `checks` the same report exits 0 whichever number moved; with it each mutation is named, and the JSON payload is unchanged in both readings, so the delta is the check.
- **Verdict**: harness-honesty extension on the planner's own battery. The measured delta is twelve documented planner claims that were true and unchecked, now enforced per run. No behavior, estimator or pin moves. Boundary: the table locks current behavior rather than proving it optimal; a deliberate planner change must update `EXPECTED` (a reviewed diff, which is the intent), and eight batteries remain uncovered.
- **Gates**: unittest 565/565 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_progress_guard_checks` -> before: 1 error (`checks` absent); after: 9 OK.
  - `python -m evals.progress_guard` -> exit 0 with findings `[]`.
  - `python ..\..\scratch\ablate_119.py` -> five mutations, each exit 1 with named findings.
  - `python -m unittest discover -s tests -t .` -> 565 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 120**: unittest 565 OK; aikit 5/5; `progress_guard` real run clean/exit 0 and each of the five mutations exit 1; `EXPECTED` 12 pairs; `telemetry_lock` contract; `audit_batteries` covered includes `telemetry_lock` and `progress_guard`, uncovered still names `calibration`/`estimators`/`recompute`; `expected_model`; `expected_verdict_word`; `verify_result_records`; snapshot evidence; `confidence_is_outcome`; `vector_audit`; `SelfModel.size()`; recall cost; standing 89/11.0; T1 1581; holdout 738; cold-start 16/8/13/6; `detectability`; `syn` 0.054115320909768228 `phi` 0.0; policy decbfce3...; all earlier pins unchanged.

## Cycle 120 - check the header-reader battery's memory property

- **Baseline** (commit 3ff466a):
  - canonical gate: 565 tests OK; aikit check 5/5; `policy_digest` decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - `evals/header_reader.py` printed its two memory figures and exited 0 either way; its whole purpose is one claim — headers-only reading costs far less peak memory than retaining every record.
  - re-measured: all 124.2 MB, headers 0.1 MB, ratio 863.8x, matching the README exactly.
- **Gap**: the battery's single property was unenforced. A change making `read_headers` accumulate would only alter the printed JSON; the exit code stayed 0.
- **Target delta**: the two modes are compared on the property every run; a reader that retains or returns everything, or loses the header, is named and exits 1.
- **Falsifier**: the real run reports a finding; a regression exits 0; or a pinned value moves.
- **Change**: `evals/header_reader.py` adds `MIN_MEMORY_RATIO = 10.0` and `checks(report)` naming `headers-returned:`, `all-returned:`, `headers-count:`, `heads-disagree:`, `missing-mode:` and `memory-ratio:`, and exits through the ADR-112 contract; `tests/test_header_reader_checks.py` adds 9 tests. ADR-114. The audit test now expects `header_reader` among the covered batteries.
- **After** (same battery):
  - real run: findings `[]`, exit 0; all 124.2 MB / 100001 returned, headers 0.1 MB / 1 returned, ratio 863.8x.
  - retains everything: `memory-ratio:1.0<10.0`, exit 1; returns everything: `headers-returned:100001!=1`, exit 1; loses the header: `headers-count:0!=1` + disagreement, exit 1.
  - standing 89/11.0 and `policy_digest` unchanged.
- **Ablation**: without `checks` all three regressions print and exit 0; with it each is named, and the payload is identical in both readings, so the delta is the check.
- **Verdict**: harness-honesty extension on a quantitative battery. The measured delta is a memory property that was true and unchecked, now enforced per run with a noise-robust ratio floor. No behavior, estimator or pin moves. Boundary: the floor tolerates a slow leak below 10x; the property is proved at one size (100k), not at every size; six batteries remain uncovered.
- **Gates**: unittest 574/574 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_header_reader_checks` -> before: 1 error (`checks` absent); after: 9 OK.
  - `python -m evals.header_reader` -> exit 0 with findings `[]`.
  - `python ..\..\scratch\ablate_120.py` -> real clean 863.8x; three mutations each exit 1.
  - `python -m unittest discover -s tests -t .` -> 574 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 121**: unittest 574 OK; aikit 5/5; `header_reader` real run clean/exit 0, ratio > 10, and its three mutations exit 1; `progress_guard` five mutations exit 1; `telemetry_lock` contract; `audit_batteries` covered includes `telemetry_lock`/`progress_guard`/`header_reader`, uncovered still names `calibration`/`estimators`/`recompute`/`execution_budget`/`prompt_budget`/`resume_identity`/`vector_audit`; `expected_model`; `expected_verdict_word`; `verify_result_records`; snapshot evidence; `confidence_is_outcome`; `SelfModel.size()`; recall cost; standing 89/11.0; T1 1581; holdout 738; cold-start 16/8/13/6; `syn` 0.054115320909768228 `phi` 0.0; policy decbfce3...; all earlier pins unchanged.

## Cycle 121 - enforce the prompt-budget "no behavior change" claim

- **Baseline** (commit 9559f48):
  - canonical gate: 574 tests OK; aikit check 5/5; `policy_digest` decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - `evals/prompt_budget.py` already computed `actions_match_rule` and printed it, exiting 0 either way.
  - re-measured: uncapped 63 tokens / 0 omitted, budgeted 52 / 13 omitted, both 13 steps / 1.0 reward, matching the README.
- **Gap**: the battery's load-bearing claim — a prompt cap is behavior-preserving — was computed and discarded. A cap that changed one action would print `actions_match_rule: false` and exit 0, so no gate could see it.
- **Target delta**: the claim is enforced every run, along with step/reward parity and the fact that the cap trimmed something; each regression is named.
- **Falsifier**: the real run reports a finding; a behavior-changing cap exits 0; or a pinned value moves.
- **Change**: `evals/prompt_budget.py` adds `checks(report)` naming `missing-mode:`, `actions-differ-from-rule:`, `reward:`, `steps-varies:`, `reward-varies:`, `cap-did-not-trim:`, `uncapped-omitted:` and `budgeted-omitted:`, and exits through the ADR-112 contract; `tests/test_prompt_budget_checks.py` adds 9 tests. ADR-115. The audit test now expects `prompt_budget` among the covered batteries.
- **After** (same battery):
  - real run: findings `[]`, exit 0; uncapped 63/0, budgeted 52/13, both 13 steps / 1.0, actions match.
  - cap changes an action: `actions-differ-from-rule:budgeted`, exit 1; changes step count: `steps-varies:[13, 99]`, exit 1; trims nothing: `cap-did-not-trim:63>=63`, exit 1; reward lost: `reward:budgeted:0.0`, exit 1.
  - standing 89/11.0 and `policy_digest` unchanged.
- **Ablation**: without `checks` a behavior-changing cap exits 0; with it the same payload exits 1, and the JSON is identical in both readings, so the delta is the check.
- **Verdict**: harness-honesty extension on the model-seam release valve. The measured delta is a behavior-parity claim that was true and discarded, now enforced. No behavior, estimator or pin moves. Boundary: the claim is checked on one case (T3:15), not every task or size; five batteries remain uncovered.
- **Gates**: unittest 583/583 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_prompt_budget_checks` -> before: 1 error (`checks` absent); after: 9 OK.
  - `python -m evals.prompt_budget` -> exit 0 with findings `[]`.
  - `python ..\..\scratch\ablate_121.py` -> real clean; four mutations each exit 1.
  - `python -m unittest discover -s tests -t .` -> 583 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 122**: unittest 583 OK; aikit 5/5; `prompt_budget` real clean/exit 0 with `actions_match_rule True` in both modes, 63/52 tokens, 0/13 omitted, 13 steps / 1.0 reward, and its four mutations exit 1; `header_reader`; `progress_guard`; `telemetry_lock`; `audit_batteries` covered includes those four, uncovered names `calibration`/`estimators`/`recompute`/`execution_budget`/`resume_identity`/`vector_audit`; `expected_model`; `expected_verdict_word`; `verify_result_records`; snapshot evidence; `confidence_is_outcome`; `SelfModel.size()`; recall cost; standing 89/11.0; T1 1581; holdout 738; cold-start 16/8/13/6; `syn` 0.054115320909768228 `phi` 0.0; policy decbfce3...; all earlier pins unchanged.

## Cycle 122 - enforce the resume-identity battery's decisions

- **Baseline** (commit 35fed00):
  - canonical gate: 583 tests OK; aikit check 5/5; `policy_digest` decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - `evals/resume_identity.py` computed six identity claims and printed them, exiting 0 either way.
  - re-measured: same resume/True, changed-seed new/False, changed-target new/False, volatile resume/True, legacy ask/False, policy-any resume/False; reruns share an episode digest and actions; seed 65 differs at 6 steps vs 13.
- **Gap**: identity decisions were computed and discarded. A change that made a changed seed resume, or a volatile key alter the digest, only altered the printed JSON.
- **Target delta**: each mode's decision and same/different digest is enforced, plus volatile immunity, header agreement and rerun reproduction.
- **Falsifier**: the real run reports a finding; an identity regression exits 0; or a pinned value moves.
- **Change**: `evals/resume_identity.py` adds `EXPECTED_DECISIONS` (six `(decision, same_digest)` pairs) and `checks(report)` naming `missing-mode:`, `decision:`, `same-digest:`, `volatile-changed-the-digest`, `digest-unchanged:`, `header-mismatch:`, `rerun-differs:`, `rerun-actions-differ:` and `seed65-steps-equal:`, and exits through the ADR-112 contract; `tests/test_resume_identity_checks.py` adds 10 tests. ADR-116.
- **After** (same battery):
  - real run: findings `[]`, exit 0, six decisions as documented.
  - changed seed resumes: `decision:changed-seed:resume!=new`, exit 1; volatile key moves the digest: `volatile-changed-the-digest`, exit 1; header disagrees: `header-mismatch:same`, exit 1; legacy resumes: two findings, exit 1.
  - standing 89/11.0 and `policy_digest` unchanged.
- **Ablation**: without `checks` each identity regression prints and exits 0; with it each is named, and the payload is identical in both readings.
- **Verdict**: harness-honesty extension on the identity layer. The measured delta is six documented resume decisions that were true and unenforced, now checked per run. No behavior, estimator or pin moves. Boundary: the table pins the current identity policy rather than proving it correct; a deliberate policy change must update `EXPECTED_DECISIONS`, and four batteries remain uncovered.
- **Gates**: unittest 593/593 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_resume_identity_checks` -> before: 1 error (`checks` absent); after: 10 OK.
  - `python -m evals.resume_identity` -> exit 0 with findings `[]`.
  - `python ..\..\scratch\ablate_122.py` -> real clean; four mutations each exit 1.
  - `python -m unittest discover -s tests -t .` -> 593 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 123**: unittest 593 OK; aikit 5/5; `resume_identity` six decisions as documented and its four mutations exit 1; `prompt_budget`; `header_reader`; `progress_guard`; `telemetry_lock`; `audit_batteries` covered includes those five, uncovered names `calibration`/`estimators`/`recompute`/`execution_budget`/`vector_audit`; `expected_model`; `expected_verdict_word`; `verify_result_records`; snapshot evidence; `confidence_is_outcome`; `SelfModel.size()`; recall cost; standing 89/11.0; T1 1581; holdout 738; cold-start 16/8/13/6; `syn` 0.054115320909768228 `phi` 0.0; policy decbfce3...; all earlier pins unchanged.

## Cycle 123 - enforce the execution-budget battery's enforcement claims

- **Baseline** (commit 41610b0):
  - canonical gate: 593 tests OK; aikit check 5/5; `policy_digest` decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - `evals/execution_budget.py` printed five modes and exited 0 either way.
  - re-measured: generous 13 steps / 1.0 / actions match; step `steps` 4>3 at 3 steps; llm `llm_calls` 3>2 after 2 calls; token `tokens` 10>8; time `seconds`.
- **Gap**: budget enforcement was computed and discarded. A budget that stopped enforcing, or enforced the wrong dimension, only altered the printed JSON.
- **Target delta**: each mode must name its own dimension, a capped run must not be a success, its usage must exceed its limit, and the generous run must match the rule.
- **Falsifier**: the real run reports a finding; an enforcement regression exits 0; or a pinned value moves.
- **Change**: `evals/execution_budget.py` adds `EXPECTED_KIND` and `checks(report)` naming `missing-mode:`, `kind:`, `generous-changed-actions:`, `generous-not-success`, `generous-steps:`, `generous-reward:`, `capped-reported-success:`, `missing-usage:` and `not-exceeded:`, and exits through the ADR-112 contract; `tests/test_execution_budget_checks.py` adds 10 tests. ADR-117.
- **After** (same battery):
  - real run: findings `[]`, exit 0; step/llm/token/time name their own dimension; generous matches the rule at 13 steps / 1.0.
  - step stops enforcing: `kind:step:None!=steps`; wrong dimension: `kind:llm:steps!=llm_calls`; usage below limit: `not-exceeded:token:1.0<=8.0`; changed generous run: `generous-changed-actions:False`; capped run claims success: `capped-reported-success:step` — all exit 1.
  - standing 89/11.0 and `policy_digest` unchanged.
- **Ablation**: without `checks` each enforcement regression prints and exits 0; with it each is named, and the payload is identical in both readings.
- **Verdict**: harness-honesty extension on the budget layer. The measured delta is five enforcement claims that were true and unenforced, now checked per run. No behavior, estimator or pin moves. Boundary: the time mode is checked only for its dimension name (the wall clock is nondeterministic), and three batteries remain uncovered.
- **Gates**: unittest 603/603 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_execution_budget_checks` -> before: 1 error (`checks` absent); after: 10 OK.
  - `python -m evals.execution_budget` -> exit 0 with findings `[]`.
  - `python ..\..\scratch\ablate_123.py` -> real clean; five mutations each exit 1.
  - `python -m unittest discover -s tests -t .` -> 603 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 124**: unittest 603 OK; aikit 5/5; `execution_budget` five modes name their own dimension, generous 13/1.0 matches the rule, and its five mutations exit 1; `resume_identity`; `prompt_budget`; `header_reader`; `progress_guard`; `telemetry_lock`; `audit_batteries` covered includes those six, uncovered names `calibration`/`estimators`/`recompute`/`vector_audit`; `expected_model`; `expected_verdict_word`; `verify_result_records`; snapshot evidence; `confidence_is_outcome`; `SelfModel.size()`; recall cost; standing 89/11.0; T1 1581; holdout 738; cold-start 16/8/13/6; `syn` 0.054115320909768228 `phi` 0.0; policy decbfce3...; all earlier pins unchanged.

## Cycle 124 - pin the calibration battery's exact fixture scores

- **Baseline** (commit 95d9387):
  - canonical gate: 603 tests OK; aikit check 5/5; `policy_digest` decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - `evals/calibration.py` ran six cases with exact-by-construction scores and exited 0 either way.
  - re-measured: perfect 0.0/1.0, calibrated 0.166/0.308333, inverted 1.0/-3.0, small 0.0/None, ignored 0.04/0.84, run 0.230769/-2.25.
- **Gap**: the scorer's known-answer fixtures were unenforced. A formula change that moved Brier or skill only altered the printed JSON, so the battery's whole point — that the scores are correct — was not checked.
- **Target delta**: every fixture score is pinned within float-format tolerance, warnings are required on the small and inverted cases, and the real run keeps 13 steps / 1.0 / 13 resolved.
- **Falsifier**: the real run reports a finding; a moved score exits 0; or a pinned value moves.
- **Change**: `evals/calibration.py` adds `EXPECTED` and `checks(report)` naming `missing-mode:`, `brier:`, `skill:`, `no-warning:`, `run-steps:`, `run-reward:` and `run-resolved:`, and exits through the ADR-112 contract; `tests/test_calibration_checks.py` adds 9 tests. ADR-118.
- **After** (same battery):
  - real run: findings `[]`, exit 0; all six fixtures score as documented.
  - perfect Brier moves: `brier:perfect:0.5!=0.0`; inverted skill moves: `skill:inverted:0.0!=-3.0`; small sample looks resolved: `skill:small:1.0!=None`; real-run Brier moves: `brier:run-T3-15:0.1!=0.230769` — all exit 1.
  - standing 89/11.0 and `policy_digest` unchanged.
- **Ablation**: without `checks` each scorer regression prints and exits 0; with it each is named, and the payload is identical in both readings.
- **Verdict**: harness-honesty extension on the scorer's known-answer fixtures. The measured delta is six exact scores that were true and unchecked, now pinned. No behavior, estimator or pin moves. Boundary: this pins the scorer against the current fixtures, so a deliberate formula change must update `EXPECTED`; the real-run score is pinned too, so a planner change that altered T3:15 would surface here; the remaining uncovered modules (`estimators`, `recompute`, `vector_audit`) are pure libraries with unit tests rather than batteries.
- **Gates**: unittest 612/612 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python -m unittest tests.test_calibration_checks` -> before: 1 error (`checks` absent); after: 9 OK.
  - `python -m evals.calibration` -> exit 0 with findings `[]`.
  - `python ..\..\scratch\ablate_124.py` -> real clean; four mutations each exit 1.
  - `python -m unittest discover -s tests -t .` -> 612 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 125**: unittest 612 OK; aikit 5/5; `calibration` six fixtures at their exact scores, warnings on small/inverted, real run 13 steps / 1.0 / 13 resolved, and its four mutations exit 1; `execution_budget`; `resume_identity`; `prompt_budget`; `header_reader`; `progress_guard`; `telemetry_lock`; `audit_batteries` covered includes those seven, uncovered names `estimators`/`recompute`/`vector_audit`; `expected_model`; `expected_verdict_word`; `verify_result_records`; snapshot evidence; `confidence_is_outcome`; `SelfModel.size()`; recall cost; standing 89/11.0; T1 1581; holdout 738; cold-start 16/8/13/6; `syn` 0.054115320909768228 `phi` 0.0; policy decbfce3...; all earlier pins unchanged.

## Cycle 125 - cover the vector-audit adapter and make its order observable

- **Baseline** (commit 3029244):
  - canonical gate: 612 tests OK; aikit check 5/5; `policy_digest` decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - a coverage probe over the modules the exit-code audit classed as libraries found one genuinely untested public path: `vector_audit.audit_vectors` (added in cycle 109) had no test.
  - measured: it works (`audit_vectors == audit_rows` on correctly flattened blocks), but a wrong block order changes the audit's answer (`S0` reported instead of `M0`).
- **Gap**: an untested adapter whose correctness depends on an unpinned flatten order. Nothing was broken, but the contract it depends on was unenforced, so a future reorder would silently mislabel columns.
- **Target delta**: the adapter is covered and its block order is observable by a test that fails under a wrong flatten.
- **Falsifier**: the adapter test passes under a deliberately wrong block order; or the real suite fails.
- **Change**: `tests/test_vector_audit_adapter.py` adds 7 tests (adapter equals row audit, block order and column count, an `M0`-only fixture making order observable, a degenerate matrix, an independent matrix, the empty case, tuple/list equivalence). No production change. ADR-119.
- **After** (same code):
  - 7 tests pass; the suite total rises 612 -> 619.
  - the honest adapter equals `audit_rows` on every fixture checked.
  - standing 89/11.0 and `policy_digest` unchanged.
- **Ablation**: the first version of the order test passed under an S/P/M/hub flatten (failures=0); after adding the `M0`-only fixture the same wrong order produces 1 failure (`constant == ['S0']` instead of `['M0']`). The test is load-bearing only in its strengthened form, which is recorded rather than implied.
- **Verdict**: coverage extension on an untested adapter, plus a correction of my own first attempt. No behavior, estimator or pin moves. Boundary: this covers the adapter's contract, not every audit function (they have their own tests); the two remaining "uncovered" modules, `estimators` and `recompute`, are libraries whose public functions `test_estimators`, `test_recompute` and `test_wiring` already exercise — the exit-code audit cannot judge a library.
- **Gates**: unittest 619/619 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python ..\..\scratch\probe_lib_coverage.py` -> `vector_audit` untested: `['audit_vectors']`.
  - `python -m unittest tests.test_vector_audit_adapter` -> 7 OK.
  - `python ..\..\scratch\ablate_125.py` -> first run failures=0 (weak); after strengthening failures=1.
  - `python -m unittest discover -s tests -t .` -> 619 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 126**: unittest 619 OK; aikit 5/5; `vector_audit.audit_vectors` equals `audit_rows`, order-observable fixture reports `["M0"]`, wrong order fails; `calibration` fixtures; `execution_budget`; `resume_identity`; `prompt_budget`; `header_reader`; `progress_guard`; `telemetry_lock`; `audit_batteries` uncovered names `estimators`/`recompute`/`vector_audit`; `expected_model`; `expected_verdict_word`; `verify_result_records`; snapshot evidence; `confidence_is_outcome`; `SelfModel.size()`; recall cost; standing 89/11.0; T1 1581; holdout 738; cold-start 16/8/13/6; `syn` 0.054115320909768228 `phi` 0.0; policy decbfce3...; all earlier pins unchanged.

## Cycle 126 - pin the estimator edge conventions

- **Baseline** (commit 7f01932):
  - canonical gate: 619 tests OK; aikit check 5/5; `policy_digest` decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - `evals/estimators.py` documents a neutral-value convention per function for degenerate input; the suite checked only the happy path.
  - measured all twelve edge cases against the shipped code: every one returns the documented neutral value and none raises.
- **Gap**: the documented edge contracts were unverified. A refactor could have made `transfer_gain` raise on a zero baseline, dropped `recovery`'s clip, or divided by zero in `gbi` at `pre >= 1`, with no test noticing.
- **Target delta**: each convention is pinned, and a mutation of any of them fails the suite.
- **Falsifier**: a mutation of a documented convention leaves the suite green; or the real suite fails.
- **Change**: `tests/test_estimator_edges.py` adds 8 tests (one per function's edge, plus a no-raise sweep). No production change. ADR-120.
- **After** (same code):
  - 8 tests pass; the suite total rises 619 -> 627.
  - standing 89/11.0 and `policy_digest` unchanged.
- **Ablation** (three mutations of the shipped functions):
  - `transfer_gain` raises on a zero baseline -> 2 errors.
  - `recovery` loses its clip -> 1 failure (`-1.25 != 0.0`).
  - `gbi` divides at `pre >= 1` -> 2 errors, including the `ZeroDivisionError` the shipped code avoids.
  - restoring the functions -> 0 failures, 0 errors.
- **Verdict**: coverage extension on documented-but-unverified library conventions. No estimate, behavior or pin moves. Boundary: the tests pin the documented neutral conventions, not the optimality of the statistics; a deliberate convention change must update them, which is the intent.
- **Gates**: unittest 627/627 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python ..\..\scratch\probe_estimator_edges.py` -> all 12 edge cases document-conformant.
  - `python -m unittest tests.test_estimator_edges` -> 8 OK.
  - `python ..\..\scratch\ablate_126.py` -> three mutations each fail; restore clean.
  - `python -m unittest discover -s tests -t .` -> 627 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 127**: unittest 627 OK; aikit 5/5; `estimators` edge conventions pinned and three mutations each fail; `vector_audit` adapter; `calibration` fixtures; `execution_budget`; `resume_identity`; `prompt_budget`; `header_reader`; `progress_guard`; `telemetry_lock`; `audit_batteries` uncovered names `estimators`/`recompute`/`vector_audit`; `expected_model`; `expected_verdict_word`; `verify_result_records`; snapshot evidence; `confidence_is_outcome`; `SelfModel.size()`; recall cost; standing 89/11.0; T1 1581; holdout 738; cold-start 16/8/13/6; `syn` 0.054115320909768228 `phi` 0.0; policy decbfce3...; all earlier pins unchanged.

## Cycle 127 - carry the synergy scope into every battery trace slot

- **Baseline** (commit 75afc8d):
  - canonical gate: 627 tests OK; aikit check 5/5; `policy_digest` decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - ADR-099 added `syn_scope` to `recompute` and ADR-108 carried it into snapshot records, but `evals.coldstart._trace_slot` still emitted only `syn`/`syn_n`/`phi`/`gain`/`recovery`/`n_records`.
  - measured: `_trace_slot` dropped a `syn_scope` in its input, so five batteries printed a bare `syn` with no sufficiency qualifier.
- **Gap**: the misreading ADR-099 exists to prevent was still present in every battery trace readout. Cold-start printed `syn 0.0` with nothing saying the estimator is blind to columns 2-5.
- **Target delta**: every trace slot carries the scope (`None` when absent); all existing fields unchanged.
- **Falsifier**: a battery still prints a bare `syn`; an existing trace field changes; or a pinned value moves.
- **Change**: `evals/coldstart.py` `_trace_slot` adds `syn_scope` (defaulting to `None`) with a docstring naming why; `tests/test_trace_slot_scope.py` adds 5 tests. ADR-121.
- **After** (same batteries):
  - `coldstart` 4/4 slots, `dead_pool` 5/5, `escape` 2/2, `trust` 4/4, `manifest_binding` 2/2 — 17 of 17 carry `syn_scope`.
  - cold-start cases report `{'sufficient': False, 'reason': 'constant-scope-column'}` beside the unchanged `syn` 0.0.
  - standing 89/11.0 and `policy_digest` unchanged.
- **Ablation**: without the field each slot prints a bare `syn`; with it each carries the qualifier, and the numeric fields are byte-identical in both readings, so the delta is the qualifier.
- **Verdict**: telemetry-honesty extension completing the ADR-099 wiring. The measured delta is five battery readouts that showed a bare `syn` and now show what it measured; no estimate or behavior moves. Boundary: this covers `_trace_slot` only; a battery reporting `syn` elsewhere needs its own change, and the scope still does not widen the estimator.
- **Gates**: unittest 632/632 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python ..\..\scratch\probe_scope_wiring.py` -> five batteries dropped the scope.
  - `python -m unittest tests.test_trace_slot_scope` -> before: 3 failures + 1 error; after: 5 OK.
  - `python ..\..\scratch\ablate_127.py` -> 17/17 slots carry `syn_scope`.
  - `python -m unittest discover -s tests -t .` -> 632 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 128**: unittest 632 OK; aikit 5/5; every battery trace slot carries `syn_scope` (17/17), cold-start reports `sufficient: false` / `constant-scope-column`, existing slot fields unchanged; `estimators` edges; `vector_audit` adapter; `calibration` fixtures; `execution_budget`; `resume_identity`; `prompt_budget`; `header_reader`; `progress_guard`; `telemetry_lock`; `expected_model`; `expected_verdict_word`; `verify_result_records`; snapshot evidence; `confidence_is_outcome`; `SelfModel.size()`; recall cost; standing 89/11.0; T1 1581; holdout 738; cold-start 16/8/13/6; `syn` 0.054115320909768228 `phi` 0.0; policy decbfce3...; all earlier pins unchanged.

## Cycle 128 - compose every verifier into one aggregate

- **Baseline** (commit 8668e31):
  - canonical gate: 632 tests OK; aikit check 5/5; `policy_digest` decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - cycles 110-117 produced six independent verifiers; a survey of the public `verify_*` names showed no aggregate entry point.
- **Gap**: nothing composed the verifiers, so a consumer had to know to call each one, and a forgotten check silently weakened the verdict — the same failure mode the individual cycles were fixing one layer at a time.
- **Target delta**: one call runs every layer and returns the union of findings with each layer's own result, reimplementing nothing.
- **Falsifier**: the honest log fails a layer; a forgery that defeats one layer passes the aggregate; or a raising layer hides the others.
- **Change**: `run_verify.py` adds `verify_run(...)` composing `verify_chain`, `verify_episode_header`, `verify_action_replay(check_verdict=True)` and `verify_result_records`, catching a raising layer as `<layer>:<error>`; `tests/test_verify_run.py` adds 6 tests. ADR-122.
- **After** (same logs):
  - honest log with the model pin: `ok True`, all four layers pass.
  - forged actions: `chain True`, `episode True`, `replay False`, `results False`, aggregate `False`.
  - forged results: same shape — the aggregate names which layer spoke.
  - malformed policy pin: `episode:<error>` recorded while `chain` and `replay` still report.
  - standing 89/11.0 and `policy_digest` unchanged.
- **Ablation**: removing any single layer would accept that layer's forgery (`replay` for actions, `results` for costs); the aggregate reports both because it runs both.
- **Verdict**: composition, not a new check. The measured delta is a single verdict that covers all four evidence layers and names the failing one; no verifier's behavior changes. Boundary: the aggregate is only as strong as its weakest member — replay still cannot catch a consistently rewritten trajectory — and a pin must still be supplied by the caller.
- **Gates**: unittest 638/638 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python ..\..\scratch\probe_aggregate.py` -> six verifiers, no aggregate.
  - `python -m unittest tests.test_verify_run` -> 6 OK.
  - `python ..\..\scratch\ablate_128.py` -> per-layer isolation on two forgeries.
  - `python -m unittest discover -s tests -t .` -> 638 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 129**: unittest 638 OK; aikit 5/5; `verify_run` honest True with four layers and each forgery rejected by its own layer; `syn_scope` in 17/17 trace slots; `estimators` edges; `vector_audit` adapter; `calibration` fixtures; `execution_budget`; `resume_identity`; `prompt_budget`; `header_reader`; `progress_guard`; `telemetry_lock`; `expected_model`; `expected_verdict_word`; `verify_result_records`; snapshot evidence; `confidence_is_outcome`; `SelfModel.size()`; recall cost; standing 89/11.0; T1 1581; holdout 738; cold-start 16/8/13/6; `syn` 0.054115320909768228 `phi` 0.0; policy decbfce3...; all earlier pins unchanged.

## Cycle 129 - give the aggregate verifier a command line

- **Baseline** (commit 4630b3d):
  - canonical gate: 638 tests OK; aikit check 5/5; `policy_digest` decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - a survey of top-level modules showed `run_verify.py` had no `main`, no `argparse` and no `__main__` guard; only `state_machines.py` had a CLI.
  - measured: `python -m run_verify --log <path>` produced no output and no entry point existed.
- **Gap**: the one call that checks every evidence layer could be used only by importing it, so a human could not run it — the aggregate was shipped but unreachable.
- **Target delta**: a CLI with 0/1/2 exit codes and a terse per-layer report.
- **Falsifier**: a clean log exits non-zero; a failing log exits 0; misuse raises a traceback instead of exiting 2.
- **Change**: `run_verify.py` adds `format_report` and `main(argv=None)` with `--log` (required), `--json` and the policy/workspace/model/anchor/journal pins, plus a `__main__` guard; `tests/test_verify_run_cli.py` adds 6 tests driving the real module through a subprocess. ADR-123.
- **After** (same logs):
  - clean log: exit 0, `OK` with four `ok` layers; with `--model` set, exit 0.
  - wrong `--model`: exit 1, `episode FAIL`, `! model-mismatch`.
  - truncated log: exit 1, `replay FAIL`, `! missing-verdict`.
  - missing path and bare invocation: exit 2.
  - standing 89/11.0 and `policy_digest` unchanged.
- **Ablation**: without `main` there is no way to run the aggregate from a shell, so every exit code above is unreachable; with it the four outcomes are exercised through the real entry point.
- **Verdict**: usability extension on the aggregate verifier. The measured delta is four reachable CLI outcomes where there were none; no check, pin or estimate moves. Boundary: the CLI exposes the existing pins and adds no check; the caller still chooses which pins to supply.
- **Gates**: unittest 644/644 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python ..\..\scratch\probe_cli.py` -> only `state_machines.py` has a CLI.
  - `python -m unittest tests.test_verify_run_cli` -> before: 1 error; after: 6 OK.
  - `python ..\..\scratch\ablate_129.py` -> exit 0/0/1/1/2 across five cases.
  - `python -m unittest discover -s tests -t .` -> 644 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 130**: unittest 644 OK; aikit 5/5; `run_verify` CLI clean 0, wrong model 1 (`episode FAIL`, `model-mismatch`), truncated 1 (`replay FAIL`, `missing-verdict`), missing/bare 2; `verify_run` four layers; `syn_scope` 17/17; `estimators` edges; `vector_audit` adapter; `calibration` fixtures; `execution_budget`; `resume_identity`; `prompt_budget`; `header_reader`; `progress_guard`; `telemetry_lock`; `expected_model`; `expected_verdict_word`; `verify_result_records`; snapshot evidence; `confidence_is_outcome`; `SelfModel.size()`; recall cost; standing 89/11.0; T1 1581; holdout 738; cold-start 16/8/13/6; `syn` 0.054115320909768228 `phi` 0.0; policy decbfce3...; all earlier pins unchanged.

## Cycle 130 - remove the unreachable budget push/pop pair

- **Baseline** (commit 47f1b3d):
  - canonical gate: 644 tests OK; aikit check 5/5; `policy_digest` decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - a dead-code sweep over production modules found `budget.push_budget` with one occurrence (its own `def`) and `pop_budget` with one non-def occurrence inside the other's docstring; no module, test or README line used either.
  - measured: both behaved correctly (nest like a stack, interleave with `use_budget`, `spend` charges the pushed budget) — the defect was an unreachable public name, not a wrong one.
- **Gap**: shipped API with no caller and no test. A reader must guess whether it is supported, and a refactor can break it silently because nothing exercises it. It also duplicates `use_budget`'s two lines exactly.
- **Target delta**: the dead pair is removed; `use_budget` nesting and exception restoration become pinned where they were untested.
- **Falsifier**: a tree module still references the removed names; `use_budget` stops nesting or restoring; or a pinned value moves.
- **Change**: `budget.py` deletes `push_budget`/`pop_budget`; `tests/test_budget_surface.py` adds 6 tests (names gone, `use_budget` present, nests and restores, restores on exception, no tree reference, module contract intact). ADR-124.
- **After** (same tree):
  - 6 surface tests pass; suite total rises 644 -> 650.
  - `use_budget` nests outer/inner and restores after `RuntimeError`; `current_budget()` is `None` outside.
  - standing 89/11.0 and `policy_digest` unchanged.
- **Ablation**: restoring the two functions makes `test_push_and_pop_are_gone` fail (`True is not false`); deleting them makes it pass, so the test is the load-bearing guard rather than a restatement.
- **Verdict**: dead-code removal plus coverage of the surviving installer. The measured delta is an unreachable public pair gone and `use_budget` behavior now pinned; no budget, behavior or estimate moves. Boundary: a downstream import of `push_budget` outside this repo would break — acceptable for an undocumented pair with no in-tree caller, and recorded rather than assumed.
- **Gates**: unittest 650/650 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python ..\..\scratch\probe_dead2.py` -> `push_budget` refs=0, `pop_budget` only a docstring.
  - `python ..\..\scratch\probe_budget_stack.py` -> both behave correctly before removal.
  - `python -m unittest tests.test_budget_surface` -> before: 2 failures; after: 6 OK.
  - `python ..\..\scratch\ablate_130.py` -> restore fails the test, removal passes.
  - `python -m unittest discover -s tests -t .` -> 650 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 131**: unittest 650 OK; aikit 5/5; `push_budget`/`pop_budget` absent and unreferenced; `use_budget` nests and restores on exception; `run_verify` CLI 0/1/2; `verify_run` four layers; `syn_scope` 17/17; `estimators` edges; `vector_audit` adapter; `calibration` fixtures; `execution_budget`; `resume_identity`; `prompt_budget`; `header_reader`; `progress_guard`; `telemetry_lock`; `expected_model`; `expected_verdict_word`; `verify_result_records`; snapshot evidence; `confidence_is_outcome`; `SelfModel.size()`; recall cost; standing 89/11.0; T1 1581; holdout 738; cold-start 16/8/13/6; `syn` 0.054115320909768228 `phi` 0.0; policy decbfce3...; all earlier pins unchanged.

## Cycle 131 - pin the aggregate verifier's per-layer isolation

- **Baseline** (commit cf69554):
  - canonical gate: 650 tests OK; aikit check 5/5; `policy_digest` decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - `tests/test_verify_run.py` asserted only that the forged layer fails; nothing required the uninvolved layers to stay green.
  - measured: a hand-broken `verify_run` that fails every layer on any finding passed the cycle-128 suite with 0 failures.
- **Gap**: the aggregate's headline claim — it names which layer spoke rather than failing wholesale — was asserted one-sided, so a wholesale-failing regression satisfied every existing check.
- **Target delta**: each forgery also proves the layers that never read the tampered data stay `ok`.
- **Falsifier**: the strengthened suite still passes a wholesale-failing aggregate; or the real suite fails.
- **Change**: `tests/test_verify_run.py` adds the isolation asserts to the forged-action and rewritten-result tests (chain and episode stay `ok`); the model-pin test already checks the finding text. No production change. ADR-125.
- **After** (same code):
  - real suite: 650 OK (count unchanged — two tests strengthened).
  - wholesale-failing aggregate: 3 failures (`False is not true` on `chain` twice, `'model-mismatch' not found in ['collateral']`) where it previously reported 0.
  - standing 89/11.0 and `policy_digest` unchanged.
- **Ablation**: with the wholesale-failing aggregate the new asserts fail; with the shipped aggregate they pass, so the asserts are load-bearing rather than satisfied by construction.
- **Verdict**: test-strength extension on the aggregate's central claim. The measured delta is a one-sided assertion made two-sided; no behavior, verifier or pin moves. Boundary: this pins isolation between the four composed layers, not the completeness of each layer's internal checks.
- **Gates**: unittest 650/650 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python ..\..\scratch\probe_layer_claims.py` -> only the failing layer was asserted.
  - `python -m unittest tests.test_verify_run` -> 6 OK with the new asserts.
  - `python ..\..\scratch\ablate_131.py` -> wholesale aggregate: 3 failures vs 0 before.
  - `python -m unittest discover -s tests -t .` -> 650 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 132**: unittest 650 OK; aikit 5/5; `verify_run` per-layer isolation asserted in both directions (forged layer fails, uninvolved layers stay ok); `push_budget`/`pop_budget` absent; `use_budget` nests/restores; `run_verify` CLI 0/1/2; `syn_scope` 17/17; `estimators` edges; `vector_audit` adapter; `calibration` fixtures; `execution_budget`; `resume_identity`; `prompt_budget`; `header_reader`; `progress_guard`; `telemetry_lock`; `expected_model`; `expected_verdict_word`; `verify_result_records`; snapshot evidence; `confidence_is_outcome`; `SelfModel.size()`; recall cost; standing 89/11.0; T1 1581; holdout 738; cold-start 16/8/13/6; `syn` 0.054115320909768228 `phi` 0.0; policy decbfce3...; all earlier pins unchanged.

## Cycle 132 - the LIKE fallback searches the query's terms

- **Baseline** (commit b38c573):
  - canonical gate: 650 tests OK; aikit check 5/5; `policy_digest` decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - `MemoryStore.recall` tries FTS5 `MATCH`, falls back to `LIKE` on `OperationalError`, and used the query verbatim as the LIKE pattern.
  - measured against 13 real agent-written rows: `recall("T3_navigate")` -> 13 (FTS), `recall("T3_navigate AND (")` -> **0** (fallback searched the literal expression).
- **Gap**: a caller passing text containing FTS syntax got silence instead of the rows it asked for, and the existing test only asserted "does not raise", so the empty result passed.
- **Target delta**: the fallback searches the query's ordinary terms; a malformed query finds its rows; a genuine miss is still a miss.
- **Falsifier**: the malformed query still returns 0; a genuine miss starts matching; limit/ordering changes; or a pinned value moves.
- **Change**: `memory/store.py` adds `recall_terms(query)` (word runs, no keywords, min length 2) and builds a parameterised LIKE disjunction per term in the fallback, keeping `ORDER BY id ASC LIMIT ?`; an empty term list returns `[]`. `tests/test_recall_fallback.py` adds 6 tests against agent-written rows. ADR-126.
- **After** (same rows):
  - `recall("T3_navigate AND (")` -> 13; `recall("((( ")` -> 0; `recall("zzzz AND (")` -> 0; limit 3 -> the first three keys in id order.
  - memory/store-recovery/store-schema suites 16 tests OK; standing 89/11.0 and `policy_digest` unchanged.
- **Ablation**: with the raw-expression fallback the malformed query returns 0; with the term fallback it returns 13, and the other three queries are identical in both readings.
- **Verdict**: correctness fix in the memory recovery path. The measured delta is a silent empty result replaced by the 13 matching rows; no step, reward or pin moves. Boundary: this fixes term extraction, not query semantics — a multi-term query is a disjunction, and punctuation inside a term is still split.
- **Gates**: unittest 656/656 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python ..\..\scratch\probe_fts_use.py` -> the FTS query is called only from a test.
  - `python ..\..\scratch\probe_recall_real.py` -> malformed query returned 0 of 13.
  - `python -m unittest tests.test_recall_fallback` -> before: 1 error; after: 6 OK.
  - `python ..\..\scratch\ablate_132.py` -> 13 vs 0 on the malformed query.
  - `python -m unittest discover -s tests -t .` -> 656 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 133**: unittest 656 OK; aikit 5/5; `recall_terms` strips operators and keywords; malformed query finds 13, genuine misses find 0, limit/order preserved; `verify_run` isolation; `push_budget`/`pop_budget` absent; `use_budget` nests; `run_verify` CLI 0/1/2; `syn_scope` 17/17; `estimators` edges; `vector_audit` adapter; `calibration` fixtures; `execution_budget`; `resume_identity`; `prompt_budget`; `header_reader`; `progress_guard`; `telemetry_lock`; `expected_model`; `expected_verdict_word`; `verify_result_records`; snapshot evidence; `confidence_is_outcome`; `SelfModel.size()`; recall cost; standing 89/11.0; T1 1581; holdout 738; cold-start 16/8/13/6; `syn` 0.054115320909768228 `phi` 0.0; policy decbfce3...; all earlier pins unchanged.

## Cycle 133 - tokenise search terms without splitting non-ASCII words

- **Baseline** (commit a432ee7):
  - canonical gate: 656 tests OK; aikit check 5/5; `policy_digest` decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - ADR-126's `recall_terms` tokenised with `[A-Za-z0-9_]+`, an ASCII-only class.
  - measured: `"Türkçe"` -> `["rk"]`, `"français"` -> `["fran","ais"]`, `"içerik"` -> `["erik"]`, `"éè"`/`"日本語"` -> `[]`.
- **Gap**: a residual defect in my own cycle-132 fix. A wholly non-ASCII query extracts no terms and returns nothing even when a stored row contains exactly that text — the same silent-empty class ADR-126 exists to prevent.
- **Target delta**: words are tokenised whole for any script; ASCII behaviour unchanged; a non-ASCII query finds its row through both paths.
- **Falsifier**: an accented word is still split; a wholly non-ASCII query still returns nothing; or ASCII behaviour changes.
- **Change**: `memory/store.py` `recall_terms` uses `re.findall(r"[^\W]+", query, re.UNICODE)` instead of the ASCII class; `tests/test_recall_terms_unicode.py` adds 7 tests. ADR-127.
- **After** (same store):
  - `"Türkçe"` -> `["Türkçe"]`, `"日本語"` -> `["日本語"]`, `"T3_navigate"` unchanged.
  - a stored `"Türkçe içerik burada"` row is found by `recall("Türkçe")` and by `recall("Türkçe AND (")`; a stored `"日本語のテキスト"` row by `recall("日本語 AND (")`; a miss stays a miss.
  - cycle-132 fallback suite still 6 OK; standing 89/11.0 and `policy_digest` unchanged.
- **Ablation**: with the ASCII class the five probe queries give `["rk"]`, `["fran","ais"]`, `["erik"]`, `[]`, `["T3_navigate"]`; with `[^\W]+` each word stays whole, and the ASCII case is identical in both readings.
- **Verdict**: correctness fix completing cycle 132. The measured delta is a non-ASCII query going from nothing to its row; no step, reward or pin moves. Boundary: this fixes word boundaries, not ranking or stemming — accented forms are not normalised.
- **Gates**: unittest 663/663 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python ..\..\scratch\probe_terms_edges.py` -> `'éè'` -> `[]`, accent splits.
  - `python ..\..\scratch\probe_unicode_recall.py` -> `'Türkçe'` -> `['rk']`.
  - `python -m unittest tests.test_recall_terms_unicode` -> before: 4 failures; after: 7 OK.
  - `python ..\..\scratch\ablate_133.py` -> ASCII class vs `[^\W]+` on five queries.
  - `python -m unittest discover -s tests -t .` -> 663 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 134**: unittest 663 OK; aikit 5/5; `recall_terms` unicode-aware (`Türkçe`, `日本語` whole; ASCII unchanged); non-ASCII queries find their rows through FTS and fallback; `verify_run` isolation; `push_budget`/`pop_budget` absent; `run_verify` CLI 0/1/2; `syn_scope` 17/17; `estimators` edges; `vector_audit` adapter; `calibration` fixtures; `execution_budget`; `resume_identity`; `prompt_budget`; `header_reader`; `progress_guard`; `telemetry_lock`; `expected_model`; `expected_verdict_word`; `verify_result_records`; snapshot evidence; `confidence_is_outcome`; `SelfModel.size()`; recall cost; standing 89/11.0; T1 1581; holdout 738; cold-start 16/8/13/6; `syn` 0.054115320909768228 `phi` 0.0; policy decbfce3...; all earlier pins unchanged.

## Cycle 134 - record which store capabilities production reads

- **Baseline** (commit 589e9a5):
  - canonical gate: 663 tests OK; aikit check 5/5; `policy_digest` decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - the agent writes 13 JSON rows per episode into `memories` plus a 13-entry FTS5 index; `recall` is the only path that reads that content.
  - measured: `recall` has **zero** production callers; only `count` and `get_layout` are read.
- **Gap**: an unstated integration fact. A reader of the telemetry could not tell whether a store-backed run exercised recall or merely paid for the writes, and two wrong versions of my own probe (counting `self.memory.recall(` as a store call, missing `getattr(store, "get_layout")`) showed the measurement needed to be code.
- **Target delta**: the measured capability set is a test; adding or removing a store read path is caught.
- **Falsifier**: the probe misses a real caller; a non-caller is counted; or the recorded set drifts silently.
- **Change**: `tests/test_store_capability_use.py` adds `store_capability_use()` plus 5 tests (13 rows with 13 FTS entries, `recall` uncalled, `count`/`get_layout` present, the index still queryable, tokeniser matches ADR-127). No production change. ADR-128.
- **After** (same tree):
  - probe reports `count`/`get_layout`/`layout_fingerprint` in `agent.py` and no `recall`; `recall("T3_navigate")` still returns 13, so the capability works but is unwired.
  - standing 89/11.0 and `policy_digest` unchanged.
- **Ablation**: injecting a synthetic `store.recall(...)` line makes `test_recall_has_no_production_caller` fail naming `agent.py`; removing it passes, so the recorded fact cannot go stale silently.
- **Verdict**: integration-fact recording, not a behavior change. The measured delta is an undocumented write-only capability made explicit and guarded. Boundary: wiring recall into the loop would change the policy digest and every action pin — a separate decision with its own re-baseline; the probe is syntactic, so an aliased call would go unrecorded.
- **Gates**: unittest 668/668 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python ..\..\scratch\probe_content_read.py` -> `recall` has no production caller.
  - `python ..\..\scratch\probe_store_api.py` -> only `count`/`save`/`get_layout`/`close` called.
  - `python -m unittest tests.test_store_capability_use` -> before: 1 failure (detector conflated the in-memory ring); after: 5 OK.
  - `python ..\..\scratch\ablate_134.py` -> injected caller detected.
  - `python -m unittest discover -s tests -t .` -> 668 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 135**: unittest 668 OK; aikit 5/5; `store_capability_use` reports no `recall` caller and does report `count`/`get_layout`; 13 rows + 13 FTS entries per episode; index queryable; `recall_terms` unicode-aware; `verify_run` isolation; `push_budget`/`pop_budget` absent; `run_verify` CLI 0/1/2; `syn_scope` 17/17; `estimators` edges; `vector_audit` adapter; `calibration` fixtures; `execution_budget`; `resume_identity`; `prompt_budget`; `header_reader`; `progress_guard`; `telemetry_lock`; `expected_model`; `expected_verdict_word`; `verify_result_records`; snapshot evidence; `confidence_is_outcome`; `SelfModel.size()`; recall cost; standing 89/11.0; T1 1581; holdout 738; cold-start 16/8/13/6; `syn` 0.054115320909768228 `phi` 0.0; policy decbfce3...; all earlier pins unchanged.

## Cycle 135 - report whether a prompt budget was honoured

- **Baseline** (commit 85b8167):
  - canonical gate: 668 tests OK; aikit check 5/5; `policy_digest` decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - `pack` keeps the anchor line unconditionally; `prompt_stats` reported `tokens`/`omitted` but not whether the prompt fit the budget.
  - measured on T3 (uncapped 62 tokens): budget 60 -> 50/omitted 1/within; budget 40 -> 50 and **10 over**; budget 9 -> 50 and **41 over**.
- **Gap**: a caller or telemetry reader could not distinguish a met budget from an overrun — the same `tokens`/`omitted` shape for both.
- **Target delta**: the stats report `within_budget` and `over_by`; the kept lines and rendered prompt are unchanged.
- **Falsifier**: the real run reports a wrong flag; the prompt text moves; or `pack`'s triple changes.
- **Change**: `models/llamacpp.py` `prompt_stats` adds `within_budget` (`None` when uncapped) and `over_by = max(0, tokens - max_tokens)`; `tests/test_prompt_budget_honesty.py` adds 7 tests. ADR-129.
- **After** (same observation):
  - budget 120/60: `within_budget True`, `over_by 0`; budget 40: `False`, `over_by 10`; budget 9: `False`, `over_by 41`; uncapped: `None`.
  - prompt text and `pack` triple byte-identical; prompt/llamacpp/battery-check suites 20 tests OK; standing 89/11.0 unchanged.
- **Ablation**: without the two fields a 40-token budget returns a 50-token prompt and the stats dict is indistinguishable from the within-budget case; with them the overrun is named.
- **Verdict**: telemetry-honesty extension on the prompt path. The measured delta is a budget breach made visible; no prompt, action or pin moves. Boundary: it reports the breach, it does not prevent it — truncating the anchor would drop the legal-action list.
- **Gates**: unittest 675/675 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python ..\..\scratch\probe_pack.py` -> budget 40/30/20/9 all over budget with no flag.
  - `python -m unittest tests.test_prompt_budget_honesty` -> before: 5 errors; after: 7 OK.
  - `python ..\..\scratch\ablate_135.py` -> shipped names the breach; ablated silent.
  - `python -m unittest discover -s tests -t .` -> 675 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 136**: unittest 675 OK; aikit 5/5; `prompt_stats` reports `within_budget`/`over_by` (120/60 True/0, 40 False/10, 9 False/41, uncapped None/0) and the prompt text is unchanged; `store_capability_use`; `recall_terms` unicode-aware; `verify_run` isolation; `push_budget`/`pop_budget` absent; `run_verify` CLI 0/1/2; `syn_scope` 17/17; `estimators` edges; `vector_audit` adapter; `calibration` fixtures; `execution_budget`; `resume_identity`; `header_reader`; `progress_guard`; `telemetry_lock`; `expected_model`; `expected_verdict_word`; `verify_result_records`; snapshot evidence; `confidence_is_outcome`; `SelfModel.size()`; recall cost; standing 89/11.0; T1 1581; holdout 738; cold-start 16/8/13/6; `syn` 0.054115320909768228 `phi` 0.0; policy decbfce3...; all earlier pins unchanged.

## Cycle 136 - report a negative synergy gap as negative

- **Baseline** (commit eeb2e43):
  - canonical gate: 675 tests OK; aikit check 5/5; `policy_digest` decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - `synergy` returns `syn = I(joint) - I(c1) - I(c2)` and `syn_n = syn / I(joint)`, so a negative gap can reach `syn_n = -1.0`, the largest magnitude the ratio can take.
  - measured on the six pinned cases: T1:71 +0.037283/+0.077258; T2:3 -0.376770/-1.000000; T3:15 -0.057913/-0.213553; T3:65 -0.450561/-1.000000; T3:74 -0.040767/-0.116866; T3:479 -0.047824/-0.147114 — five of six negative, two at exactly -1.0.
- **Gap**: a reader taking the magnitude as interaction strength would rank the two `-1.0` cases highest when they are the strongest anti-interaction. Nothing distinguished a maximal positive from a maximal negative without checking a second field's sign.
- **Target delta**: the direction travels with the number as a pinned `syn_sign`; `syn`/`syn_n` unchanged.
- **Falsifier**: the real run reports the wrong direction; `syn`/`syn_n` move; or a pinned value changes.
- **Change**: `evals/estimators.py` adds `synergy_sign(syn, syn_n)` (positive/negative/zero from the gap's sign); `evals/recompute.py` reports it as `syn_sign`; `tests/test_synergy_sign.py` adds 6 tests. ADR-130.
- **After** (same cases):
  - T1:71 `positive`; the other five `negative`, including T2:3 and T3:65 at `syn_n = -1.0`.
  - estimator/recompute/scope/wiring/snapshot-evidence suites 24 tests OK; standing 89/11.0 and `policy_digest` unchanged.
- **Ablation**: without `syn_sign` two of six pinned cases report `syn_n = -1.0` with nothing distinguishing them from a maximal positive interaction; with it both read `negative`.
- **Verdict**: telemetry-honesty extension on the integration readout. The measured delta is the direction of an already-reported number; no value, action or pin moves. Boundary: it labels the direction — it does not make a negative gap positive, and five of six pinned cases genuinely show the joint carrying less than its marginals.
- **Gates**: unittest 681/681 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python ..\..\scratch\probe_syn_sign.py` -> five of six negative, two at -1.0.
  - `python -m unittest tests.test_synergy_sign` -> before: 1 error; after: 6 OK.
  - `python ..\..\scratch\ablate_136.py` -> sign readout names both -1.0 cases negative.
  - `python -m unittest discover -s tests -t .` -> 681 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 137**: unittest 681 OK; aikit 5/5; `syn_sign` positive for T1:71, negative for T2:3/T3:15/T3:65/T3:74/T3:479; `syn_n = -1.0` labelled negative; `prompt_stats` honesty fields; `store_capability_use`; `recall_terms` unicode-aware; `verify_run` isolation; `run_verify` CLI 0/1/2; `syn_scope` 17/17; `estimators` edges; `vector_audit` adapter; `calibration` fixtures; `execution_budget`; `resume_identity`; `header_reader`; `progress_guard`; `telemetry_lock`; `expected_model`; `expected_verdict_word`; `verify_result_records`; snapshot evidence; `confidence_is_outcome`; `SelfModel.size()`; recall cost; standing 89/11.0; T1 1581; holdout 738; cold-start 16/8/13/6; `syn` 0.054115320909768228 `phi` 0.0; policy decbfce3...; all earlier pins unchanged.

## Cycle 137 - carry the synergy sign into the batteries and the snapshot

- **Baseline** (commit fa0e9c6):
  - canonical gate: 681 tests OK; aikit check 5/5; `policy_digest` decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - `syn_sign` existed in `recompute`, but `evals/coldstart._trace_slot` (six batteries) and `snapshot.run_record` (the diff gate) still dropped it.
  - measured: both emitted `syn`/`syn_n` with no `syn_sign`, so `syn -0.450561 syn_n -1.000000` gave a reader no direction.
- **Gap**: the same wiring gap ADR-121 fixed for `syn_scope`, one field later. Every battery readout still presented a maximal negative ratio as an unlabelled number.
- **Target delta**: both reported shapes carry `syn_sign` (`None` when absent); no existing field changes.
- **Falsifier**: a battery still prints a bare negative `syn`; an existing field moves; or a pinned value changes.
- **Change**: `evals/coldstart.py` `_trace_slot` and `snapshot.py` `run_record` add `syn_sign` defaulting to `None`; `tests/test_synergy_sign_wiring.py` adds 6 tests. ADR-131.
- **After** (same batteries):
  - `coldstart` 4/4, `dead_pool` 5/5, `escape` 2/2, `trust` 4/4, `manifest_binding` 2/2 — 17/17 slots carry `syn_sign` (was 0/17).
  - trace-slot/snapshot/digest/cold-start-recovery/wiring suites 33 tests OK; standing 89/11.0 and `policy_digest` unchanged.
- **Ablation**: without the wiring every battery and the snapshot record show a bare negative `syn`; with it 17/17 slots carry the sign, and the numeric fields are byte-identical in both readings.
- **Verdict**: telemetry-honesty extension completing ADR-130. The measured delta is 17 readouts gaining a direction; no value, action or pin moves. Boundary: the sign says nothing about magnitude, and a negative gap stays negative.
- **Gates**: unittest 687/687 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python ..\..\scratch\probe_sign_wiring.py` -> neither shape carried `syn_sign`.
  - `python -m unittest tests.test_synergy_sign_wiring` -> before: 2 failures + 3 errors; after: 6 OK.
  - `python ..\..\scratch\ablate_137.py` -> 17/17 slots carry the sign.
  - `python -m unittest discover -s tests -t .` -> 687 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 138**: unittest 687 OK; aikit 5/5; `syn_sign` in 17/17 battery slots and in `run_record`; the real T3:65 case reaches the slot as `negative` with `syn_n = -1.0`; `prompt_stats` honesty; `store_capability_use`; `recall_terms` unicode-aware; `verify_run` isolation; `run_verify` CLI 0/1/2; `syn_scope` 17/17; `estimators` edges; `vector_audit` adapter; `calibration` fixtures; `execution_budget`; `resume_identity`; `header_reader`; `progress_guard`; `telemetry_lock`; `expected_model`; `expected_verdict_word`; `verify_result_records`; snapshot evidence; `confidence_is_outcome`; `SelfModel.size()`; recall cost; standing 89/11.0; T1 1581; holdout 738; cold-start 16/8/13/6; `syn` 0.054115320909768228 `phi` 0.0; policy decbfce3...; all earlier pins unchanged.

## Cycle 138 - score a claim's declared confidence as a forecast

- **Baseline** (commit 466c042):
  - canonical gate: 687 tests OK; aikit check 5/5; `policy_digest` decbfce34c9517d1594dd9c27949ac9b144c8e8631aca68dd39f0a28ad88c010.
  - `ClaimLedger.add(..., confidence=...)` validates a probability and stores it; a survey found only validation, the constructor default, the eval's echo and a preservation test — no consumer compared it with an outcome.
- **Gap**: a declared probability with no calibration readout. The repo scores the self-model's confidence/outcome pairs with Brier and skill; a claim could declare 0.95 on every claim and never be told it was wrong.
- **Target delta**: judged claims become scorer input, and the claims battery reports Brier/skill plus over-confidence bins over its own claims.
- **Falsifier**: a proposed claim is scored; an inconclusive verdict is given an outcome; the score is not computable; or the ledger is mutated.
- **Change**: `claims.py` adds `claim_forecasts(ledger)` (`supported`->1, `refuted`->0, `inconclusive`->`None`, `proposed` excluded); `evals/claims.py` reports a `calibration` block; `tests/test_claim_forecasts.py` adds 7 tests. ADR-132.
- **After** (same battery):
  - `counts {total 6, resolved 5, ignored 1, supported 3, refuted 2}`, Brier 0.2605, skill -0.085417, `bin 0.8-1.0 is overconfident by 0.22`.
  - ablation ledger (0.85 on six claims): Brier 0.3025, skill -0.260417, over-confidence 0.25.
  - claim/calibration/claim-store suites 50 tests OK; standing 89/11.0 and `policy_digest` unchanged.
- **Ablation**: without `claim_forecasts` the confidence is stored and never scored; with it every judged claim contributes and the over-confidence bin is named.
- **Verdict**: calibration-coverage extension on the claims layer. The measured delta is a declared probability that is now scored; no verdict, action or pin moves. Boundary: verdicts are the claim's own judgement, so a wrong verdict yields a correctly-scored wrong forecast, not a truth check; `inconclusive` is excluded from Brier.
- **Gates**: unittest 694/694 OK; aikit check brain 5/5 PASS.
- **Commands run**:
  - `python ..\..\scratch\probe_claim_confidence.py` -> confidence validated/stored/echoed, never scored.
  - `python -m unittest tests.test_claim_forecasts` -> before: 1 error; after: 7 OK.
  - `python -m evals.claims` -> calibration counts 6/5/1 at Brier 0.2605.
  - `python ..\..\scratch\ablate_138.py` -> 0.85-ledger Brier 0.3025, over-confidence named.
  - `python -m unittest discover -s tests -t .` -> 694 OK.
  - `python aikit.py check brain` -> 5/5.
- **Pinned regression baselines for cycle 139**: unittest 694 OK; aikit 5/5; `claim_forecasts` maps supported/refuted/inconclusive and excludes proposed, ledger unchanged; claims battery calibration 6/5/1 at Brier 0.2605 skill -0.085417 with the 0.8-1.0 over-confidence bin; `syn_sign` 17/17; `prompt_stats` honesty; `store_capability_use`; `recall_terms` unicode-aware; `verify_run` isolation; `run_verify` CLI 0/1/2; `syn_scope` 17/17; `estimators` edges; `vector_audit` adapter; `calibration` fixtures; `execution_budget`; `resume_identity`; `header_reader`; `progress_guard`; `telemetry_lock`; `expected_model`; `expected_verdict_word`; `verify_result_records`; snapshot evidence; `confidence_is_outcome`; `SelfModel.size()`; recall cost; standing 89/11.0; T1 1581; holdout 738; cold-start 16/8/13/6; `syn` 0.054115320909768228 `phi` 0.0; policy decbfce3...; all earlier pins unchanged.







