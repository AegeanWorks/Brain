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
