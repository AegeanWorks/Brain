# Codebase Map & Symbol Catalog 🗺️

> **AUTO-GENERATED & VERIFIED BY `scripts/update_knowledge_base.py`**
> This document catalogues Python modules, classes, and exported functions. See Map Coverage for any stack it does not index.

---

## 📊 Codebase Metrics
- **Total Python Modules**: `216`
- **Total Classes**: `221`
- **Total Top-Level Functions**: `611`
- **Total Class Methods**: `1152`
- **Total Source Lines**: `29378`

## 🧭 Map Coverage
- **Indexed**: python (`216` module(s))
- **Not indexed by this map**: none (no non-Python source files were found)

---

## 📦 Modules & Exported Symbols

### [`agent.py`](agent.py)
> *Rule-based agent loop over GridWorld state dicts.*

**Size**: `1671` lines (`69207` bytes)

**Classes:**
- `class Memory` - *Ordered store of observed state dicts.*
  - Method `.__init__()`
  - Method `.bind_hub(getter)`
  - Method `.read_hub()`
  - Method `.save(state)`
  - Method `.recall(limit)` - *Return stored states, most recent ``limit`` or all when None.*
  - Method `.clear()`
  - Method `.__len__()`
- `class Planner` - *Fixed rule-based policy over the state dict.*
  - Method `.__init__(backend, trust_window, noop_guard, progress_guard, progress_skip_after, cycle_escape, skip_after_distrust, probe_manifest, dead_pool_filter, rule_readout)`
  - Method `.bind_hub(getter)`
  - Method `.bind_recall_source(source)` - *Install a callable returning the persisted initial state.*
  - Method `.reset_recall_cache()` - *Forget any cached layout; called once per episode.*
  - Method `.reset_trust()` - *Restore full trust in the backend at the start of an episode.*
  - Method `.read_hub()`
  - Method `.plan(state, memories)`
- `class SelfModel` - *Record of (state, action, reward, done) transitions.*
  - Method `.__init__()`
  - Method `.bind_hub(getter)`
  - Method `.read_hub()`
  - Method `.record(state, action, reward, done)`
  - Method `.history()`
  - Method `.size()` - *Return the number of recorded transitions in O(1).*
  - Method `.clear()`
- `class Telemetry` - *Append-only log of step events.*
  - Method `.__init__()`
  - Method `.bind_hub(getter)`
  - Method `.read_hub()`
  - Method `.log(event)`
  - Method `.events()`
  - Method `.clear()`
- `class Agent` - *Closed loop over a GridWorld instance.*
  - Method `.__init__(memory, planner, selfmodel, telemetry, world, memory_store, planner_tracker, self_model, telemetry_log, module_signals, module_s_mode)`
  - Property `.log_path` - *Return file path of telemetry_log when present, else None.*
  - Method `.hub_write(content)` - *Merge a dict into the shared hub and return a hub copy.*
  - Method `.get_hub()` - *Return a copy of the shared hub mapping.*
  - Method `._reset_episode()`
  - Method `.online_predictions()` - *Return the outcomes learned online so far, keyed by feature.*
  - Method `._persistent_layout()` - *Return the persisted initial state for this world, or None.*
  - Method `._layout_complete(state)` - *True when a state carries every goal field its task consumes.*
  - Method `._remember_layout(state)` - *Persist the initial state once; never store an incomplete one.*
  - Method `._module_signals(memories, learned, keys, seen)` - *Return pre-action M/P/S state that is not an elapsed-time counter.*
  - Method `._step_vectors(idx, new_state, reward, memories)` - *Build numeric M/P/S/hub vectors for one step.*
  - Method `.run(max_steps, budget)` - *Run the loop; optionally install an execution budget.*
  - Method `._run_loop(max_steps)` - *Run perceive/plan/act/observe loop; return trace list.*
  - Method `.run_task(task_id, seed, max_steps, budget)` - *Build GridWorld(task_id, seed) and run the loop.*
  - Method `._episode_verdict(trace, max_steps)` - *Return (verdict, reason) without mistaking the cap for success.*
  - Method `.run_task_logged(task_id, seed, max_steps, log_path, budget, workspace_root, calibration_path, calibration_keep_recent, calibration_hmac_key)` - *Run task with header, per-step actions+results, and verdict.*
  - Method `.substrate_errors()` - *Return a copy of per-module persistent-substrate failure counts.*

**Functions:**
- `def _canonical_json(value)`
- `def _probe_safe(value)` - *Coerce a recalled value into JSON-safe probe data.*
- `def policy_digest(policy)` - *SHA-256 over the canonical declared planner configuration.*
- `def model_label(backend)` - *Stable model label for run headers: 'rule' with no backend.*
- `def world_fingerprint(world)` - *Return a world's deterministic layout fingerprint, or None.*
- `def _first_of_best_tour(pos, cells)` - *First cell of the shortest Manhattan tour from pos through cells.*
- `def _tour_audit(pos, cells)` - *Audit first-item ties in the exhaustive shortest item tour.*
- `def _enters_blocked_corridor(nxt, goal, obstacles)` - *True when stepping onto the goal's column/row while an obstacle*
- `def _bfs_step(pos, goal, obstacles)` - *Return one deterministic BFS step toward ``goal`` and its distance.*
- `def _bfs_distance(pos, goal, obstacles)` - *Shortest free-cell BFS distance, or None when unreachable.*
- `def _rule_confidence(pos, goal, obstacles, action, visits)` - *Return BFS move-tie facts for one rule action and its goal.*
- `def _step_toward(pos, goal, obstacles, visits, probe, dead_pool_filter)`

---

### [`budget.py`](budget.py)
> *Per-run execution budget: steps, LLM calls, tokens and wall time.*

**Size**: `158` lines (`5838` bytes)

**Classes:**
- `class BudgetExceeded` - *Raised when one dimension of the run budget is exhausted.*
  - Method `.__init__(kind, limit, used)`
- `class ExecutionBudget` - *Limits and usage for one top-level agent run.*
  - Method `.__post_init__()`
  - Method `.remaining(kind)` - *Remaining units for one dimension; seconds uses wall time.*
  - Method `.elapsed()` - *Seconds since this budget started.*
  - Method `.spend(kind, units)` - *Consume units, or raise :class:`BudgetExceeded` naming the dimension.*
  - Method `.check_time()` - *Raise when wall time has already exceeded the seconds limit.*
  - Property `.pressure` - *The fullest non-time dimension as a 0..1 fraction.*
  - Method `.snapshot()` - *JSON-ready limits, usage, elapsed time, pressure and exceeded flag.*

**Functions:**
- `def _valid_limits(limits)`
- `def current_budget()` - *The active budget for this context, or None.*
- `def use_budget(budget)` - *Install a budget for the current task; nested runs inherit it.*
- `def spend(kind, units)` - *Spend from the active budget when one is installed; else no-op.*
- `def budget_from_limits(limits)` - *Build an ExecutionBudget from a partial limit mapping.*

---

### [`calibration.py`](calibration.py)
> *Forecast calibration: Brier, log loss, skill and reliability bins.*

**Size**: `173` lines (`7287` bytes)

**Functions:**
- `def _clip(probability)`
- `def _bin_index(probability)`
- `def _validate(forecasts, min_resolved)`
- `def confidence_is_outcome(forecasts)` - *True when the recorded probability carries no information of its own.*
- `def summary(forecasts, min_resolved)` - *Compute the calibration scorecard for a sequence of forecasts.*

---

### [`calibration_store.py`](calibration_store.py)
> *Append-only calibration forecast journal with per-record checksums.*

**Size**: `573` lines (`21809` bytes)

**Functions:**
- `def _canonical(value)`
- `def _valid_digest(value)`
- `def _record_digest(record)`
- `def _record_mac(record, key)`
- `def _validate_hmac_key(value)`
- `def _now()`
- `def _validate_probability(value)`
- `def _validate_outcome(value)`
- `def _validate_at(value)`
- `def _validate_forecast(forecast)`
- `def _validate_record(record)` - *Validate one stored record's schema, fields and checksum.*
- `def _seal(forecast, at, hmac_key)`
- `def _read_records(path, hmac_key)`
- `def _fsync_dir(path)`
- `def _check_free_space(directory)`
- `def _locked(target, timeout_seconds)` - *Hold an exclusive advisory lock for one forecast append.*
- `def _write_records_atomic(target, records)`
- `def _write_json_atomic(target, value)`
- `def _backup_file(source, backup)`
- `def append_forecasts(forecasts, path, at, lock_timeout, keep_recent, hmac_key)` - *Append validated, checksummed forecasts under the writer lock.*
- `def load_forecasts(path, hmac_key)` - *Load all valid forecast records, raising on any store defect.*
- `def load_all_forecasts(path, archive_path, hmac_key)` - *Load archived forecasts in order, then the live journal.*
- `def verify_forecast_file(path, hmac_key)` - *Verify every record's schema, checksum, MAC, id and outcome.*
- `def _rotate_locked(target, archive, keep_recent, hmac_key)` - *Rotate ``target`` into ``archive``; the caller holds the lock.*
- `def rotate_forecast_journal(path, keep_recent, archive_path, lock_timeout, hmac_key)` - *Archive older forecasts and keep the newest ``keep_recent`` live.*

---

### [`claims.py`](claims.py)
> *Immutable claims, kill tests and verdict history (research-engine transfer).*

**Size**: `257` lines (`9394` bytes)

**Classes:**
- `class Verdict`
  - Method `.__post_init__()`
- `class Claim`
  - Method `.__post_init__()`
- `class ClaimLedger` - *Ordered in-memory claims with append-only verdict history.*
  - Method `.__init__(claims)`
  - Method `._insert(claim)`
  - Method `.add(text, kill_test, confidence, claim_id)` - *Create a proposed claim and return it.*
  - Method `.get(claim_id)`
  - Method `.record(claim_id, status, evidence, at, ref)` - *Append a verdict to one claim and return the updated claim.*
  - Method `.claims()`
  - Method `.summary()`
  - Method `.to_dict()`
  - Method `.from_dict(payload)`

**Functions:**
- `def _stamp()`
- `def _validate_ref(value)`
- `def _validate_text(value, name)`
- `def _validate_confidence(value)`
- `def _validate_claim(claim)`
- `def record_verdict(claim, status, evidence, at, ref)` - *Return a new Claim with the verdict appended and status updated.*
- `def claim_forecasts(ledger)` - *Return one forecast record per judged claim, for calibration scoring.*

---

### [`claims_store.py`](claims_store.py)
> *Durable claim-ledger snapshots with checksums, backups and quarantine.*

**Size**: `371` lines (`13812` bytes)

**Classes:**
- `class ClaimStoreMacError` - *The caller's key cannot authenticate the snapshot; do not quarantine.*

**Functions:**
- `def _canonical(value)`
- `def _valid_digest(value)`
- `def _digest(payload)`
- `def _mac(payload, key)`
- `def _validate_hmac_key(value)`
- `def _sealed(ledger, saved_at)`
- `def _validate_payload(value)`
- `def _read_payload(path, hmac_key)`
- `def _fsync_dir(path)`
- `def _check_free_space(directory)`
- `def _replace_with_retries(source, target)`
- `def _write_atomic(target, text)`
- `def _locked(target, timeout_seconds)` - *Hold an exclusive advisory lock for one claim-store write.*
- `def save_ledger(ledger, path, saved_at, lock_timeout, hmac_key)` - *Write one checksummed claim-ledger snapshot atomically.*
- `def _quarantine(target)`
- `def load_ledger(path, hmac_key)` - *Load a claim ledger, recovering from a backup after a corrupt primary.*
- `def verify_ledger_file(path, hmac_key)` - *Verify the primary snapshot's schema, checksum, MAC and claims.*

---

### [`claims_verify.py`](claims_verify.py)
> *Read-only verification of claim verdict refs against logged episodes.*

**Size**: `266` lines (`11382` bytes)

**Functions:**
- `def _validate_options(hmac_key, verify_logs)`
- `def _normalise_paths(log_paths)`
- `def _normalise_journals(paths, journal_paths)`
- `def _log_episodes(path, hmac_key, verify_logs, journal_path)`
- `def verify_claim_refs(ledger, log_paths, hmac_key, verify_logs, journal_paths, verify_episodes, expected_policy_sha256, expected_workspace_sha256, expected_model, verify_replay)` - *Check every verdict ref against the episodes found in the logs.*
- `def verify_claim_store(store_path, log_paths, hmac_key, verify_logs, journal_paths, verify_episodes, expected_policy_sha256, expected_workspace_sha256, store_hmac_key, expected_model, verify_replay)` - *Load a claim-store snapshot and verify its verdict refs.*

---

### [`demo.py`](demo.py)
> *Headless scripted drive: prints WORLD-DELTA lines, no input, exits 0.*

**Size**: `22` lines (`769` bytes)

**Functions:**
- `def _parse_seed(argv)`

---

### [`episode_replay.py`](episode_replay.py)
> *Replay a log's actions through the world its header names.*

**Size**: `217` lines (`9216` bytes)

**Functions:**
- `def parse_verdict_reason(reason)` - *Parse ``"steps=<n> reward=<r>"`` into ``{"steps", "reward"}`` or None.*
- `def logged_steps(records)` - *Return the action records that carry a step, in log order.*
- `def expected_verdict_word(replay, budget)` - *Return the word the trajectory and budget support.*
- `def verify_result_records(log_path, records, expected_cost)` - *Check each step's paired result record against the step itself.*
- `def replay_actions(task, seed, actions, max_steps)` - *Replay ``actions`` through a fresh world; return the visited states.*
- `def verify_action_replay(log_path, records, max_steps, check_verdict)` - *Replay a log's actions and report where the trajectory diverges.*

---

### [`episode_verify.py`](episode_verify.py)
> *Independent verification of a log header's episode digest.*

**Size**: `122` lines (`5270` bytes)

**Functions:**
- `def _valid_digest(value)`
- `def verify_episode_header(log_path, expected_policy_sha256, expected_workspace_sha256, expected_model)` - *Rebuild the episode identity from one log's header fields.*

---

### [`evals/__init__.py`](evals/__init__.py)
> *Brain evals package: task pins, estimators, recompute.*

**Size**: `1` lines (`61` bytes)

---

### [`evals/anchor_journal.py`](evals/anchor_journal.py)
> *Anchor-journal battery: chained run anchors and truncation detection.*

**Size**: `88` lines (`3028` bytes)

**Functions:**
- `def _build(path)`
- `def _truncate(path, keep)`
- `def measure_case(mode, directory)`
- `def run_battery(modes)`
- `def main()`

---

### [`evals/backend_conformance.py`](evals/backend_conformance.py)
> *Backend conformance battery: the seam is checkable without reading code.*

**Size**: `144` lines (`4715` bytes)

**Classes:**
- `class Conforming`
  - Method `.identity()`
  - Method `.generate(observation)`
- `class Alternating`
  - Method `.__init__()`
  - Method `.identity()`
  - Method `.generate(observation)`
- `class ClassIdentity`
  - Method `.generate(observation)`
- `class ReturnsNone`
  - Method `.identity()`
  - Method `.generate(observation)`

**Functions:**
- `def measure()` - *Run the contract over every control and the shipped registry.*
- `def checks(report)` - *Return the claims this battery's own output contradicts.*
- `def main()`

---

### [`evals/battery_check.py`](evals/battery_check.py)
> *One exit-code contract for the eval batteries.*

**Size**: `110` lines (`3950` bytes)

**Functions:**
- `def exit_code_for(findings)` - *Return the process exit code for one battery's findings.*
- `def battery_result(name, findings, payload)` - *Build one battery's report: name, ok flag, findings and payload.*
- `def format_findings(name, findings)` - *Render findings as one attributable line each, for stderr.*
- `def _adopts_contract(source)` - *True when a module's source references the contract by name.*
- `def _refuses_by_raising(tree)` - *True when the module contains an explicit ``raise`` statement.*
- `def audit_batteries(root)` - *Report which eval modules adopt the exit-code contract.*
- `def main()` - *Print the audit; exit 1 when any battery lacks a self-check.*

---

### [`evals/calibration.py`](evals/calibration.py)
> *Calibration battery: proper scores over fixtures and a real run.*

**Size**: `162` lines (`5547` bytes)

**Functions:**
- `def _forecast(identifier, probability, outcome)`
- `def _perfect()`
- `def _inverted()`
- `def _calibrated()`
- `def _compact(stats)`
- `def _fixture_case(name, forecasts, min_resolved)`
- `def measure_run()`
- `def run_battery()`
- `def checks(report)` - *Return the claims this battery's own output contradicts.*
- `def main()`

---

### [`evals/calibration_autoretention.py`](evals/calibration_autoretention.py)
> *Automatic calibration-retention battery at the logged-run bridge.*

**Size**: `154` lines (`6405` bytes)

**Functions:**
- `def _run(tmp, agent, task, seed, name, calibration_path, keep)`
- `def _stats(records)`
- `def _combined(path)`
- `def measure_case(mode, directory)`
- `def run_battery(modes)`
- `def main()`

---

### [`evals/calibration_bridge.py`](evals/calibration_bridge.py)
> *Calibration bridge battery: logged runs persist their own forecasts.*

**Size**: `177` lines (`7603` bytes)

**Functions:**
- `def _run(agent, task, seed, tmp, name, calibration_path, hmac_key)`
- `def _stats(records, min_resolved)`
- `def measure_case(mode, directory)`
- `def run_battery(modes)`
- `def main()`

---

### [`evals/calibration_retention.py`](evals/calibration_retention.py)
> *Calibration retention battery: archive older forecasts, keep the newest.*

**Size**: `178` lines (`7378` bytes)

**Functions:**
- `def _forecasts(rows)`
- `def _stats(records)`
- `def measure_case(mode, directory)`
- `def run_battery(modes)`
- `def main()`

---

### [`evals/calibration_store.py`](evals/calibration_store.py)
> *Calibration-store battery: cross-run forecasts and named defects.*

**Size**: `234` lines (`9699` bytes)

**Functions:**
- `def _forecasts(rows)`
- `def _stats(records)`
- `def measure_case(mode, directory)`
- `def run_battery(modes)`
- `def main()`

---

### [`evals/chain_anchor.py`](evals/chain_anchor.py)
> *Terminal-anchor battery: truncated telemetry tails are detected.*

**Size**: `84` lines (`2859` bytes)

**Functions:**
- `def _build_log(path)`
- `def _truncate(path, keep)`
- `def measure_case(mode, directory)`
- `def run_battery(modes)`
- `def main()`

---

### [`evals/claim_evidence.py`](evals/claim_evidence.py)
> *Claim/evidence battery: verdict refs cite logged episode digests.*

**Size**: `115` lines (`4639` bytes)

**Functions:**
- `def _run(tmp, task, seed, name)`
- `def measure_case(mode, directory)`
- `def run_battery(modes)`
- `def main()`

---

### [`evals/claim_ref_verify.py`](evals/claim_ref_verify.py)
> *Claim-ref battery: verdict refs checked against live log headers.*

**Size**: `262` lines (`11489` bytes)

**Functions:**
- `def _run(tmp, task, seed, name)`
- `def _ledger(one, two)`
- `def _summary(ledger)`
- `def measure_case(mode, directory)`
- `def run_battery(modes)`
- `def main()`

---

### [`evals/claims.py`](evals/claims.py)
> *Claim/verdict battery: kill tests over real T3 run outcomes.*

**Size**: `90` lines (`3420` bytes)

**Functions:**
- `def measure()`
- `def run_battery()`
- `def main()`

---

### [`evals/claims_store.py`](evals/claims_store.py)
> *Claim-store battery: durable snapshots vs the in-memory ledger.*

**Size**: `242` lines (`10426` bytes)

**Functions:**
- `def _ledger(limit)`
- `def _summary(ledger)`
- `def measure_case(mode, directory)`
- `def run_battery(modes)`
- `def main()`

---

### [`evals/coldstart.py`](evals/coldstart.py)
> *Cold-start recovery battery: behavior plus trace, before/after.*

**Size**: `329` lines (`12666` bytes)

**Classes:**
- `class ColdWorld` - *GridWorld whose observations omit the task's goal fields.*
  - Method `._state()`
- `class CaptureBackend` - *Record every observation and decline, forcing the rule fallback.*
  - Method `.__init__()`
  - Method `.generate(observation)`

**Functions:**
- `def warm_run(store, task, seed, max_steps)` - *Run the full-information episode and persist its layout.*
- `def cold_run(store, task, seed, max_steps, ablate, log_path, capture)` - *Run the hidden-observation episode after a simulated restart.*
- `def _actions_digest(trace)`
- `def _layout_keys(store, task, seed)`
- `def _probe_summary(steps)`
- `def _model_summary(backend, seed)`
- `def _trace_slot(stats)` - *Build one battery trace slot, including what the ``syn`` measured.*
- `def measure_case(task, seed, want_steps, want_reward, directory, ablate, capture, max_steps)` - *Run one warm/cold pair and return the recorded slots.*
- `def measure_cold_first(task, seed, want_steps, want_reward, directory, ablate, capture, max_steps)` - *Cold -> warm -> cold: prove a cold-first run cannot poison the row.*
- `def run_battery(cases, ablate, capture, max_steps, scenario)` - *Measure every case in one temporary directory.*
- `def _parse_case(text)`
- `def main()`

---

### [`evals/dead_pool.py`](evals/dead_pool.py)
> *Dead-pool guard battery: behavior plus the dead_pool probe.*

**Size**: `194` lines (`7177` bytes)

**Classes:**
- `class _ForcedMultiWorld`
  - Method `.__init__(target, obstacles)`
  - Method `._build_layout(rng)`
- `class DeclineBackend` - *Record every observation and decline, forcing the rule action.*
  - Method `.__init__()`
  - Method `.generate(observation)`

**Functions:**
- `def _actions_digest(trace)`
- `def _prompt_sha256(observation)`
- `def _decisions(steps)`
- `def _dead_pools(steps)`
- `def measure_case(target, obstacles, want_steps, directory, mode, max_steps)`
- `def run_battery(cases, mode, max_steps)` - *Measure every case under one mode in one temporary directory.*
- `def _parse_case(text)`
- `def main()`

---

### [`evals/episode_header.py`](evals/episode_header.py)
> *Episode-header battery: recompute episode_sha256 from the logged seed.*

**Size**: `235` lines (`10289` bytes)

**Functions:**
- `def _run(tmp, name, workspace_root)`
- `def _rewrite_header(path, mutate)`
- `def _ledger(episode)`
- `def measure_case(mode, directory)`
- `def run_battery(modes)`
- `def main()`

---

### [`evals/escape.py`](evals/escape.py)
> *Repeated-position cycle-escape battery: behavior plus model-seam trace.*

**Size**: `202` lines (`7411` bytes)

**Classes:**
- `class _ForcedWorld`
  - Method `.__init__(target, obstacles)`
  - Method `._build_layout(rng)`
- `class DeclineBackend` - *Record every observation and decline, forcing the rule action.*
  - Method `.__init__()`
  - Method `.generate(observation)`
- `class BlindPlanner` - *Executable memory cut: the planner never sees episode memories.*
  - Method `.plan(state, memories)`

**Functions:**
- `def _actions_digest(trace)`
- `def _decisions(steps)`
- `def _escapes(steps)`
- `def _prompt_sha256(observation, seed, model_id)`
- `def measure_case(name, target, obstacles, directory, mode, max_steps)`
- `def run_battery(cases, mode, max_steps)` - *Measure every case under one mode in one temporary directory.*
- `def _parse_case(text)`
- `def main()`

---

### [`evals/estimators.py`](evals/estimators.py)
> *Stdlib-only estimators for Brain evals.*

**Size**: `270` lines (`9743` bytes)

**Functions:**
- `def _discretize(values, bins)`
- `def mutual_info_discrete(xs, ys, bins)` - *Mutual information in nats between discretized xs and ys.*
- `def _solve(A, b)`
- `def phi_ar(trace)` - *Residual-variance ratio: 1 - MSE(whole)/MSE(partitioned), clipped at 0.*
- `def synergy_scope(trace, target)` - *Report which trace columns ``synergy`` reads, and whether they can decide.*
- `def synergy(trace, target)` - *Joint-minus-marginals gap: (syn, syn_n).*
- `def synergy_sign(syn, syn_n)` - *Classify a synergy gap's direction as ``positive``, ``negative`` or ``zero``.*
- `def gbi(pre_decodable, post_decodable)` - *Headroom-normalized change: (post - pre) / (1 - pre).*
- `def logistic_k(x, y)` - *Grid search over slope k; returns (best_k, r2).*
- `def transfer_gain(naive_steps, reuse_steps)` - *Relative step reduction: (naive - reuse) / naive.*
- `def recovery(time_outside, window)` - *Window fraction inside bounds: 1 - time_outside / window, clipped.*
- `def permutation_null(values_fn, shuffles, seed)` - *95th percentile of null statistics from a seeded generator.*

---

### [`evals/execution_budget.py`](evals/execution_budget.py)
> *Execution-budget battery: generous, step, LLM, token and time caps.*

**Size**: `170` lines (`5909` bytes)

**Classes:**
- `class WaitingBackend`
  - Method `.__init__()`
  - Method `.generate(observation)`
- `class PromptBackend`
  - Method `.__init__(tokens)`
  - Method `.generate(observation)`

**Functions:**
- `def _measure(mode)`
- `def run_battery(modes)`
- `def checks(report)` - *Return the claims this battery's own output contradicts.*
- `def main()`

---

### [`evals/header_reader.py`](evals/header_reader.py)
> *Header-reader battery: streaming headers vs decoding every record.*

**Size**: `125` lines (`4546` bytes)

**Functions:**
- `def _write_log(path)`
- `def measure_case(mode, directory)`
- `def run_battery(modes)`
- `def checks(report)` - *Return the claims this battery's own output contradicts.*
- `def main()`

---

### [`evals/lesion_audit.py`](evals/lesion_audit.py)
> *Lesion detectability: can a readout tell a lesion from arbitrary noise?*

**Size**: `122` lines (`4536` bytes)

**Functions:**
- `def module_columns(module, width)` - *Column indices belonging to ``module`` within a row of ``width``.*
- `def substitute_module(rows, module, seed)` - *Copy ``rows`` with ``module``'s block replaced by seeded random floats.*
- `def _synergy_of(rows)`
- `def _phi_of(rows)`
- `def detectability(rows, seed)` - *Report, per readout, which modules it can distinguish from noise.*

---

### [`evals/manifest_binding.py`](evals/manifest_binding.py)
> *Generation-manifest binding battery: behavior plus model-seam trace.*

**Size**: `167` lines (`6453` bytes)

**Classes:**
- `class ManifestBackend` - *Decline every proposal while recording its generation manifest.*
  - Method `.__init__(checkpoint, model_id)`
  - Method `.generate(observation)`

**Functions:**
- `def _actions_digest(trace)`
- `def _decisions(steps)`
- `def measure_case(task, seed, directory, mode, checkpoint, max_steps)`
- `def run_battery(cases, mode, max_steps)` - *Measure every case under one mode in one temporary directory.*
- `def _parse_case(text)`
- `def main()`

---

### [`evals/merkle_anchor.py`](evals/merkle_anchor.py)
> *Merkle batch-anchor battery: root, proof, truncation and tamper.*

**Size**: `102` lines (`3663` bytes)

**Functions:**
- `def _build(path, records)`
- `def _truncate(path, keep)`
- `def measure_case(mode, directory)`
- `def run_battery(modes)`
- `def main()`

---

### [`evals/merkle_compaction.py`](evals/merkle_compaction.py)
> *Merkle compaction battery: three anchors to one union root, safely.*

**Size**: `146` lines (`5898` bytes)

**Functions:**
- `def _log(path, records)`
- `def _three_batches(path)`
- `def _truncate(path, keep)`
- `def _lines(path)`
- `def measure_case(mode, directory)`
- `def run_battery(modes)`
- `def main()`

---

### [`evals/merkle_journal.py`](evals/merkle_journal.py)
> *Merkle journal battery: chained batches and retained historical proofs.*

**Size**: `163` lines (`6091` bytes)

**Functions:**
- `def _log(path, records)`
- `def _truncate(path, keep)`
- `def _canonical(value)`
- `def _resign(record)`
- `def _two_batches(path)`
- `def _history(path, journal, index)`
- `def measure_case(mode, directory)`
- `def run_battery(modes)`
- `def main()`

---

### [`evals/module_state.py`](evals/module_state.py)
> *Read the optional six-value module-state channel from telemetry.*

**Size**: `88` lines (`2888` bytes)

**Functions:**
- `def _row(args)` - *Return one six-signal row plus target, or None when malformed.*
- `def read_signals(log_path)` - *Return one row per action record carrying a ``signals`` block.*
- `def pool_signals(log_paths)` - *Concatenate the signal rows from several episode logs.*
- `def scan_module_states(log_paths, trials)` - *Scan pooled signal rows with the shared pair gate and family null.*
- `def scan_module_state_blocks(log_paths, trials)` - *Return the pooled signal scan split into module and world pairs.*

---

### [`evals/pair_scan.py`](evals/pair_scan.py)
> *Searching for an interacting column pair needs a per-pair validity gate.*

**Size**: `294` lines (`12161` bytes)

**Functions:**
- `def _dependent(first, second)` - *True when one column is a deterministic function of the other.*
- `def _target_column(values, target)` - *True when a column is identical to the target.*
- `def _target_leak(values, target)` - *True when the target is a deterministic function of the column.*
- `def block_for(column, width)` - *Return the M/P/S/hub block a column belongs to.*
- `def pair_report(rows, target, first, second, trials, with_null, guard_target)` - *Score one column pair, refusing artifacts before scoring.*
- `def _family_wise(rows, target, reports, trials, seed)` - *Attach a max/min-statistic null to every pair that passed the gate.*
- `def scan_pairs(rows, target, trials, family_wise, seed, guard_target)` - *Return every feature-column pair's report, sorted by gap descending.*
- `def interactions(rows, target, trials, family_wise, seed, guard_target)` - *Return only the pairs that pass the gate AND beat their family upward.*
- `def anti_interactions(rows, target, trials, family_wise, seed, guard_target)` - *Return pairs that pass the gate and sit below their family null.*
- `def module_pair(report)` - *True when a report's two blocks are different M/P/S modules.*
- `def world_pair(report)` - *True when a report includes the world hub.*
- `def module_interactions(rows, target, trials, family_wise, seed, guard_target)` - *Return corrected interactions whose two blocks are different modules.*
- `def world_interactions(rows, target, trials, family_wise, seed, guard_target)` - *Return corrected interactions that include a ``hub`` column.*

---

### [`evals/phi_diagnosis.py`](evals/phi_diagnosis.py)
> *A pinned 0.0 must say whether the estimator *could* have moved.*

**Size**: `64` lines (`2281` bytes)

**Functions:**
- `def _columns(rows)`
- `def phi_diagnosis(rows)` - *Explain a ``phi_ar`` result as data.*
- `def probe_scale()` - *Return the smallest synthetic series that moves ``phi_ar`` off 0.0.*

---

### [`evals/progress_guard.py`](evals/progress_guard.py)
> *Progress-guard battery: wrong-way moves, the guard, and the skip.*

**Size**: `204` lines (`8282` bytes)

**Classes:**
- `class WrongWayBackend` - *Legal free-cell movement away from the fixed target.*
  - Method `.__init__()`
  - Method `._distance(start, target, obstacles)`
  - Method `.generate(observation)`

**Functions:**
- `def measure_case(mode, task, seed)`
- `def run_battery(modes)`
- `def checks(report)` - *Compare a battery report with the pre-registered expectations.*
- `def main()`

---

### [`evals/prompt_budget.py`](evals/prompt_budget.py)
> *Prompt-budget battery: capped model prompts, unchanged rule actions.*

**Size**: `166` lines (`6260` bytes)

**Classes:**
- `class PromptBackend` - *Record the rendered prompt/manifest, then decline to the rule.*
  - Method `.__init__(budget)`
  - Method `.generate(observation)`

**Functions:**
- `def _synthetic(mode)`
- `def measure_case(mode)`
- `def run_battery(modes)`
- `def checks(report)` - *Return the claims this battery's own output contradicts.*
- `def main()`

---

### [`evals/recompute.py`](evals/recompute.py)
> *Recompute eval statistics from a JSONL log without trusting self-reports.*

**Size**: `171` lines (`6659` bytes)

**Functions:**
- `def _mean(xs)`
- `def _numbers(value)`
- `def _vec_row(rec)`
- `def _handle_eval_payload(args, acc)`
- `def dedupe_rows(rows)` - *Collapse adjacent identical rows to one.*
- `def recompute(log_path)` - *Read JSONL log and return dict with syn, phi, gbi, gain, recovery.*
- `def main()`

---

### [`evals/replication.py`](evals/replication.py)
> *A scan candidate must survive a held-out pool.*

**Size**: `98` lines (`4321` bytes)

**Functions:**
- `def _train_candidate(report, alpha)` - *True when a train report is a positive, family-significant pair.*
- `def scan_with_holdout(train_rows, train_target, holdout_rows, holdout_target, trials, stability_trials, alpha, require_replication, require_stability)` - *Return train candidates with their stability and holdout verdicts.*

---

### [`evals/resume_identity.py`](evals/resume_identity.py)
> *Episode-identity battery: canonical digests, resume decisions, headers.*

**Size**: `177` lines (`7058` bytes)

**Functions:**
- `def _config(seed)`
- `def _logged(seed, directory, name)`
- `def _measure(mode, directory)`
- `def run_battery(modes)`
- `def checks(report)` - *Return the claims this battery's own output contradicts.*
- `def main()`

---

### [`evals/rule_confidence.py`](evals/rule_confidence.py)
> *Rule-confidence battery: BFS move ties with the action held fixed.*

**Size**: `221` lines (`8777` bytes)

**Functions:**
- `def _state(x, y, target, task, items)`
- `def _readout_stats(rules)`
- `def _tie_stats(pairs)`
- `def _tour_stats(tours)`
- `def _run_seed(task, seed, readout, directory, suffix)`
- `def measure_seeds(mode, directory)`
- `def measure_case(mode, directory)`
- `def run_battery(modes)`
- `def main()`

---

### [`evals/snapshot_diff.py`](evals/snapshot_diff.py)
> *Snapshot-diff battery: portable run records and deterministic deltas.*

**Size**: `78` lines (`2558` bytes)

**Functions:**
- `def _battery(directory)`
- `def measure_case(mode, directory)`
- `def run_battery(modes)`
- `def main()`

---

### [`evals/snapshot_digest.py`](evals/snapshot_digest.py)
> *Snapshot content-vs-graph digest battery.*

**Size**: `90` lines (`3446` bytes)

**Functions:**
- `def _battery(directory)`
- `def measure_case(mode, directory)`
- `def run_battery(modes)`
- `def main()`

---

### [`evals/synergy_null.py`](evals/synergy_null.py)
> *A synergy gap plus the null it has to be read against.*

**Size**: `91` lines (`3633` bytes)

**Functions:**
- `def permutation_null(trace, target, trials, seed)` - *Return ``trials`` synergy gaps for shuffled copies of ``target``.*
- `def synergy_verdict(trace, target, trials, seed)` - *Report a synergy gap against its permutation null.*

---

### [`evals/telemetry_lock.py`](evals/telemetry_lock.py)
> *Concurrent telemetry battery: serialized append vs lock-off ablation.*

**Size**: `114` lines (`4247` bytes)

**Functions:**
- `def _no_lock(_path, timeout_seconds)`
- `def run_battery(writers, records, ablate)` - *Run concurrent writers and return the chain verdict.*
- `def checks(report)` - *Return the claims this battery's own output contradicts.*
- `def main()`

---

### [`evals/telemetry_mac.py`](evals/telemetry_mac.py)
> *Keyed telemetry battery: HMAC-signed records and named tamper findings.*

**Size**: `92` lines (`3236` bytes)

**Functions:**
- `def _build(path, key)`
- `def _rewrite(path, mutate)`
- `def measure_case(mode, directory)`
- `def run_battery(modes)`
- `def main()`

---

### [`evals/trust.py`](evals/trust.py)
> *Backend-trust battery: stalled legal proposals versus the rule fallback.*

**Size**: `222` lines (`8891` bytes)

**Classes:**
- `class WaitingBackend` - *Legal but stalled proposal: never moves or rewards.*
  - Method `.__init__()`
  - Method `.generate(observation)`
- `class NoopBackend` - *Propose a boundary/obstacle-blocked direction when one exists.*
  - Method `.__init__()`
  - Method `.generate(observation)`

**Functions:**
- `def _actions_digest(trace)`
- `def _decisions(steps)`
- `def _prompt_sha256(observation, seed, model_id)`
- `def measure_case(task, seed, directory, trust_window, noop_guard, backend_name, max_steps, skip_after_distrust)`
- `def run_battery(cases, trust_window, noop_guard, backend_name, max_steps, skip_after_distrust)` - *Measure every case in one temporary directory.*
- `def _parse_case(text)`
- `def main()`

---

### [`evals/vector_audit.py`](evals/vector_audit.py)
> *Audit a telemetry vector matrix for degenerate (non-independent) columns.*

**Size**: `110` lines (`3847` bytes)

**Functions:**
- `def _width(rows)`
- `def _label(index)`
- `def column_report(rows)` - *Return the constant columns, row/column counts, and their labels.*
- `def duplicate_pairs(rows)` - *Return sorted label pairs whose columns are byte-identical.*
- `def distinct_columns(rows)` - *Return the number of distinct non-constant column value sequences.*
- `def degenerate_columns(rows)` - *Return labels of columns that repeat another column's values.*
- `def audit_rows(rows)` - *Report the independence of one vector matrix in a single mapping.*
- `def audit_vectors(vectors)` - *Audit ``(M, P, S, hub)`` tuples directly, flattening them first.*

---

### [`evals/workspace_binding.py`](evals/workspace_binding.py)
> *Workspace-binding battery: source digest in logged run headers.*

**Size**: `91` lines (`3282` bytes)

**Functions:**
- `def _workspace(root)`
- `def _logged(root, log_path)`
- `def measure_case(mode, directory)`
- `def run_battery(modes)`
- `def main()`

---

### [`identity.py`](identity.py)
> *Episode identity and the resume guard (neurocore transfer).*

**Size**: `116` lines (`4172` bytes)

**Functions:**
- `def _clean(value)`
- `def canonical_projection(input_data, config)` - *The stable part of a request that must match before a resume.*
- `def digest_projection(projection)` - *SHA-256 over the canonical projection JSON.*
- `def input_digest(input_data, config)` - *Return ``(sha256, projection)`` for one request/config pair.*
- `def normalise_policy(policy)` - *Return a declared resume policy, defaulting to strict.*
- `def resume_decision(existing_sha, current_sha, policy, resume_any)` - *Return ``resume``, ``new`` or ``ask`` for one episode comparison.*
- `def resume_guard(episode, input_data, config, policy)` - *Compare an existing episode with this request.*
- `def prepare_resume(session_manager, episode, input_data, config)` - *Guard one candidate episode, pausing it when it must not resume.*

---

### [`inventory.py`](inventory.py)
> *Project-owned UI inventory: one `kind|name|locator` line per control.*

**Size**: `6` lines (`233` bytes)

---

### [`memory/__init__.py`](memory/__init__.py)
> *Memory package: SQLite-backed key/content store with FTS5 index.*

**Size**: `4` lines (`135` bytes)

---

### [`memory/store.py`](memory/store.py)
> *SQLite-backed store with FTS5 index and LIKE fallback.*

**Size**: `343` lines (`13678` bytes)

**Classes:**
- `class MemoryStore` - *Persisted key/content map with full-text lookup.*
  - Method `.__init__(path)` - *Open or create the store at path. Uses WAL mode.*
  - Method `._connect_validated()` - *Connect, apply the schema, and reject files failing checks.*
  - Method `._ensure_layout_fingerprint(conn)` - *Add the layouts fingerprint column to an older store in place.*
  - Method `._quarantine_corrupt(reason)` - *Move the unreadable database file (plus WAL sidecars) aside.*
  - Method `.recovery_notes()` - *Return a copy of the recovery log (empty on a clean open).*
  - Method `._persist()` - *Commit then flush the database file to storage.*
  - Method `.save(key, content, conf)` - *Insert or replace one record by key. Returns the row id.*
  - Method `.save_layout(task, seed, content, replace, fingerprint)` - *Persist one initial task state; first write wins by default.*
  - Method `.get_layout(task, seed, fingerprint)` - *Return the stored initial-state content for (task, seed), or None.*
  - Method `.layout_fingerprint(task, seed)` - *Return the stored layout fingerprint for (task, seed), or None.*
  - Method `.recall(query, limit)` - *Return up to limit records matching query, ordered by id ASC.*
  - Method `.snapshot()` - *Return a deterministic dict view of all records ordered by id.*
  - Method `.count()` - *Return the number of stored records.*
  - Method `.close()` - *Flush and close the underlying connection.*
  - Method `.__enter__()`
  - Method `.__exit__(exc_type, exc, tb)`

**Functions:**
- `def recall_terms(query)` - *Return the ordinary search terms in ``query``, FTS operators removed.*

---

### [`models/__init__.py`](models/__init__.py)
> *Swappable small-model backends for Brain policies.*

**Size**: `10` lines (`518` bytes)

---

### [`models/backend.py`](models/backend.py)
> *ModelBackend interface and deterministic StubBackend for protocol pins.*

**Size**: `52` lines (`1870` bytes)

**Classes:**
- `class ModelBackend` - *Propose one action token for an observation mapping.*
  - Method `.generate(observation)` - *Return one action token string for the observation.*
  - Method `.identity()` - *Return a stable, human-readable provider identity for run pins.*
- `class StubBackend` - *Replay a canned action script indexed by observation steps.*
  - Method `.__init__(script)`
  - Method `.identity()`
  - Method `.generate(observation)`

---

### [`models/conformance.py`](models/conformance.py)
> *Check a provider against the backend contract, without reading its code.*

**Size**: `124` lines (`5263` bytes)

**Functions:**
- `def check_backend(provider, observation, calls)` - *Exercise ``provider`` and return ``ok`` plus named findings.*
- `def _needs_script(provider)` - *True when the provider is StubBackend-like and needs a script list.*
- `def _check_script()`
- `def format_findings(report)` - *Render a conformance report as one line, for battery output.*

---

### [`models/llamacpp.py`](models/llamacpp.py)
> *llama.cpp backend: llama-server subprocess plus completion client.*

**Size**: `266` lines (`10282` bytes)

**Classes:**
- `class LlamaCppBackend` - *Drive a local llama-server for action proposals.*
  - Method `.__init__(server_exe, model_path, port, seed, timeout, n_predict, prompt_budget)`
  - Method `.base_url()`
  - Method `.identity()` - *Stable pin: provider plus checkpoint basename.*
  - Method `.start_server(wait_seconds)` - *Launch llama-server and wait until /health reports ok.*
  - Method `.generate(observation)` - *Post one chat completion; return the parsed token or None.*
  - Method `.close()` - *Terminate the server process if running, bounded wait.*
  - Method `.__enter__()`
  - Method `.__exit__(exc_type, exc, tb)`

**Functions:**
- `def estimate_tokens(text)` - *Stable provider-agnostic estimate: roughly four characters/token.*
- `def pack(lines, budget)` - *Fit prompt lines into a token budget, keeping the first line.*
- `def _prompt_lines(observation)`
- `def build_prompt(observation, max_tokens)` - *Render a compact deterministic action prompt for an observation.*
- `def prompt_stats(observation, max_tokens)` - *Return token/omission statistics for one rendered prompt.*
- `def parse_action(text)` - *Return the first legal action token in text, else None.*

---

### [`models/manifest.py`](models/manifest.py)
> *Generation manifest fingerprints for the model seam.*

**Size**: `70` lines (`2619` bytes)

**Functions:**
- `def canonical(obj)` - *Render canonical JSON: sorted keys, compact separators, ASCII.*
- `def manifest_for(prompt, observation, model_id, checkpoint, sampling)` - *Build the generation manifest for one backend call.*
- `def prompt_set_manifest(entries)` - *Hash a battery's manifest list into one prompt-set digest.*
- `def _jsonable(value)` - *Convert an observation mapping into canonical JSON-safe data.*

---

### [`models/registry.py`](models/registry.py)
> *A name-to-provider registry so a backend can be selected without code.*

**Size**: `60` lines (`2012` bytes)

**Functions:**
- `def register(name, factory)` - *Register ``factory`` under ``name``; a duplicate name raises.*
- `def build(name, **config)` - *Build the provider registered under ``name`` with ``config``.*
- `def names()` - *Return the registered backend names, sorted.*
- `def _build_llamacpp(**config)`

---

### [`planner/__init__.py`](planner/__init__.py)
> *Planner package: ordered step tracker with skip-on-error recovery.*

**Size**: `4` lines (`129` bytes)

---

### [`planner/plan.py`](planner/plan.py)
> *Ordered step tracker with explicit ok/fail marks and recovery.*

**Size**: `74` lines (`2621` bytes)

**Classes:**
- `class Planner` - *Track a linear sequence of named operations.*
  - Method `.__init__(steps)` - *Build a tracker from an optional initial step list.*
  - Method `.add_step(name, op)` - *Append one pending step. Returns its index.*
  - Method `.next()` - *Return the current step dict copy, or None when drained.*
  - Method `.mark_ok()` - *Mark the current step ok and advance. Returns True if moved.*
  - Method `.mark_fail()` - *Mark the current step failed. Cursor holds for recover().*
  - Method `.recover()` - *Skip failed entries and return the next viable step or None.*
  - Method `.state()` - *Return cursor plus per-step status list.*

---

### [`run_agent.py`](run_agent.py)
> *Run one episode, optionally with a backend chosen by name.*

**Size**: `89` lines (`3453` bytes)

**Functions:**
- `def _parse_script(text)` - *Split a comma-separated action script, ignoring blanks.*
- `def _build_backend(name, script)` - *Build a registered backend, or exit 2 with the available names.*
- `def main(argv)`

---

### [`run_verify.py`](run_verify.py)
> *One call that runs every shipped verifier over a finished log.*

**Size**: `129` lines (`5341` bytes)

**Functions:**
- `def verify_run(log_path, expected_policy_sha256, expected_workspace_sha256, expected_model, hmac_key, anchor_path, journal_path)` - *Run every shipped verifier over one log; return the union.*
- `def format_report(report)` - *Render one aggregate report as terse, greppable lines.*
- `def main(argv)` - *CLI: exit 0 clean, 1 a finding, 2 misuse.*

---

### [`self_model/__init__.py`](self_model/__init__.py)
> *Self-model package: budget/error/confidence counters.*

**Size**: `4` lines (`124` bytes)

---

### [`self_model/model.py`](self_model/model.py)
> *Running counters for cost, step outcomes, and reported confidence.*

**Size**: `120` lines (`4820` bytes)

**Classes:**
- `class SelfModel` - *Tally budget use, step counts, errors, and confidence values.*
  - Method `.__init__()` - *Start all counters at zero with an empty confidence log.*
  - Method `.record(cost, ok, conf)` - *Log one step: add cost, count ok/error, append confidence.*
  - Method `.record_prediction(cost, ok, predicted)` - *Log one step with a confidence formed *before* the outcome.*
  - Method `.snapshot()` - *Return steps, errors, budget, mean_conf, and error_rate.*
  - Method `.reset()` - *Return all counters to zero and clear the confidence log.*
  - Method `.calibration(min_resolved)` - *Score recorded confidence/outcome pairs with Brier/log loss.*
  - Method `.forecast_count()` - *Return the number of recorded confidence/outcome pairs.*
  - Method `.forecasts(prefix, start)` - *Return recorded pairs as forecast records with ids ``prefix:index``.*

---

### [`self_model/online.py`](self_model/online.py)
> *Learn the reward probability from error, without being told the rule.*

**Size**: `81` lines (`3058` bytes)

**Classes:**
- `class OnlinePredictor` - *Laplace-smoothed outcome frequencies that improve with every step.*
  - Method `.__init__()`
  - Method `.predict(key)` - *Probability of reward for ``key`` from counts so far.*
  - Method `.observe(key, outcome)` - *Record one outcome for ``key``; returns the updated count.*
  - Method `.table()` - *Return the learned probabilities, keyed by feature.*
  - Method `.keys()` - *Return the feature keys seen so far.*
  - Method `.seen(key)` - *Return how many outcomes have been recorded for ``key``.*

**Functions:**
- `def distance_bucket(state, task)` - *Pre-action distance to the nearest goal, capped at 3 (``9`` = none).*
- `def feature_key(task, state, action)` - *The key this predictor learns over: nothing but observable inputs.*

---

### [`self_model/prediction.py`](self_model/prediction.py)
> *Rung 1: a pre-outcome self-prediction the agent can be scored on.*

**Size**: `83` lines (`3185` bytes)

**Functions:**
- `def _goal_cells(state, task)`
- `def goal_distance(state, task)` - *Manhattan distance from the pre-action position to the nearest goal.*
- `def predict_outcome(state, action, task)` - *Probability that this step earns reward, from pre-action information.*

---

### [`snapshot.py`](snapshot.py)
> *Deterministic run snapshots and record-set diffing (lattice transfer).*

**Size**: `274` lines (`9598` bytes)

**Functions:**
- `def run_record(task, seed, trace, stats)` - *Build one snapshot record from a task/seed trace and trace stats.*
- `def capture_snapshot(cases, directory, max_steps)` - *Run each ``(task, seed)`` and return sorted run records.*
- `def export_snapshot(records, path, meta_path)` - *Write records as sorted JSONL through an atomic replace.*
- `def _write_atomic(target, body)`
- `def read_snapshot(path)` - *Read a JSONL snapshot into a list of records.*
- `def _clean(value)`
- `def _ordered(records)`
- `def _digest(records)`
- `def graph_sha256(records)` - *Exact digest of every record, including volatile capture fields.*
- `def content_sha256(records)` - *Semantic digest with volatile capture fields removed recursively.*
- `def snapshot_digests(records)` - *Return record count, exact graph digest and semantic content digest.*
- `def write_snapshot_meta(records, meta_path)` - *Write the digest metadata as atomic JSON and return it.*
- `def verify_snapshot(path, meta_path)` - *Verify a snapshot against its meta record count and digests.*
- `def _index(records)`
- `def diff_records(old_records, new_records)` - *Compare two record sets by ``(record_type, id)``.*
- `def _fsync_dir(path)`

---

### [`state_machines.py`](state_machines.py)
> *Explicit state-machine registry for Brain (PRINCIPLE-009, PRINCIPLE-016).*

**Size**: `523` lines (`22720` bytes)

**Classes:**
- `class Machine` - *One lifecycle as data: states, intended transitions, and its source.*
  - Method `.allows(source, target)` - *Return True when ``source -> target`` is a declared transition.*

**Functions:**
- `def as_dict()` - *Return a deterministic JSON-ready view of the whole registry.*
- `def check_live()` - *Compare declared states with live product constants.*
- `def run_transition(machine, source, target)` - *Print and return the triad verdict for one declared transition.*
- `def print_machine(machine)` - *Render one machine for a human or agent reader.*
- `def main(argv)` - *Run the read-only registry CLI.*

---

### [`telemetry/__init__.py`](telemetry/__init__.py)
> *Telemetry package: append-only JSONL record store plus trace ablation.*

**Size**: `5` lines (`192` bytes)

---

### [`telemetry/ablate.py`](telemetry/ablate.py)
> *Deterministic trace transforms for ablation.*

**Size**: `194` lines (`6643` bytes)

**Functions:**
- `def _zero_value(value)`
- `def _zero_vector(vec)`
- `def _copy_step(step)`
- `def _map_trace(trace, func)`
- `def hub_zero(trace)` - *Return trace copy with every ``hub`` vector replaced by zeros.*
- `def module_lesion(trace, mod)` - *Return trace copy with module ``mod`` column zeroed.*
- `def shuffle_hub(trace, seed)` - *Return trace copy with each ``hub`` vector permuted deterministically.*
- `def _zero_top_and_args(row, keys)` - *Copy one logged row and zero ``keys`` top-level and in args.*
- `def _map_rows(rows, keys)`
- `def hub_zero_rows(rows)` - *Return logged rows copy with hub components zeroed.*
- `def lesion_m(rows)` - *Return logged rows copy with M components zeroed, others kept.*
- `def lesion_p(rows)` - *Return logged rows copy with P components zeroed, others kept.*
- `def lesion_s(rows)` - *Return logged rows copy with S components zeroed, others kept.*

---

### [`telemetry/log.py`](telemetry/log.py)
> *Append-only JSONL record store, schema 2.*

**Size**: `820` lines (`33109` bytes)

**Classes:**
- `class Telemetry` - *JSONL append-only store at ``path``.*
  - Method `.__init__(path, lock_timeout, hmac_key)`
  - Method `._head_digest()` - *Return the digest new records must link to.*
  - Method `._write_record(record)`
  - Method `.write_header(task, budget, manifest_sha256, manifest_path, policy, policy_sha256, model, episode_sha256, workspace_sha256, seed)` - *Write header record (seq 0) describing task and budget.*
  - Method `.append_action(seq, kind, args, M, P, S, hub)` - *Record an action before it executes.*
  - Method `.append_result(seq, ok, output, cost, M, P, S, hub)` - *Record the result for a prior action ``seq``.*
  - Method `.write_verdict(verdict, reason, seq)` - *Write terminal verdict record.*
  - Method `.write_anchor(anchor_path)` - *Write a head/count witness for the current log.*
  - Method `.write_anchor_journal(journal_path, created_at)` - *Append the current log head/count to an anchor journal.*
  - Method `.write_merkle_anchor(batch_size, anchor_path, created_at)` - *Write a Merkle batch anchor for the last records.*
  - Method `.append_merkle_anchor(batch_size, journal_path, created_at)` - *Append a Merkle batch anchor to the hash-chained journal.*
  - Method `.read_all()` - *Return list of decoded JSON objects in file order.*
  - Method `.read_headers()` - *Return only decoded header records, in file order.*
  - Method `.bins(step_ms)` - *Group records into fixed time bins from first timestamp.*

**Functions:**
- `def _append_lock(path, timeout_seconds)` - *Hold an exclusive advisory lock for one telemetry append.*
- `def _canonical(record)`
- `def _digest_of(record)`
- `def _mac_of(record, key)` - *HMAC-SHA256 over the canonical record without its ``mac`` field.*
- `def _last_nonempty_line(path, chunk_size)` - *Return the last non-empty line, reading backward from the file tail.*
- `def sha256_file(path)` - *Return hex sha256 of file bytes at ``path``.*
- `def _dir_fsync(dir_path)` - *Fsync directory entry for ``dir_path``; no-op where unsupported.*
- `def _anchor_path(path)`
- `def write_anchor(path, head, records, anchor_path)` - *Write a terminal head/count witness beside the log.*
- `def read_anchor(anchor_path)` - *Return the decoded anchor mapping, or None when missing/malformed.*
- `def _anchor_journal_path(path)`
- `def _valid_digest(value)`
- `def _anchor_payload(record)`
- `def _anchor_hash(record)`
- `def _validate_anchor_record(value, line_number)` - *Validate one journal record; raise ValueError with a named defect.*
- `def append_anchor(path, head, records, journal_path, created_at)` - *Append one anchor to a JSONL journal and return the stored record.*
- `def verify_anchor_journal(journal_path)` - *Verify every anchor's hash and its link to the previous anchor.*
- `def verify_chain(path, anchor_path, journal_path, hmac_key)` - *Verify the hash chain of the JSONL log at ``path``.*

---

### [`telemetry/merkle.py`](telemetry/merkle.py)
> *Domain-separated Merkle batch anchors and inclusion proofs.*

**Size**: `621` lines (`23733` bytes)

**Functions:**
- `def pack(data)` - *Prefix ``data`` with its length so concatenated parts are unambiguous.*
- `def digest(domain, *parts)` - *One 32-byte SHA-256 digest bound to a named protocol domain.*
- `def merkle_root(leaves)` - *Root of a domain-separated Merkle tree; empty and odd trees defined.*
- `def merkle_proof(leaves, index)` - *Sibling hashes from the leaf level upwards; promoted nodes add b''.*
- `def merkle_verify(leaf, index, proof, root)` - *Recompute the root from one leaf and its proof, rejecting forgery.*
- `def _leaf(value)`
- `def _anchor_path(log_path)`
- `def _read_records(log_path)`
- `def _fsync_dir(path)`
- `def _write_anchor(target, anchor)`
- `def _write_journal_record(target, record)`
- `def _write_meta(target, meta)`
- `def _validate_anchor(anchor)`
- `def _build_anchor(log_path, batch_size, created_at)` - *Build the batch anchor for the last ``batch_size`` record digests.*
- `def write_merkle_anchor(log_path, batch_size, anchor_path, created_at)` - *Commit the last ``batch_size`` record digests into a Merkle anchor.*
- `def _canonical_json(value)`
- `def _anchor_hash(record)`
- `def _valid_digest(value)`
- `def _validate_journal_record(record, line_number)` - *Validate one journal record's anchor fields, prev link and hash.*
- `def _journal_path(log_path)`
- `def _scan_journal(journal_path)` - *Return ``(records, errors)`` after validating links and order.*
- `def append_merkle_anchor(log_path, batch_size, journal_path, created_at)` - *Append one batch anchor to a hash-chained journal.*
- `def compact_merkle_journal(log_path, journal_path, output_path, replace, created_at)` - *Merge every journal anchor into one root over their union.*
- `def verify_merkle_journal(log_path, journal_path)` - *Verify journal links/order and, when given, every batch root.*
- `def merkle_proof_for_journal_record(log_path, journal_path, record_index)` - *Prove one record in the latest journal batch that contains it.*
- `def verify_merkle_anchor(log_path, anchor_path)` - *Verify the batch range against the log and the anchor root.*
- `def merkle_proof_for_record(log_path, anchor_path, record_index)` - *Return the detached inclusion proof for one record in the batch.*
- `def verify_merkle_proof(bundle)` - *Verify a detached proof bundle produced by ``merkle_proof_for_record``.*

---

### [`tests/__init__.py`](tests/__init__.py)
**Size**: `0` lines (`0` bytes)

---

### [`tests/test_ablation.py`](tests/test_ablation.py)
> *Ablation transform checks.*

**Size**: `58` lines (`2109` bytes)

**Classes:**
- `class TestAblation`
  - Method `.test_hub_zero_kills_hub_content()`
  - Method `.test_lesion_isolates()`
  - Method `.test_shuffle_deterministic_and_preserves_multiset()`

**Functions:**
- `def _trace()`

---

### [`tests/test_adjacent_block.py`](tests/test_adjacent_block.py)
> *Adjacent block: target directly behind a column obstacle.*

**Size**: `50` lines (`1742` bytes)

**Classes:**
- `class BlindPlanner`
  - Method `.plan(state, memories)`
- `class TestAdjacentBlock`
  - Method `.test_seed307_optimal_6()`
  - Method `.test_t3_300_399_total()`
  - Method `.test_ablation_blind_truncates_adjacent_trap()`

**Functions:**
- `def _steps(task, seed, planner, max_steps)`

---

### [`tests/test_agent.py`](tests/test_agent.py)
> *Agent loop checks: run completes with a non-empty trace.*

**Size**: `63` lines (`2256` bytes)

**Classes:**
- `class TestAgent`
  - Method `.test_run_completes_all_tasks()`
  - Method `.test_run_with_injected_world()`
  - Method `.test_hub_shared()`
  - Method `.test_tempdir_trace_roundtrip()`

---

### [`tests/test_agent_online.py`](tests/test_agent_online.py)
> *The agent learns across episodes, not inside one.*

**Size**: `67` lines (`2656` bytes)

**Classes:**
- `class TestAgentLearnsOnline`
  - Method `.test_a_fresh_agent_knows_nothing()`
  - Method `.test_one_episode_populates_the_table()`
  - Method `.test_the_table_persists_across_episodes()`
  - Method `.test_the_learned_rule_matches_the_world()`
  - Method `.test_actions_are_unchanged_by_learning()`

---

### [`tests/test_anchor_journal.py`](tests/test_anchor_journal.py)
> *Anchor journal: each run head commits to the previous anchor.*

**Size**: `124` lines (`5167` bytes)

**Classes:**
- `class TestAnchorJournal`
  - Method `.test_journal_chains_two_anchors()`
  - Method `.test_truncated_log_detected_against_latest_anchor()`
  - Method `.test_deleted_anchor_detected()`
  - Method `.test_tampered_anchor_head_detected()`
  - Method `.test_backwards_seq_rejected()`
  - Method `.test_missing_journal_reported()`
  - Method `.test_single_anchor_api_unchanged()`

**Functions:**
- `def _log(path, records)`
- `def _truncate(path, keep)`

---

### [`tests/test_backend_conformance_checks.py`](tests/test_backend_conformance_checks.py)
> *The conformance battery must check its own controls.*

**Size**: `75` lines (`3071` bytes)

**Classes:**
- `class TestBackendConformanceChecks`
  - Method `.setUpClass()`
  - Method `.test_a_clean_report_has_no_findings()`
  - Method `.test_the_conforming_control_passes()`
  - Method `.test_the_non_deterministic_control_is_named()`
  - Method `.test_the_class_identity_control_is_named()`
  - Method `.test_the_no_proposal_control_is_named_once()`
  - Method `.test_both_shipped_providers_are_registered()`
  - Method `.test_a_widened_contract_is_named()`
  - Method `.test_a_missing_control_is_named()`
  - Method `.test_an_unregistered_provider_is_named()`

---

### [`tests/test_backend_contract.py`](tests/test_backend_contract.py)
> *A backend seam is only pluggable if a provider can be checked, not read.*

**Size**: `147` lines (`5262` bytes)

**Classes:**
- `class _Echo` - *Minimal conforming provider: returns the first legal token.*
  - Method `.identity()`
  - Method `.generate(observation)`
- `class _NoIdentity`
  - Method `.generate(observation)`
- `class _Raising`
  - Method `.identity()`
  - Method `.generate(observation)`
- `class _ReturnsNone`
  - Method `.identity()`
  - Method `.generate(observation)`
- `class _ReturnsInt`
  - Method `.identity()`
  - Method `.generate(observation)`
- `class TestBackendContract`
  - Method `.test_the_abc_requires_generate()`
  - Method `.test_identity_is_part_of_the_protocol()`
  - Method `.test_identity_survives_a_class_rename()`
  - Method `.test_a_conforming_provider_passes()`
  - Method `.test_a_missing_identity_is_named()`
  - Method `.test_a_raising_provider_is_reported_not_swallowed()`
  - Method `.test_a_none_proposal_is_named()`
  - Method `.test_a_non_string_proposal_is_named()`
  - Method `.test_determinism_is_checked()`
  - Method `.test_the_registry_builds_a_known_provider()`
  - Method `.test_an_unknown_name_raises_and_names_the_choices()`
  - Method `.test_registering_a_duplicate_raises()`
  - Method `.test_the_registry_names_what_it_has()`

---

### [`tests/test_battery_contract.py`](tests/test_battery_contract.py)
> *A battery must fail loudly, not merely print.*

**Size**: `112` lines (`4647` bytes)

**Classes:**
- `class TestBatteryContract`
  - Method `.test_no_findings_is_success()`
  - Method `.test_any_finding_is_failure()`
  - Method `.test_result_carries_ok_and_findings()`
  - Method `.test_result_without_findings_is_ok()`
  - Method `.test_format_findings_is_one_line_each()`
  - Method `.test_a_battery_exits_non_zero_when_it_reports_a_finding()`
- `class TestBatteryAudit`
  - Method `.test_audit_reports_the_shipped_batteries()`
  - Method `.test_audit_still_names_the_uncovered_batteries()`
  - Method `.test_audit_finds_both_populations()`
  - Method `.test_audit_of_a_missing_directory_degrades()`

---

### [`tests/test_blocked_corridor.py`](tests/test_blocked_corridor.py)
> *Blocked-corridor entry: goal column/row with an obstacle in between.*

**Size**: `52` lines (`1843` bytes)

**Classes:**
- `class BlindPlanner`
  - Method `.plan(state, memories)`
- `class TestBlockedCorridor`
  - Method `.test_seed479_optimal_10()`
  - Method `.test_t3_400_499_total()`
  - Method `.test_ablation_blind_truncates_corridor_trap()`

**Functions:**
- `def _steps(task, seed, planner, max_steps)`

---

### [`tests/test_budget.py`](tests/test_budget.py)
> *Execution budgets: steps, LLM calls, tokens and wall time.*

**Size**: `137` lines (`5425` bytes)

**Classes:**
- `class WaitingBackend`
  - Method `.__init__()`
  - Method `.generate(observation)`
- `class PromptBackend` - *Decline but report a fixed prompt token cost.*
  - Method `.__init__(tokens)`
  - Method `.generate(observation)`
- `class TestExecutionBudget`
  - Method `.test_spend_pressure_and_snapshot()`
  - Method `.test_step_limit_raises()`
  - Method `.test_zero_seconds_raises()`
  - Method `.test_context_scope_is_opt_in()`
  - Method `.test_invalid_limits_and_kind_rejected()`
  - Method `.test_generous_budget_keeps_agent_actions()`
  - Method `.test_step_budget_stops_before_next_action()`
  - Method `.test_llm_call_budget_stops_before_next_call()`
  - Method `.test_token_budget_spends_prompt_stats()`
  - Method `.test_elapsed_and_remaining()`

---

### [`tests/test_budget_surface.py`](tests/test_budget_surface.py)
> *Shipped public API must be reachable or it is dead weight.*

**Size**: `81` lines (`3364` bytes)

**Classes:**
- `class TestBudgetSurface`
  - Method `.test_push_and_pop_are_gone()`
  - Method `.test_use_budget_is_the_supported_installer()`
  - Method `.test_use_budget_nests_and_restores()`
  - Method `.test_use_budget_restores_on_exception()`
  - Method `.test_no_module_in_the_tree_references_the_removed_names()`
  - Method `.test_budget_module_still_parses_and_exports_its_contract()`

---

### [`tests/test_calibration.py`](tests/test_calibration.py)
> *Calibration scoring: Brier, log loss, skill and reliability bins.*

**Size**: `115` lines (`4567` bytes)

**Classes:**
- `class TestCalibration`
  - Method `.test_perfect_forecast()`
  - Method `.test_inverted_forecast()`
  - Method `.test_calibrated_fixture_discriminates()`
  - Method `.test_unresolved_outcomes_ignored()`
  - Method `.test_empty_and_small_samples_warn()`
  - Method `.test_invalid_inputs_rejected()`
  - Method `.test_selfmodel_records_confidence_and_outcomes()`

**Functions:**
- `def _forecast(identifier, probability, outcome)`
- `def _perfect()`
- `def _inverted()`

---

### [`tests/test_calibration_autoretention.py`](tests/test_calibration_autoretention.py)
> *Automatic calibration retention at the logged-run bridge.*

**Size**: `176` lines (`8163` bytes)

**Classes:**
- `class TestCalibrationAutoRetention`
  - Method `.test_single_run_retains_ten()`
  - Method `.test_second_run_extends_the_archive()`
  - Method `.test_no_threshold_keeps_all_live()`
  - Method `.test_keep_recent_without_path_rejected()`
  - Method `.test_invalid_keep_recent_rejected()`
  - Method `.test_corrupt_archive_fails_after_verdict()`
  - Method `.test_keep_one_is_allowed()`
  - Method `.test_retained_actions_match_unretained()`

**Functions:**
- `def _run(tmp, agent, task, seed, name, calibration_path, keep)`

---

### [`tests/test_calibration_bridge.py`](tests/test_calibration_bridge.py)
> *SelfModel forecast bridge: logged runs persist their own forecasts.*

**Size**: `210` lines (`9797` bytes)

**Classes:**
- `class TestCalibrationBridge`
  - Method `.test_selfmodel_forecasts_prefix_and_slice()`
  - Method `.test_logged_run_persists_only_this_run()`
  - Method `.test_logged_summary_matches_in_memory()`
  - Method `.test_keyed_bridge_roundtrip_and_wrong_key()`
  - Method `.test_keyed_bridge_requires_a_path()`
  - Method `.test_invalid_bridge_key_rejected()`
  - Method `.test_default_none_writes_nothing()`
  - Method `.test_bridge_requires_a_self_model()`
  - Method `.test_bridge_requires_forecast_api()`
  - Method `.test_append_failure_surfaces_after_verdict()`
  - Method `.test_bridge_does_not_change_actions()`

**Functions:**
- `def _run(tmp, task, seed, calibration_path, agent, log_name)`

---

### [`tests/test_calibration_checks.py`](tests/test_calibration_checks.py)
> *The calibration battery must check its own fixtures.*

**Size**: `106` lines (`4133` bytes)

**Classes:**
- `class TestCalibrationChecks`
  - Method `.setUpClass()`
  - Method `.test_a_real_run_has_no_findings()`
  - Method `.test_every_fixture_scores_as_documented()`
  - Method `.test_perfect_beats_inverted()`
  - Method `.test_small_sample_warns_and_inverted_warns()`
  - Method `.test_the_real_run_keeps_its_pinned_score()`
  - Method `.test_a_moved_brier_is_named()`
  - Method `.test_a_moved_skill_is_named()`
  - Method `.test_a_suddenly_resolved_small_sample_is_named()`
  - Method `.test_a_missing_mode_is_named()`

**Functions:**
- `def _case(report, mode)`

---

### [`tests/test_calibration_retention.py`](tests/test_calibration_retention.py)
> *Calibration-journal retention: archive older forecasts, keep the newest.*

**Size**: `278` lines (`12718` bytes)

**Classes:**
- `class TestCalibrationRetention`
  - Method `.test_rotate_splits_and_preserves_score()`
  - Method `.test_second_rotation_extends_the_archive()`
  - Method `.test_append_with_threshold_rotates()`
  - Method `.test_append_threshold_is_incremental()`
  - Method `.test_append_threshold_noop_under_limit()`
  - Method `.test_append_threshold_corrupt_archive_keeps_records()`
  - Method `.test_append_invalid_threshold_rejected()`
  - Method `.test_short_journal_is_a_noop()`
  - Method `.test_conflicting_archive_id_rejected()`
  - Method `.test_corrupt_live_or_archive_rejected()`
  - Method `.test_missing_live_is_a_noop()`
  - Method `.test_invalid_parameters_rejected()`
  - Method `.test_stale_lock_is_stolen()`
  - Method `.test_fresh_lock_times_out_without_rotation()`

**Functions:**
- `def _forecasts(rows)`

---

### [`tests/test_calibration_store.py`](tests/test_calibration_store.py)
> *Calibration forecast journal: append-only, checksummed, cross-run.*

**Size**: `319` lines (`14829` bytes)

**Classes:**
- `class TestCalibrationStore`
  - Method `.test_append_and_load_roundtrip()`
  - Method `.test_two_runs_aggregate_to_ten()`
  - Method `.test_duplicate_id_refused_without_writing()`
  - Method `.test_duplicate_within_batch_refused()`
  - Method `.test_invalid_batch_writes_nothing()`
  - Method `.test_tampered_record_fails_verify_and_load()`
  - Method `.test_corrupt_line_names_the_line()`
  - Method `.test_keyed_journal_roundtrip_and_wrong_key()`
  - Method `.test_keyed_journal_requires_macs()`
  - Method `.test_keyed_journal_detects_recomputed_checksum()`
  - Method `.test_keyed_rotation_preserves_records_and_score()`
  - Method `.test_invalid_hmac_key_rejected()`
  - Method `.test_unkeyed_append_over_keyed_journal_refused()`
  - Method `.test_unkeyed_rotation_over_keyed_journal_refused()`
  - Method `.test_missing_store_is_empty()`
  - Method `.test_unresolved_outcome_is_ignored()`
  - Method `.test_stale_lock_is_stolen()`
  - Method `.test_fresh_lock_times_out_without_writing()`
  - Method `.test_empty_append_is_a_noop()`
  - Method `.test_invalid_inputs_rejected()`

**Functions:**
- `def _forecasts(rows)`

---

### [`tests/test_chain.py`](tests/test_chain.py)
> *Tamper-evident telemetry: hash-chain probes.*

**Size**: `110` lines (`4108` bytes)

**Classes:**
- `class TestChain`
  - Method `.test_intact_chain_verifies()`
  - Method `.test_edited_record_detected()`
  - Method `.test_deleted_record_breaks_link()`
  - Method `.test_reordered_records_detected()`
  - Method `.test_legacy_unchained_record_flagged()`
  - Method `.test_corrupt_line_detected()`

**Functions:**
- `def _write_fixture(path)`
- `def _lines(path)`
- `def _rewrite(path, lines)`

---

### [`tests/test_chain_anchor.py`](tests/test_chain_anchor.py)
> *Terminal telemetry anchor: a truncated tail must not read back as valid.*

**Size**: `105` lines (`4186` bytes)

**Classes:**
- `class TestChainAnchor`
  - Method `.test_intact_log_passes_with_anchor()`
  - Method `.test_truncated_tail_detected_with_anchor()`
  - Method `.test_anchor_off_leaves_truncation_undetected()`
  - Method `.test_missing_anchor_reported()`
  - Method `.test_anchor_mismatch_reported()`
  - Method `.test_anchor_write_is_atomic_and_deterministic()`
  - Method `.test_write_anchor_helper_roundtrip()`

**Functions:**
- `def _log(path, records)`
- `def _truncate(path, keep)`

---

### [`tests/test_claim_evidence.py`](tests/test_claim_evidence.py)
> *Claim/evidence cross-link: verdict refs cite logged episode digests.*

**Size**: `98` lines (`3993` bytes)

**Classes:**
- `class TestClaimEvidence`
  - Method `.test_logged_episode_ref_roundtrip()`
  - Method `.test_two_run_refs_are_distinct()`
  - Method `.test_legacy_payload_without_ref_still_loads()`
  - Method `.test_invalid_ref_does_not_change_history()`

**Functions:**
- `def _run(tmp, task, seed, name)`

---

### [`tests/test_claim_forecasts.py`](tests/test_claim_forecasts.py)
> *A claim's declared confidence must be scoreable, not just stored.*

**Size**: `83` lines (`3488` bytes)

**Classes:**
- `class TestClaimForecasts`
  - Method `.test_resolved_claims_become_forecasts()`
  - Method `.test_a_proposed_claim_is_excluded()`
  - Method `.test_inconclusive_is_kept_as_unresolved()`
  - Method `.test_the_score_is_computable()`
  - Method `.test_an_all_confident_ledger_scores_badly()`
  - Method `.test_empty_ledger_yields_no_forecasts()`
  - Method `.test_the_mapping_does_not_change_the_ledger()`

**Functions:**
- `def _ledger()`

---

### [`tests/test_claim_ref_verify.py`](tests/test_claim_ref_verify.py)
> *Claim-ref verification: every referenced verdict must match a live log.*

**Size**: `320` lines (`15315` bytes)

**Classes:**
- `class TestClaimRefVerifier`
  - Method `.test_two_logs_verify_both_refs()`
  - Method `.test_missing_log_leaves_ref_unverified()`
  - Method `.test_fabricated_ref_unverified()`
  - Method `.test_unreferenced_verdict_reported()`
  - Method `.test_missing_log_path_rejected()`
  - Method `.test_log_without_header_rejected()`
  - Method `.test_malformed_log_rejected()`
  - Method `.test_multiple_headers_in_one_log_are_unioned()`
  - Method `.test_store_verifier_loads_and_checks()`
  - Method `.test_tampered_log_rejected_by_default()`
  - Method `.test_keyed_log_correct_and_wrong_key()`
  - Method `.test_invalid_options_rejected()`
  - Method `.test_store_verifier_can_require_chain()`
  - Method `.test_anchored_journal_verifies()`
  - Method `.test_truncated_log_passes_chain_but_fails_journal()`
  - Method `.test_missing_journal_rejected()`
  - Method `.test_journal_requires_verify_logs()`
  - Method `.test_two_logs_two_journals()`
  - Method `.test_single_journal_path_requires_one_log()`
  - Method `.test_unknown_journal_key_rejected()`
  - Method `.test_tampered_journal_rejected()`
  - Method `.test_store_verifier_passes_journal()`
  - Method `.test_store_verifier_authenticates_a_keyed_store()`
  - Method `.test_invalid_inputs_rejected()`

**Functions:**
- `def _run(tmp, task, seed, name)`
- `def _ledger(ref_one, ref_two)`

---

### [`tests/test_claim_replay.py`](tests/test_claim_replay.py)
> *Claim refs must be checkable against the trajectory, not just the header.*

**Size**: `114` lines (`5140` bytes)

**Classes:**
- `class TestClaimReplay`
  - Method `._fixture(directory)`
  - Method `.test_honest_log_verifies_with_replay_enabled()`
  - Method `.test_chain_valid_forgery_is_rejected()`
  - Method `.test_replay_is_opt_in_and_off_by_default()`
  - Method `.test_replay_requires_log_verification()`
  - Method `.test_replay_must_be_a_bool()`

**Functions:**
- `def _forged(log_path, out_path, action)` - *Re-emit a log through Telemetry with every step action replaced.*

---

### [`tests/test_claims.py`](tests/test_claims.py)
> *Claim/verdict records with kill tests and an immutable ledger.*

**Size**: `205` lines (`8938` bytes)

**Classes:**
- `class TestClaims`
  - Method `.test_add_claim_defaults_and_ids()`
  - Method `.test_record_verdict_history_and_immutability()`
  - Method `.test_verdict_ref_roundtrip()`
  - Method `.test_legacy_verdict_without_ref_loads_none()`
  - Method `.test_invalid_ref_rejected()`
  - Method `.test_ref_history_preserved()`
  - Method `.test_frozen_verdict_with_ref()`
  - Method `.test_inconclusive_verdict()`
  - Method `.test_summary_counts()`
  - Method `.test_invalid_inputs_rejected()`
  - Method `.test_to_dict_from_dict_roundtrip()`
  - Method `.test_status_must_match_verdict_history()`
  - Method `.test_from_dict_rejects_inconsistent_status()`
  - Method `.test_verdict_texts_validated_on_load()`
  - Method `.test_consistent_legacy_payload_loads()`
  - Method `.test_dataclasses_frozen()`

---

### [`tests/test_claims_store.py`](tests/test_claims_store.py)
> *Durable claim-ledger store: atomic snapshots, backups and quarantine.*

**Size**: `296` lines (`13574` bytes)

**Classes:**
- `class TestClaimStore`
  - Method `.test_roundtrip_preserves_claims_and_verdicts()`
  - Method `.test_refs_survive_snapshot()`
  - Method `.test_forged_status_with_valid_checksum_rejected()`
  - Method `.test_keyed_snapshot_roundtrip_and_wrong_key()`
  - Method `.test_keyed_snapshot_requires_a_mac()`
  - Method `.test_keyed_snapshot_detects_recomputed_checksum()`
  - Method `.test_unkeyed_save_over_keyed_snapshot_refused()`
  - Method `.test_invalid_hmac_key_rejected()`
  - Method `.test_missing_primary_returns_empty()`
  - Method `.test_second_save_backs_up_and_corrupt_recovers()`
  - Method `.test_missing_primary_loads_backup()`
  - Method `.test_tampered_payload_fails_verify_and_load()`
  - Method `.test_invalid_schema_rejected()`
  - Method `.test_stale_lock_is_stolen()`
  - Method `.test_fresh_lock_times_out_without_writing()`
  - Method `.test_no_temporary_files_after_saves()`
  - Method `.test_saved_at_makes_checksum_deterministic()`
  - Method `.test_invalid_inputs_rejected()`

**Functions:**
- `def _ledger(extra)`
- `def _rewrite(path, mutate)`

---

### [`tests/test_coldstart_recovery.py`](tests/test_coldstart_recovery.py)
> *Cold-start recovery: restart re-reads the persisted task layout.*

**Size**: `207` lines (`9159` bytes)

**Classes:**
- `class TestColdStartRecovery`
  - Method `.test_restart_recovers_layout_from_store()`
  - Method `.test_layout_ablation_truncates_at_cap()`
  - Method `.test_probe_names_persistent_source()`
  - Method `.test_warm_probe_uses_state_not_store()`
  - Method `.test_layout_first_write_wins()`
  - Method `.test_cold_first_does_not_poison_layout()`
  - Method `.test_warm_run_heals_incomplete_layout()`
  - Method `.test_completeness_gate_ablation_repoisons()`

**Functions:**
- `def _steps(log_path)`
- `def _layout_keys(store, task, seed)`

---

### [`tests/test_column_traps.py`](tests/test_column_traps.py)
> *Column-blocking traps: depth-2 lookahead enters blocked columns early.*

**Size**: `54` lines (`2030` bytes)

**Classes:**
- `class BlindPlanner`
  - Method `.plan(state, memories)`
- `class TestColumnTraps`
  - Method `.test_column_trap_seeds_optimal()`
  - Method `.test_t3_200_299_total()`
  - Method `.test_ablation_blind_truncates_column_traps()`

**Functions:**
- `def _steps(task, seed, planner, max_steps)`

---

### [`tests/test_corrected_counts.py`](tests/test_corrected_counts.py)
> *The corrected distinguishability counts, at one observation per step.*

**Size**: `77` lines (`3297` bytes)

**Classes:**
- `class TestCorrectedDistinguishability`
  - Method `.test_no_pinned_trace_is_distinguishable()`
  - Method `.test_the_scope_reports_one_row_per_step()`
  - Method `.test_the_syn_value_is_unchanged_by_dedupe()`
  - Method `.test_a_degenerate_null_reports_no_spread()`
  - Method `.test_dedupe_is_idempotent()`

---

### [`tests/test_cycle_escape.py`](tests/test_cycle_escape.py)
> *Repeated-position cycle escape: memory drives a BFS exit from a loop.*

**Size**: `139` lines (`5550` bytes)

**Classes:**
- `class _ForcedWorld`
  - Method `.__init__(target, obstacles)`
  - Method `._build_layout(rng)`
- `class BlindPlanner`
  - Method `.plan(state, memories)`
- `class DeclineBackend` - *Record the model-seam observation and force the rule fallback.*
  - Method `.__init__()`
  - Method `.generate(observation)`
- `class TestCycleEscape`
  - Method `.test_repeated_position_escape_recovers()`
  - Method `.test_memory_cut_restores_cap()`
  - Method `.test_escape_disabled_restores_cap()`
  - Method `.test_probe_records_escape_at_the_model_seam()`
  - Method `.test_escape_actions_deterministic()`
  - Method `.test_policy_declares_cycle_escape()`
  - Method `.test_invalid_cycle_escape_rejected()`

**Functions:**
- `def _run(target, obstacles, planner, max_steps)`

---

### [`tests/test_dead_pool.py`](tests/test_dead_pool.py)
> *Dead-pool guard: drop a dead goal step only when a live path is closer.*

**Size**: `96` lines (`3894` bytes)

**Classes:**
- `class DeclineBackend`
  - Method `.__init__()`
  - Method `.generate(observation)`
- `class TestDeadPool`
  - Method `.test_probe_records_excluded_dead_step()`
  - Method `.test_ablation_restores_detour()`
  - Method `.test_blind_still_truncates()`
  - Method `.test_guard_deterministic()`
  - Method `.test_policy_declares_dead_pool_filter()`
  - Method `.test_invalid_dead_pool_filter_rejected()`

---

### [`tests/test_degenerate_confidence.py`](tests/test_degenerate_confidence.py)
> *A calibration score must name circular confidence, not present it.*

**Size**: `93` lines (`3851` bytes)

**Classes:**
- `class TestConfidenceDiagnosis`
  - Method `.test_perfect_separation_is_diagnosed()`
  - Method `.test_genuine_spread_is_not_diagnosed()`
  - Method `.test_single_confidence_across_both_classes_is_diagnosed()`
  - Method `.test_single_outcome_class_is_not_diagnosed()`
  - Method `.test_partial_separation_is_not_diagnosed()`
  - Method `.test_summary_does_not_flag_a_perfect_forecast()`
  - Method `.test_self_model_calibration_flags_its_own_record()`
  - Method `.test_self_model_with_spread_is_not_flagged()`
  - Method `.test_the_real_agent_run_is_no_longer_flagged()`

**Functions:**
- `def _pairs(rows)`
- `def _flagged(result)`

---

### [`tests/test_duplicate_rows.py`](tests/test_duplicate_rows.py)
> *Every step emits two identical vector rows, so every statistic is over n=2T.*

**Size**: `94` lines (`3534` bytes)

**Classes:**
- `class TestDuplicateVectorRows`
  - Method `.test_every_step_emits_two_identical_rows()`
  - Method `.test_the_pair_is_byte_identical()`
  - Method `.test_dedupe_halves_the_row_count()`
  - Method `.test_dedupe_changes_no_header_record()`
  - Method `.test_the_collinearity_survives_dedupe()`
  - Method `.test_dedupe_is_order_preserving()`
  - Method `.test_dedupe_keeps_non_adjacent_repeats()`
  - Method `.test_dedupe_degrades_on_empty_input()`

**Functions:**
- `def _episode(task, seed)`
- `def _dependent_count(rows)`

---

### [`tests/test_episode_replay.py`](tests/test_episode_replay.py)
> *Action-replay verification: a valid chain does not prove the trajectory.*

**Size**: `122` lines (`5561` bytes)

**Classes:**
- `class TestActionReplay`
  - Method `.test_logged_steps_are_the_step_actions()`
  - Method `.test_replay_reproduces_the_recorded_trajectory()`
  - Method `.test_valid_chain_with_replaced_actions_is_caught()`
  - Method `.test_replay_stops_at_the_world_terminal()`
  - Method `.test_invalid_actions_are_named_not_raised()`
  - Method `.test_missing_header_is_named()`

**Functions:**
- `def _write_log(directory, name, task, seed)`
- `def _rewrite(log_path, out_path, action)` - *Re-emit a log through Telemetry with every step action replaced.*

---

### [`tests/test_episode_verify.py`](tests/test_episode_verify.py)
> *Episode-header verification: recompute episode_sha256 from the seed.*

**Size**: `273` lines (`12419` bytes)

**Classes:**
- `class TestEpisodeVerify`
  - Method `.test_logged_header_has_seed_and_verifies()`
  - Method `.test_wrong_seed_mismatch()`
  - Method `.test_wrong_episode_mismatch()`
  - Method `.test_missing_seed_reported()`
  - Method `.test_missing_header_reported()`
  - Method `.test_malformed_log_rejected()`
  - Method `.test_invalid_stored_policy_reported()`
  - Method `.test_workspace_pin_matches()`
  - Method `.test_workspace_pin_mismatch()`
  - Method `.test_workspace_pin_needs_a_stored_digest()`
  - Method `.test_invalid_stored_workspace_reported()`
  - Method `.test_claims_workspace_pin()`
  - Method `.test_invalid_expected_workspace_rejected()`
  - Method `.test_expected_policy_matches()`
  - Method `.test_expected_policy_mismatch()`
  - Method `.test_forged_policy_with_matching_episode_is_caught_by_pin()`
  - Method `.test_invalid_expected_policy_rejected()`
  - Method `.test_claims_expected_policy()`
  - Method `.test_claim_refs_verify_episodes()`
  - Method `.test_episode_check_is_opt_in()`

**Functions:**
- `def _run(tmp, task, seed, name, workspace_root)`
- `def _ledger(episode)`
- `def _rewrite_header(path, mutate)`

---

### [`tests/test_estimator_edges.py`](tests/test_estimator_edges.py)
> *Pin the estimator edge cases their docstrings promise.*

**Size**: `81` lines (`3067` bytes)

**Classes:**
- `class TestEstimatorEdges`
  - Method `.test_transfer_gain_neutral_on_nonpositive_naive()`
  - Method `.test_recovery_is_clipped_to_unit_interval()`
  - Method `.test_phi_neutral_below_three_rows_and_on_constant_input()`
  - Method `.test_synergy_neutral_on_empty_or_mismatched_input()`
  - Method `.test_mutual_information_neutral_without_variation()`
  - Method `.test_gbi_saturates_at_and_above_one()`
  - Method `.test_logistic_k_neutral_on_empty_or_mismatched_input()`
  - Method `.test_no_estimator_raises_on_degenerate_input()`

---

### [`tests/test_estimators.py`](tests/test_estimators.py)
> *Estimator unit checks: stdlib only.*

**Size**: `75` lines (`2595` bytes)

**Classes:**
- `class TestEstimators`
  - Method `.test_mi_nonnegative_correlated()`
  - Method `.test_syn_nonnegative_xor()`
  - Method `.test_phi_clip_and_signal()`
  - Method `.test_gbi_formula()`
  - Method `.test_transfer_recovery_formulas()`
  - Method `.test_logistic_k_r2_range()`
  - Method `.test_permutation_null_deterministic()`

---

### [`tests/test_execution_budget_checks.py`](tests/test_execution_budget_checks.py)
> *The execution-budget battery must enforce its own caps.*

**Size**: `96` lines (`3643` bytes)

**Classes:**
- `class TestExecutionBudgetChecks`
  - Method `.setUpClass()`
  - Method `.test_a_real_run_has_no_findings()`
  - Method `.test_each_mode_names_its_own_dimension()`
  - Method `.test_a_capped_run_exceeds_its_limit()`
  - Method `.test_generous_budget_preserves_the_rule_run()`
  - Method `.test_a_capped_run_is_not_a_success()`
  - Method `.test_a_budget_that_stops_enforcing_is_named()`
  - Method `.test_a_wrong_dimension_is_named()`
  - Method `.test_a_cap_above_its_limit_is_named()`
  - Method `.test_a_changed_generous_run_is_named()`
  - Method `.test_a_missing_mode_is_named()`

**Functions:**
- `def _case(report, mode)`

---

### [`tests/test_exhaustive_t3.py`](tests/test_exhaustive_t3.py)
> *Exhaustive T3 coverage: every (target, obstacle) config optimal.*

**Size**: `97` lines (`3468` bytes)

**Classes:**
- `class _ForcedLayoutWorld` - *GridWorld with a fixed T3 layout, built through the class hook.*
  - Method `.__init__(target, obstacle)`
  - Method `._build_layout(rng)`
- `class TestExhaustiveT3`
  - Method `.test_all_3906_configs_optimal()`

**Functions:**
- `def _bfs_optimal(target, obstacle)`
- `def _run_config(target, obstacle, max_steps)`

---

### [`tests/test_file_locks.py`](tests/test_file_locks.py)
> *Advisory lock ownership: a stale-lock victim must not delete its successor.*

**Size**: `70` lines (`2568` bytes)

**Classes:**
- `class TestFileLockOwnership`
  - Method `._check(lock_factory)`
  - Method `.test_telemetry_lock_preserves_successor()`
  - Method `.test_claim_store_lock_preserves_successor()`
  - Method `.test_calibration_store_lock_preserves_successor()`

**Functions:**
- `def _steal_and_replace(lock_path, new_token)`
- `def _normal_release(lock_factory, target)`
- `def _stolen_release(lock_factory, target)`

---

### [`tests/test_golden_traces.py`](tests/test_golden_traces.py)
> *Golden trace hashes: exact action sequences for the pin seeds.*

**Size**: `47` lines (`2090` bytes)

**Classes:**
- `class TestGoldenTraces`
  - Method `.test_pin_seeds_match_golden_hashes()`

**Functions:**
- `def _fingerprint(trace)`

---

### [`tests/test_header_reader_checks.py`](tests/test_header_reader_checks.py)
> *The header-reader battery must check its own memory claim.*

**Size**: `87` lines (`3466` bytes)

**Classes:**
- `class TestHeaderReaderChecks`
  - Method `.setUpClass()`
  - Method `.test_a_real_run_has_no_findings()`
  - Method `.test_header_mode_returns_only_headers()`
  - Method `.test_all_mode_retains_every_record()`
  - Method `.test_header_mode_retains_far_less()`
  - Method `.test_both_modes_see_the_same_headers()`
  - Method `.test_a_header_reader_that_retains_everything_is_named()`
  - Method `.test_a_header_reader_that_returns_everything_is_named()`
  - Method `.test_a_lost_header_is_named()`
  - Method `.test_a_missing_mode_is_named()`

**Functions:**
- `def _mode(report, name)`

---

### [`tests/test_hidden_goal.py`](tests/test_hidden_goal.py)
> *Hidden-goal recovery: planner recalls missing goals from episode memory.*

**Size**: `94` lines (`2949` bytes)

**Classes:**
- `class _Capture`
  - Method `.__init__()`
  - Method `.generate(observation)`
- `class TestHiddenGoal`
  - Method `.test_hidden_target_recovered()`
  - Method `.test_hidden_items_recovered()`
  - Method `.test_memory_lesion_kills_hidden_recovery()`

**Functions:**
- `def _hidden_steps(task, seed, strip, blind, max_steps)`
- `def _hidden_obs(task, seed, strip, upto)`

---

### [`tests/test_holdout_500s.py`](tests/test_holdout_500s.py)
> *Frozen holdout split: seeds 500-599 pinned as regression holdout.*

**Size**: `35` lines (`1199` bytes)

**Classes:**
- `class TestHoldout500s`
  - Method `.test_holdout_500_599_totals()`

**Functions:**
- `def _steps(task, seed, max_steps)`

---

### [`tests/test_identity.py`](tests/test_identity.py)
> *Episode identity and resume policy (neurocore transfer).*

**Size**: `146` lines (`5881` bytes)

**Classes:**
- `class FakeEpisode`
  - Method `.__init__(sha)`
  - Method `.update_phase(phase)`
- `class FakeSession`
  - Method `.__init__()`
  - Method `.save_episode_state(**kwargs)`
- `class TestEpisodeIdentity`
  - Method `.test_volatile_fields_are_ignored()`
  - Method `.test_changed_target_changes_digest()`
  - Method `.test_changed_config_changes_digest()`
  - Method `.test_projection_is_canonical()`
  - Method `.test_resume_decision_matrix()`
  - Method `.test_resume_guard_fake_episode()`
  - Method `.test_prepare_resume_pauses_refused_candidate()`
  - Method `.test_prepare_resume_allows_matching_candidate()`
  - Method `.test_logged_header_carries_episode_identity()`

---

### [`tests/test_integration_differentials.py`](tests/test_integration_differentials.py)
> *Integration-structure differentials: hub/M lesions kill syn, P/S change nothing.*

**Size**: `103` lines (`4407` bytes)

**Classes:**
- `class TestIntegrationDifferentials`
  - Method `._fixed_steps(tmp)`
  - Method `.test_signal_present_and_phi_floor()`
  - Method `.test_hub_and_memory_lesions_kill_synergy()`
  - Method `.test_planner_and_selfmodel_lesions_change_nothing()`
  - Method `.test_planner_and_selfmodel_are_invisible_to_synergy()`

**Functions:**
- `def _pad(rows)`
- `def _stats(rows)`

---

### [`tests/test_joint_binning_scale.py`](tests/test_joint_binning_scale.py)
> *The joint MI must not be the coarsest of the three scalings.*

**Size**: `93` lines (`3747` bytes)

**Classes:**
- `class TestJointBinningScale`
  - Method `.test_the_joint_range_is_eight_times_the_column_range()`
  - Method `.test_a_single_bin_count_cannot_serve_both_scales()`
  - Method `.test_the_pinned_gap_changes_sign_with_the_bin_count()`
  - Method `.test_the_shipped_value_is_the_fine_one()`
  - Method `.test_the_scope_columns_are_the_pair_the_joint_uses()`

**Functions:**
- `def _rows(task, seed)`
- `def _codes(trace)`

---

### [`tests/test_layout_fingerprint.py`](tests/test_layout_fingerprint.py)
> *Layout fingerprints: distinct worlds sharing (task, seed) must not collide.*

**Size**: `119` lines (`4684` bytes)

**Classes:**
- `class _World` - *T3 world with forced geometry, optionally hiding goal fields.*
  - Method `.__init__(target, obstacles, hidden)`
  - Method `._build_layout(rng)`
  - Method `._state()`
- `class TestLayoutFingerprint`
  - Method `.test_distinct_worlds_same_key_do_not_collide()`
  - Method `.test_builtin_fingerprint_stable_across_reset()`
  - Method `.test_blind_fingerprint_ablation_restores_collision()`
  - Method `.test_legacy_row_gains_fingerprint_and_stops_colliding()`

**Functions:**
- `def _run(store, target, obstacles, hidden, max_steps)`

---

### [`tests/test_lesion_detectability.py`](tests/test_lesion_detectability.py)
> *Lesion detectability: a differential must be able to fail for its reason.*

**Size**: `99` lines (`4108` bytes)

**Classes:**
- `class TestLesionDetectability`
  - Method `.test_module_spans_cover_the_m_ps_hub_layout()`
  - Method `.test_module_columns_lists_the_span()`
  - Method `.test_synergy_sees_m_and_hub_only()`
  - Method `.test_detectability_reports_which_modules_are_visible()`
  - Method `.test_a_vacuous_lesion_is_named_not_counted_as_evidence()`
  - Method `.test_substitution_preserves_shape_and_other_modules()`
  - Method `.test_scope_still_reports_insufficiency_after_substitution()`

**Functions:**
- `def _rows(width, n)` - *Deterministic rows whose module block occupies columns 0..width-1.*

---

### [`tests/test_llamacpp.py`](tests/test_llamacpp.py)
> *llama.cpp backend: deterministic prompt building and action parsing.*

**Size**: `31` lines (`1129` bytes)

**Classes:**
- `class TestLlamaCppProtocol`
  - Method `.test_build_prompt_deterministic_and_complete()`
  - Method `.test_parse_action_first_legal_token_wins()`
  - Method `.test_parse_action_rejects_garbage()`

---

### [`tests/test_manifest.py`](tests/test_manifest.py)
> *Generation manifest fingerprints: determinism + prompt-set versioning.*

**Size**: `94` lines (`3861` bytes)

**Classes:**
- `class TestManifest`
  - Method `.test_same_inputs_same_sha256()`
  - Method `.test_prompt_change_changes_sha256()`
  - Method `.test_visits_change_changes_sha256()`
  - Method `.test_planner_obs_prompt_manifest_chain_stable()`
  - Method `.test_prompt_set_manifest_order_independent()`
  - Method `.test_backend_exposes_last_manifest_slot()`

**Functions:**
- `def _enriched_obs()`
- `def _sampling()`

---

### [`tests/test_manifest_binding.py`](tests/test_manifest_binding.py)
> *Model-manifest binding: every model decision carries its generation hash.*

**Size**: `132` lines (`5316` bytes)

**Classes:**
- `class ManifestBackend` - *Record the observation, compute its manifest, then decline.*
  - Method `.__init__(checkpoint, model_id)`
  - Method `.generate(observation)`
- `class StaleRaisingBackend` - *Leave a stale manifest behind, then raise before computing a new one.*
  - Method `.__init__()`
  - Method `.generate(observation)`
- `class TestManifestBinding`
  - Method `.test_each_decision_binds_its_manifest()`
  - Method `.test_checkpoint_swap_changes_manifest_not_actions()`
  - Method `.test_probe_off_removes_binding_without_changing_actions()`
  - Method `.test_raising_backend_does_not_leak_stale_manifest()`
  - Method `.test_policy_declares_manifest_probe()`
  - Method `.test_invalid_manifest_probe_rejected()`

**Functions:**
- `def _run(tmp, backend, probe_manifest)`
- `def _decision(record)`

---

### [`tests/test_memory.py`](tests/test_memory.py)
> *Unit tests for memory.store.MemoryStore.*

**Size**: `69` lines (`2517` bytes)

**Classes:**
- `class TestMemoryStore`
  - Method `.test_save_and_count()`
  - Method `.test_save_overwrites_same_key()`
  - Method `.test_recall_fts_and_fallback()`
  - Method `.test_recall_limit_and_order()`
  - Method `.test_snapshot_deterministic()`

---

### [`tests/test_merkle.py`](tests/test_merkle.py)
> *Merkle batch anchors and inclusion proofs (merklock transfer).*

**Size**: `150` lines (`6078` bytes)

**Classes:**
- `class TestMerkleTree`
  - Method `.test_root_and_proof_roundtrip()`
  - Method `.test_odd_tree_promotes_without_duplication()`
  - Method `.test_empty_tree_is_deterministic()`
  - Method `.test_proof_rejects_out_of_range()`
- `class TestMerkleAnchor`
  - Method `.test_batch_anchor_and_proof()`
  - Method `.test_anchor_detects_truncated_log()`
  - Method `.test_anchor_detects_tampered_root()`
  - Method `.test_anchor_detects_edited_record_digest()`
  - Method `.test_proof_rejects_tampered_leaf()`
  - Method `.test_missing_anchor_reported()`
  - Method `.test_anchor_write_is_atomic()`

**Functions:**
- `def _leaves(count)`
- `def _log(path, records)`
- `def _truncate(path, keep)`

---

### [`tests/test_merkle_compaction.py`](tests/test_merkle_compaction.py)
> *Merkle journal compaction: one union root, original preserved or backed up.*

**Size**: `171` lines (`7359` bytes)

**Classes:**
- `class TestMerkleCompaction`
  - Method `.test_copy_merges_three_batches_and_keeps_original()`
  - Method `.test_replace_backs_up_the_original()`
  - Method `.test_missing_journal_rejected()`
  - Method `.test_truncated_log_rejected()`
  - Method `.test_same_output_without_replace_rejected()`
  - Method `.test_invalid_replace_rejected()`
  - Method `.test_proof_outside_union_rejected()`
  - Method `.test_compaction_metadata_is_written()`

**Functions:**
- `def _log(path, records)`
- `def _three_batches(path)`
- `def _truncate(path, keep)`
- `def _journal_records(path)`

---

### [`tests/test_merkle_journal.py`](tests/test_merkle_journal.py)
> *Append-only Merkle batch journal and historical inclusion proofs.*

**Size**: `214` lines (`9379` bytes)

**Classes:**
- `class TestMerkleJournal`
  - Method `.test_two_batches_chain_and_historical_proof()`
  - Method `.test_truncated_log_names_the_batch()`
  - Method `.test_deleted_first_anchor_breaks_prev()`
  - Method `.test_tampered_root_with_resigned_hash_is_named()`
  - Method `.test_tampered_hash_is_named()`
  - Method `.test_range_rollback_rejected_on_append()`
  - Method `.test_missing_and_empty_journal_reported()`
  - Method `.test_journal_links_verify_without_a_log()`
  - Method `.test_proof_outside_every_batch_rejected()`
  - Method `.test_telemetry_wrapper_and_atomic_append()`
  - Method `.test_single_anchor_api_unchanged()`

**Functions:**
- `def _log(path, records)`
- `def _truncate(path, keep)`
- `def _canonical(value)`
- `def _resign(record)`
- `def _rewrite(path, records)`

---

### [`tests/test_model_backend.py`](tests/test_model_backend.py)
> *Model-backend seam: replay fidelity, invalid, raising, no-op and stall fallbacks.*

**Size**: `413` lines (`19066` bytes)

**Classes:**
- `class RaisingBackend`
  - Method `.generate(observation)`
- `class WaitingBackend` - *Legal but stalled proposal: never moves or rewards.*
  - Method `.__init__()`
  - Method `.generate(observation)`
- `class BlockedBackend` - *Propose a boundary/obstacle-blocked direction when one exists.*
  - Method `.__init__()`
  - Method `.generate(observation)`
- `class WrongWayBackend` - *Legal free-cell movement that maximises distance to the target.*
  - Method `.__init__()`
  - Method `._distance(start, target, obstacles)`
  - Method `.generate(observation)`
- `class AlternatingBackend` - *Wrong-way on odd calls, wait on even calls, breaking any streak.*
  - Method `.generate(observation)`
- `class TestModelBackendSeam`
  - Method `.test_stub_replays_rule_trace_exactly()`
  - Method `.test_invalid_tokens_fall_back_to_rule()`
  - Method `.test_raising_backend_falls_back_to_rule()`
  - Method `.test_stalled_legal_backend_falls_back_after_window()`
  - Method `.test_trust_window_none_restores_the_stall()`
  - Method `.test_noop_proposal_rejected_immediately()`
  - Method `.test_blocked_movement_rejected_immediately()`
  - Method `.test_blocked_movement_without_guard_uses_stall_window()`
  - Method `.test_distrust_skip_disabled_calls_after_window()`
  - Method `.test_noop_guard_independent_of_trust_window()`
  - Method `.test_good_backend_keeps_zero_fallbacks()`
  - Method `.test_progress_guard_rejects_wrong_way_backend()`
  - Method `.test_progress_guard_off_restores_wrong_way_cost()`
  - Method `.test_progress_guard_leaves_item_tours_untouched()`
  - Method `.test_progress_guard_independent_of_noop_guard()`
  - Method `.test_progress_skip_stops_calls_after_streak()`
  - Method `.test_progress_skip_none_keeps_all_calls()`
  - Method `.test_progress_skip_requires_consecutive_rejections()`
  - Method `.test_progress_skip_resets_between_episodes()`
  - Method `.test_invalid_progress_skip_after_rejected()`
  - Method `.test_policy_declares_backend_trust_and_noop_guard()`
  - Method `.test_invalid_progress_guard_rejected()`
  - Method `.test_invalid_trust_window_rejected()`
  - Method `.test_invalid_noop_guard_rejected()`
  - Method `.test_invalid_skip_after_distrust_rejected()`

**Functions:**
- `def _rule_actions(task, seed, max_steps)`

---

### [`tests/test_model_pin.py`](tests/test_model_pin.py)
> *The header's model label must be pinnable, like the policy digest.*

**Size**: `108` lines (`4782` bytes)

**Classes:**
- `class TestModelPin`
  - Method `.test_matching_model_pin_passes()`
  - Method `.test_wrong_model_pin_is_named()`
  - Method `.test_missing_model_is_named_when_pinned()`
  - Method `.test_pin_is_opt_in()`
  - Method `.test_invalid_model_pin_is_rejected()`

**Functions:**
- `def _write_log(directory, name, task, seed)`
- `def _rewrite_model(log_path, out_path, model)`

---

### [`tests/test_module_pair_scan.py`](tests/test_module_pair_scan.py)
> *A module interaction needs two module blocks, not the world hub.*

**Size**: `142` lines (`5735` bytes)

**Classes:**
- `class TestModulePairScan`
  - Method `.test_blocks_label_the_legacy_vector()`
  - Method `.test_pooled_scan_reports_world_pairs()`
  - Method `.test_module_pair_accepts_only_cross_module_blocks()`
  - Method `.test_world_interactions_match_the_hub_subset()`
  - Method `.test_world_interactions_exclude_module_pairs()`
  - Method `.test_pooled_module_interactions_are_empty()`
  - Method `.test_module_interactions_require_two_different_blocks()`
  - Method `.test_a_cross_module_planted_pair_is_detected()`
  - Method `.test_the_ablation_keeps_the_world_pairs()`

**Functions:**
- `def _episode(seed)`
- `def _pooled(seeds)`
- `def _cross_module(n, seed)` - *A planted XOR between column 0 (M) and column 2 (P).*

---

### [`tests/test_module_signals.py`](tests/test_module_signals.py)
> *The module-state channel must add testable state without changing actions.*

**Size**: `145` lines (`6652` bytes)

**Classes:**
- `class TestModuleSignals`
  - Method `.test_signals_are_emitted()`
  - Method `.test_module_signals_can_be_disabled()`
  - Method `.test_signal_scan_has_more_testable_module_pairs_than_legacy()`
  - Method `.test_the_s_block_is_independent()`
  - Method `.test_the_seen_mode_is_dependent()`
  - Method `.test_keys_mode_adds_one_testable_pair()`
  - Method `.test_module_interactions_are_empty_at_200_trials()`
  - Method `.test_signals_do_not_change_actions()`
  - Method `.test_block_split_reaches_module_and_world()`
  - Method `.test_malformed_signal_rows_are_ignored()`

**Functions:**
- `def _logs(directory, module_signals, seeds, task, module_s_mode)`
- `def _cross_module_count(reports)`

---

### [`tests/test_multi_goldens.py`](tests/test_multi_goldens.py)
> *Multi-obstacle golden paths: exact action sequences for two-blocker traps.*

**Size**: `46` lines (`1969` bytes)

**Classes:**
- `class TestMultiGoldens`
  - Method `.test_multi_paths_match_golden_hashes()`

**Functions:**
- `def _fingerprint(trace)`

---

### [`tests/test_multi_obstacle.py`](tests/test_multi_obstacle.py)
> *Multi-obstacle recovery: leaf viability alone truncates with two blockers.*

**Size**: `84` lines (`3235` bytes)

**Classes:**
- `class _ForcedMultiWorld`
  - Method `.__init__(target, obstacles)`
  - Method `._build_layout(rng)`
- `class BlindPlanner`
  - Method `.plan(state, memories)`
- `class TestMultiObstacle`
  - Method `.test_multi_obstacle_recovery()`
  - Method `.test_blind_kills_multi_recovery()`
  - Method `.test_standing_totals_untouched()`

**Functions:**
- `def _multi_steps(target, obstacles, planner, max_steps)`

---

### [`tests/test_negative_control.py`](tests/test_negative_control.py)
> *Executable negative controls for shipped planner integrations.*

**Size**: `52` lines (`1972` bytes)

**Classes:**
- `class TestNegativeControl`
  - Method `.test_corridor_control_fails_reproducibly()`
  - Method `.test_intact_side_of_control_pair()`

**Functions:**
- `def _steps(task, seed, max_steps)`

---

### [`tests/test_obs_coverage.py`](tests/test_obs_coverage.py)
> *Model-seam observation coverage: backend sees the goal state.*

**Size**: `106` lines (`3933` bytes)

**Classes:**
- `class _Capture`
  - Method `.__init__()`
  - Method `.generate(observation)`
- `class _ObsOracle`
  - Method `.generate(observation)`
- `class TestObsCoverage`
  - Method `.test_planner_obs_carries_goal_state()`
  - Method `.test_build_prompt_mentions_goal_state()`
  - Method `.test_obs_oracle_matches_rule_on_steerable_seeds()`

**Functions:**
- `def _obs_for(state)`
- `def _oracle_action(obs)` - *Obs-only policy: same geometry helpers, no episode memory.*
- `def _oracle_steps(task, seed, max_steps)`

---

### [`tests/test_obs_visits.py`](tests/test_obs_visits.py)
> *Model-seam visit coverage: backend sees loop-avoidance memory.*

**Size**: `107` lines (`3647` bytes)

**Classes:**
- `class _Capture`
  - Method `.__init__()`
  - Method `.generate(observation)`
- `class _VisitOracle`
  - Method `.generate(observation)`
- `class TestObsVisits`
  - Method `.test_planner_obs_carries_visits()`
  - Method `.test_build_prompt_mentions_visits()`
  - Method `.test_visit_oracle_matches_rule_on_tie_trap()`

**Functions:**
- `def _obs_for(state, memories)`
- `def _visits_from_obs(obs)`
- `def _oracle_action(obs)`
- `def _oracle_steps(task, seed, max_steps)`

---

### [`tests/test_online_learning.py`](tests/test_online_learning.py)
> *A predictor that is never told the reward rule must still learn it.*

**Size**: `126` lines (`5162` bytes)

**Classes:**
- `class TestOnlineLearning`
  - Method `.test_the_untold_predictor_learns_positive_skill()`
  - Method `.test_the_prediction_precedes_the_observation()`
  - Method `.test_the_learned_table_reconstructs_the_reward_rule()`
  - Method `.test_an_unseen_key_predicts_the_prior()`
  - Method `.test_laplace_smoothing_handles_a_single_observation()`
  - Method `.test_distance_bucket_caps_and_reports_absence()`
  - Method `.test_the_score_is_not_the_base_rate_in_disguise()`

**Functions:**
- `def _brier(pairs)`
- `def _episodes()` - *Yield (key, outcome) in a fixed order, with the pre-action key.*
- `def _prequential_score()`

---

### [`tests/test_pair_conclusions.py`](tests/test_pair_conclusions.py)
> *Pair-level conclusions must be re-derived at one observation per step.*

**Size**: `125` lines (`5556` bytes)

**Classes:**
- `class TestPairConclusionsAtCorrectN`
  - Method `.test_uniform_duplication_leaves_syn_unchanged()`
  - Method `.test_the_artifact_gate_verdicts_survive_dedupe()`
  - Method `.test_the_independent_pairs_are_the_same_at_correct_n()`
  - Method `.test_the_gaps_are_unchanged_by_dedupe()`
  - Method `.test_every_independent_pair_is_refused_by_the_target_gate()`
  - Method `.test_anti_interactions_are_empty_at_correct_n()`
  - Method `.test_interactions_remain_empty()`

**Functions:**
- `def _raw(task, seed, wired)`
- `def _split(rows)`

---

### [`tests/test_pair_scan.py`](tests/test_pair_scan.py)
> *A pair search must refuse artifacts before it reports a gap.*

**Size**: `116` lines (`4971` bytes)

**Classes:**
- `class TestPairScan`
  - Method `.test_a_constant_partner_is_refused()`
  - Method `.test_the_artifact_has_a_large_gap_and_no_mi()`
  - Method `.test_identical_partners_give_identical_gaps()`
  - Method `.test_the_scan_sorts_refused_pairs_last()`
  - Method `.test_no_shipped_pair_is_a_positive_interaction()`
  - Method `.test_anti_interactions_are_never_counted_as_interactions()`
  - Method `.test_functionally_dependent_columns_are_refused()`
  - Method `.test_an_empty_trace_degrades()`

**Functions:**
- `def _shipped(task, seed)`

---

### [`tests/test_pair_scan_fwer.py`](tests/test_pair_scan_fwer.py)
> *Scanning every pair needs a family-wise null, not per-pair tails.*

**Size**: `127` lines (`5509` bytes)

**Classes:**
- `class TestPairScanFamilyWise`
  - Method `.test_uncorrected_scan_flags_a_decoy_pair()`
  - Method `.test_corrected_scan_keeps_the_planted_pair()`
  - Method `.test_corrected_scan_refuses_the_decoy_pair()`
  - Method `.test_correction_reduces_the_selected_set()`
  - Method `.test_anti_interactions_use_the_same_correction()`
  - Method `.test_family_size_is_the_valid_pair_count()`
  - Method `.test_the_correction_is_deterministic()`
  - Method `.test_no_shipped_pair_survives_the_correction()`

**Functions:**
- `def _planted(n, decoys, seed)` - *One XOR pair plus independent binary decoys; no world, no agent.*
- `def _shipped(task, seed)`

---

### [`tests/test_pair_scan_target_column.py`](tests/test_pair_scan_target_column.py)
> *The target column is not a feature.*

**Size**: `112` lines (`4191` bytes)

**Classes:**
- `class TestPairScanTargetColumn`
  - Method `.test_the_last_column_is_the_target()`
  - Method `.test_scan_pairs_never_returns_the_target_column()`
  - Method `.test_pair_report_refuses_the_target_column()`
  - Method `.test_a_feature_pair_still_passes()`
  - Method `.test_ablation_restores_the_target_pairs()`
  - Method `.test_the_family_contains_only_feature_pairs()`

**Functions:**
- `def _wired(task, seed)`
- `def _planted(n, decoys, seed)` - *A non-leaky XOR pair with the target in the last column.*

---

### [`tests/test_pair_scan_target_leak.py`](tests/test_pair_scan_target_leak.py)
> *A feature that determines the target is not an interaction partner.*

**Size**: `92` lines (`3575` bytes)

**Classes:**
- `class TestPairScanTargetLeak`
  - Method `.test_the_leak_column_is_not_pairwise_dependent_on_noise()`
  - Method `.test_the_leak_column_determines_the_target()`
  - Method `.test_the_leak_pair_is_returned_without_the_guard()`
  - Method `.test_the_leak_pair_is_refused_by_the_guard()`
  - Method `.test_the_guarded_scan_returns_no_interaction()`
  - Method `.test_a_non_leaky_planted_pair_still_survives()`
  - Method `.test_the_family_is_empty_on_the_leaky_fixture()`

**Functions:**
- `def _leak_fixture(n, seed, levels)` - *A leak column that determines the target, plus independent noise.*
- `def _planted(n, decoys, seed)` - *The non-leaky XOR pair that the family-wise scan keeps.*

---

### [`tests/test_persistent_hidden_forage.py`](tests/test_persistent_hidden_forage.py)
> *Persistent-hidden forage: episode recall goes stale after collects.*

**Size**: `63` lines (`2273` bytes)

**Classes:**
- `class HiddenT1`
  - Method `.__init__(task_id, seed)`
  - Method `._state()`
- `class TestPersistentHiddenForage`
  - Method `.test_hidden_forage_recovered()`
  - Method `.test_hub_lesion_kills_hidden_forage()`
  - Method `.test_standing_forage_untouched()`

**Functions:**
- `def _hidden_t1_steps(seed, max_steps, planner)`

---

### [`tests/test_phi_clip.py`](tests/test_phi_clip.py)
> *A non-negativity assertion must test the clip, not restate it.*

**Size**: `79` lines (`3056` bytes)

**Classes:**
- `class TestPhiClipIsWhatIsPinned`
  - Method `.test_the_clip_floor_is_exactly_zero()`
  - Method `.test_the_clip_ceiling_is_reached_by_an_unmodellable_partition()`
  - Method `.test_a_partially_predictable_trace_sits_between_the_ends()`
  - Method `.test_the_floor_and_the_signal_are_distinguishable()`
  - Method `.test_no_shape_returns_a_negative()`

**Functions:**
- `def _sin_cos(rows)`
- `def _ar1(rows, seed)`

---

### [`tests/test_phi_diagnosis.py`](tests/test_phi_diagnosis.py)
> *The phi == 0.0 pin must carry its own scope, like the synergy one.*

**Size**: `85` lines (`3413` bytes)

**Classes:**
- `class TestPhiDiagnosis`
  - Method `.test_a_real_trace_reports_zero_and_names_why()`
  - Method `.test_a_constant_trace_is_named()`
  - Method `.test_a_varying_trace_is_not_reported_constant()`
  - Method `.test_the_estimator_can_move()`
  - Method `.test_the_diagnosis_reads_every_column()`
  - Method `.test_empty_input_degrades()`
  - Method `.test_short_input_below_three_rows_is_not_predictable_by_phi()`

**Functions:**
- `def _real_rows(task, seed)`

---

### [`tests/test_planner.py`](tests/test_planner.py)
> *Unit tests for planner.plan.Planner.*

**Size**: `55` lines (`1627` bytes)

**Classes:**
- `class TestPlanner`
  - Method `.test_add_and_next()`
  - Method `.test_mark_ok_advances()`
  - Method `.test_mark_fail_and_recover_skips()`
  - Method `.test_recover_none_when_drained()`
  - Method `.test_state_shape()`

---

### [`tests/test_plugin_seam.py`](tests/test_plugin_seam.py)
> *Two mock LLM providers to prove the seam, without a network or a model.*

**Size**: `106` lines (`3893` bytes)

**Classes:**
- `class EchoProvider` - *Conforming mock: deterministic, identity declared, legal token.*
  - Method `.identity()`
  - Method `.generate(observation)`
- `class AlternatingProvider` - *Non-deterministic control: same input, different output.*
  - Method `.__init__()`
  - Method `.identity()`
  - Method `.generate(observation)`
- `class TestPlugInSeam`
  - Method `.test_a_new_provider_is_pluggable_without_touching_the_agent()`
  - Method `.test_a_registered_provider_drives_the_planner()`
  - Method `.test_the_header_pin_comes_from_the_provider()`
  - Method `.test_the_pin_survives_a_class_rename()`
  - Method `.test_the_no_backend_label_is_unchanged()`
  - Method `.test_the_stub_keeps_its_class_name_label()`
  - Method `.test_the_conforming_mock_passes()`
  - Method `.test_the_non_deterministic_control_fails()`
  - Method `.test_every_registered_provider_is_named()`
  - Method `.test_an_unknown_name_does_not_silently_default()`
  - Method `.test_the_report_renders_as_one_line()`

---

### [`tests/test_policy_accuracy.py`](tests/test_policy_accuracy.py)
> *Policy accuracy: declared config matches the shipped planner.*

**Size**: `27` lines (`816` bytes)

**Classes:**
- `class TestPolicyAccuracy`
  - Method `.test_no_dead_depth_knob()`
  - Method `.test_declares_leaf_viability()`
  - Method `.test_digest_differs_from_legacy_depth4()`

---

### [`tests/test_policy_binding.py`](tests/test_policy_binding.py)
> *Policy binding: run headers cite the producing configuration.*

**Size**: `68` lines (`2724` bytes)

**Classes:**
- `class TestPolicyBinding`
  - Method `.test_header_cites_policy_and_model()`
  - Method `.test_digest_stable_and_config_sensitive()`
  - Method `.test_stub_backend_label()`
  - Method `.test_edited_policy_fails_verify()`

**Functions:**
- `def _logged_header(task, seed, backend)`

---

### [`tests/test_pool_corridor_policy.py`](tests/test_pool_corridor_policy.py)
> *Pool-corridor gate accuracy: declared config matches shipped pooling.*

**Size**: `30` lines (`973` bytes)

**Classes:**
- `class TestPoolCorridorPolicy`
  - Method `.test_declares_pool_corridor_gate()`
  - Method `.test_digest_differs_from_pre_gate_legacy()`
  - Method `.test_gate_value_sensitive()`

---

### [`tests/test_pool_policy.py`](tests/test_pool_policy.py)
> *Detour-pooling policy accuracy: declared config matches shipped planner.*

**Size**: `29` lines (`949` bytes)

**Classes:**
- `class TestPoolPolicy`
  - Method `.test_declares_detour_pooling()`
  - Method `.test_digest_differs_from_pre_pool_legacy()`
  - Method `.test_pooling_value_sensitive()`

---

### [`tests/test_pre_outcome_calibration.py`](tests/test_pre_outcome_calibration.py)
> *A pre-outcome prediction must not be flagged as circular.*

**Size**: `77` lines (`3225` bytes)

**Classes:**
- `class TestPreOutcomeCalibration`
  - Method `.test_a_post_hoc_confidence_still_warns()`
  - Method `.test_a_pre_outcome_prediction_does_not_warn()`
  - Method `.test_a_pre_outcome_prediction_reports_positive_skill()`
  - Method `.test_reset_clears_the_pre_outcome_flag()`
  - Method `.test_the_agent_run_reaches_real_skill()`
  - Method `.test_the_recorded_values_are_the_predictor_outputs()`

---

### [`tests/test_pre_outcome_prediction.py`](tests/test_pre_outcome_prediction.py)
> *A self-prediction must be made before the outcome and score above chance.*

**Size**: `120` lines (`4783` bytes)

**Classes:**
- `class TestPreOutcomePrediction`
  - Method `.test_the_predictor_beats_the_base_rate_on_every_task()`
  - Method `.test_the_selected_predictors_are_the_measured_ones()`
  - Method `.test_the_prediction_names_its_basis()`
  - Method `.test_an_unknown_task_degrades_to_a_coin_flip()`
  - Method `.test_a_goal_less_state_does_not_raise()`
  - Method `.test_the_predictor_never_sees_post_action_state()`
  - Method `.test_a_non_generalizing_predictor_fails_the_same_bar()`

**Functions:**
- `def _brier(pairs)`
- `def _episode(task, seed)` - *Replay one episode, recording the pre-action prediction each step.*

---

### [`tests/test_progress_guard_checks.py`](tests/test_progress_guard_checks.py)
> *The progress-guard battery must check its own documented claims.*

**Size**: `105` lines (`4564` bytes)

**Classes:**
- `class TestProgressGuardChecks`
  - Method `.setUpClass()`
  - Method `.test_a_real_run_has_no_findings()`
  - Method `.test_every_documented_number_is_pinned()`
  - Method `.test_call_counts_are_pinned()`
  - Method `.test_rewards_are_identical_across_modes()`
  - Method `.test_a_changed_step_count_is_named()`
  - Method `.test_a_changed_call_count_is_named()`
  - Method `.test_a_lost_reward_is_named()`
  - Method `.test_a_vanished_guard_is_named()`
  - Method `.test_missing_case_is_named()`

**Functions:**
- `def _case(report, mode, task, seed)`

---

### [`tests/test_prompt_budget.py`](tests/test_prompt_budget.py)
> *Prompt budgeting: estimate_tokens/pack in the model seam.*

**Size**: `109` lines (`4207` bytes)

**Classes:**
- `class _FakeResponse`
  - Method `.__init__(body)`
  - Method `.__enter__()`
  - Method `.__exit__(exc_type, exc, tb)`
  - Method `.read()`
- `class TestPromptBudget`
  - Method `.test_uncapped_prompt_exact()`
  - Method `.test_estimate_tokens_is_ceil_chars_over_four()`
  - Method `.test_pack_keeps_first_line_and_counts_omitted()`
  - Method `.test_budget_caps_trailing_visits()`
  - Method `.test_small_budget_keeps_target_and_obstacles()`
  - Method `.test_default_budget_is_uncapped()`
  - Method `.test_llamacpp_backend_applies_prompt_budget()`
  - Method `.test_invalid_prompt_budget_rejected()`

---

### [`tests/test_prompt_budget_checks.py`](tests/test_prompt_budget_checks.py)
> *The prompt-budget battery must check that the cap changes no behavior.*

**Size**: `93` lines (`3691` bytes)

**Classes:**
- `class TestPromptBudgetChecks`
  - Method `.setUpClass()`
  - Method `.test_a_real_run_has_no_findings()`
  - Method `.test_actions_match_the_rule_in_every_mode()`
  - Method `.test_steps_and_reward_are_identical_across_modes()`
  - Method `.test_the_cap_actually_trimmed()`
  - Method `.test_a_changed_action_is_named()`
  - Method `.test_a_changed_step_count_is_named()`
  - Method `.test_a_cap_that_trims_nothing_is_named()`
  - Method `.test_a_missing_mode_is_named()`
  - Method `.test_lost_reward_is_named()`

**Functions:**
- `def _mode(report, name)`

---

### [`tests/test_prompt_budget_honesty.py`](tests/test_prompt_budget_honesty.py)
> *A prompt budget must be reportable as honoured or exceeded.*

**Size**: `80` lines (`3188` bytes)

**Classes:**
- `class TestPromptBudgetHonesty`
  - Method `.test_uncapped_reports_no_budget_constraint()`
  - Method `.test_a_generous_budget_is_within()`
  - Method `.test_a_budget_that_drops_a_line_is_within()`
  - Method `.test_a_budget_below_the_anchor_is_reported_as_exceeded()`
  - Method `.test_the_breach_is_attributable_to_the_kept_anchor()`
  - Method `.test_pack_still_returns_the_same_triple()`
  - Method `.test_the_rendered_prompt_is_unchanged()`

---

### [`tests/test_random_floor.py`](tests/test_random_floor.py)
> *Random-policy floor: rule must beat chance by a margin.*

**Size**: `90` lines (`3308` bytes)

**Classes:**
- `class RandomBackend` - *Uniform choice among legal actions, seeded for determinism.*
  - Method `.__init__(seed)`
  - Method `.generate(observation)`
- `class TestRandomFloor`
  - Method `.test_rule_beats_best_of_three_randoms()`
  - Method `.test_random_backend_deterministic()`

**Functions:**
- `def _run(task, seed, backend)`

---

### [`tests/test_range_pins_0_199.py`](tests/test_range_pins_0_199.py)
> *Backfill range pins 0-199: ledger-verified totals without test pins.*

**Size**: `35` lines (`1157` bytes)

**Classes:**
- `class TestRangePins0199`
  - Method `.test_range_totals_0_199()`

**Functions:**
- `def _total(task, seeds)`

---

### [`tests/test_recall_cost.py`](tests/test_recall_cost.py)
> *Recall cost: the loop must not deep-copy history it does not read.*

**Size**: `99` lines (`3674` bytes)

**Classes:**
- `class _CountingList` - *A list that records how often it is deep-copied.*
  - Method `.__init__(items)`
  - Method `.__deepcopy__(memo)`
- `class TestRecallCost`
  - Method `._state(i)`
  - Method `.test_recall_does_not_deepcopy_the_history()`
  - Method `.test_per_step_recall_is_much_cheaper_than_a_full_deepcopy()`
  - Method `.test_agent_actions_unchanged_by_the_cost_fix()`
  - Method `.test_planner_never_mutates_the_recall_it_receives()`

---

### [`tests/test_recall_depth.py`](tests/test_recall_depth.py)
> *Recall depth: full-history recall for persistent hidden goals.*

**Size**: `63` lines (`2133` bytes)

**Classes:**
- `class HiddenWorld` - *GridWorld that omits the target after the initial state.*
  - Method `.__init__(task_id, seed)`
  - Method `._state()`
- `class TestRecallDepth`
  - Method `.test_persistent_hidden_target_recovered()`
  - Method `.test_window_ablation_kills_persistent_recovery()`

**Functions:**
- `def _persistent_hidden_steps(task, seed, window, max_steps)`

---

### [`tests/test_recall_fallback.py`](tests/test_recall_fallback.py)
> *A malformed FTS query must not make the fallback find nothing.*

**Size**: `90` lines (`3296` bytes)

**Classes:**
- `class TestRecallFallback`
  - Method `._store_with_rows(tmp)`
  - Method `.test_recall_terms_strips_fts_operators()`
  - Method `.test_a_malformed_query_still_finds_the_rows()`
  - Method `.test_a_well_formed_query_is_unchanged()`
  - Method `.test_a_query_with_no_terms_returns_nothing()`
  - Method `.test_the_fallback_preserves_limit_and_ordering()`
  - Method `.test_no_match_is_still_no_match()`

---

### [`tests/test_recall_terms_unicode.py`](tests/test_recall_terms_unicode.py)
> *Search terms must keep non-ASCII words whole.*

**Size**: `79` lines (`3247` bytes)

**Classes:**
- `class TestRecallTermsUnicode`
  - Method `.test_an_accented_word_stays_one_term()`
  - Method `.test_a_word_of_only_non_ascii_characters_is_a_term()`
  - Method `.test_operators_between_non_ascii_words_are_dropped()`
  - Method `.test_ascii_behaviour_is_unchanged()`
  - Method `.test_a_non_ascii_query_finds_its_row_through_the_fallback()`
  - Method `.test_a_wholly_non_ascii_query_finds_its_row()`
  - Method `.test_a_missing_non_ascii_word_is_still_a_miss()`

---

### [`tests/test_recompute.py`](tests/test_recompute.py)
> *Recompute check: log written via telemetry recomputes to direct estimates.*

**Size**: `60` lines (`2486` bytes)

**Classes:**
- `class TestRecompute`
  - Method `.test_recompute_matches_direct()`
  - Method `.test_self_report_scalars_ignored()`

**Functions:**
- `def _xor_trace(seed, n)`

---

### [`tests/test_replication.py`](tests/test_replication.py)
> *A scan candidate must replicate on held-out episodes.*

**Size**: `147` lines (`6801` bytes)

**Classes:**
- `class TestHoldoutReplication`
  - Method `.test_a_train_only_signal_candidate_fails_holdout()`
  - Method `.test_the_ablation_returns_the_train_candidates()`
  - Method `.test_a_planted_cross_module_pair_replicates()`
  - Method `.test_no_candidate_degrades_to_empty()`
  - Method `.test_a_100_trial_candidate_is_unstable_at_200()`
  - Method `.test_the_stability_ablation_returns_the_candidate()`
  - Method `.test_the_holdout_result_is_deterministic()`

**Functions:**
- `def _signal_rows(seeds)`
- `def _planted(seed, n)` - *A non-leaky XOR between column 0 (M) and column 2 (P).*

---

### [`tests/test_repro.py`](tests/test_repro.py)
> *Repro mode: triple-run determinism gate for the standing pins.*

**Size**: `50` lines (`1570` bytes)

**Classes:**
- `class TestRepro`
  - Method `.test_pin_seeds_triple_run_identical()`

**Functions:**
- `def _fingerprint(trace)`

---

### [`tests/test_result_records.py`](tests/test_result_records.py)
> *Result records are self-reports and must be checked against the step.*

**Size**: `163` lines (`7801` bytes)

**Classes:**
- `class TestResultRecords`
  - Method `.test_honest_log_pairs_cleanly()`
  - Method `.test_altered_output_is_named()`
  - Method `.test_altered_cost_is_named()`
  - Method `.test_failed_ok_is_named()`
  - Method `.test_unpaired_result_is_named()`
  - Method `.test_no_result_records_is_named()`

**Functions:**
- `def _write_log(directory, name, task, seed)`
- `def _rewrite_results(log_path, out_path, ok, output, cost)`

---

### [`tests/test_resume_identity_checks.py`](tests/test_resume_identity_checks.py)
> *The resume-identity battery must enforce its own identity claims.*

**Size**: `104` lines (`4187` bytes)

**Classes:**
- `class TestResumeIdentityChecks`
  - Method `.setUpClass()`
  - Method `.test_a_real_run_has_no_findings()`
  - Method `.test_every_mode_produces_its_documented_decision()`
  - Method `.test_volatile_keys_do_not_change_the_digest()`
  - Method `.test_a_changed_seed_changes_the_digest()`
  - Method `.test_a_changed_target_changes_the_digest()`
  - Method `.test_header_matches_the_digest_and_reruns_agree()`
  - Method `.test_a_changed_seed_that_resumes_is_named()`
  - Method `.test_a_volatile_key_that_moves_the_digest_is_named()`
  - Method `.test_a_header_that_disagrees_is_named()`
  - Method `.test_a_missing_mode_is_named()`

**Functions:**
- `def _case(report, mode)`

---

### [`tests/test_rule_confidence.py`](tests/test_rule_confidence.py)
> *Rule-path confidence readout: BFS move ties in the planner probe.*

**Size**: `260` lines (`10880` bytes)

**Classes:**
- `class TestRuleConfidence`
  - Method `.test_unique_move_has_full_confidence()`
  - Method `.test_two_way_tie_has_half_confidence()`
  - Method `.test_tie_alternatives_are_listed()`
  - Method `.test_alternatives_carry_visit_counts()`
  - Method `.test_unique_move_has_one_alternative()`
  - Method `.test_collect_has_empty_alternatives()`
  - Method `.test_alternatives_are_json_safe()`
  - Method `.test_collect_at_goal_has_full_confidence()`
  - Method `.test_item_tour_uses_the_rule_goal()`
  - Method `.test_tour_audit_single_item()`
  - Method `.test_tour_audit_two_way_tie()`
  - Method `.test_tour_audit_no_tie()`
  - Method `.test_tour_audit_three_items()`
  - Method `.test_tour_audit_only_for_item_moves()`
  - Method `.test_tour_audit_off_with_readout()`
  - Method `.test_tour_audit_is_json_safe()`
  - Method `.test_tour_actions_unchanged_on_logged_run()`
  - Method `.test_readout_off_removes_the_field()`
  - Method `.test_actions_identical_with_and_without_readout()`
  - Method `.test_multiple_items_readout_is_deterministic()`
  - Method `.test_no_goal_has_no_readout()`
  - Method `.test_readout_is_json_safe()`
  - Method `.test_logged_run_actions_identical()`
  - Method `.test_invalid_rule_readout_rejected()`
  - Method `.test_policy_declares_rule_readout()`

**Functions:**
- `def _state(x, y, target, obstacles, task, items, steps)`
- `def _plan(planner, state)`

---

### [`tests/test_run_agent_cli.py`](tests/test_run_agent_cli.py)
> *A registry nobody can reach is not pluggable.*

**Size**: `89` lines (`3648` bytes)

**Classes:**
- `class TestRunAgentCli`
  - Method `.test_an_episode_runs_with_the_rule_policy()`
  - Method `.test_a_registered_backend_can_be_named()`
  - Method `.test_an_unknown_backend_is_misuse_and_names_the_choices()`
  - Method `.test_a_missing_task_is_misuse()`
  - Method `.test_an_unknown_task_is_misuse()`
  - Method `.test_a_stub_without_a_script_is_misuse()`
  - Method `.test_the_run_reports_the_backend_it_actually_used()`
  - Method `.test_naming_a_backend_does_not_change_a_rule_run()`

**Functions:**
- `def _run(args)`

---

### [`tests/test_selfmodel.py`](tests/test_selfmodel.py)
> *Unit tests for self_model.model.SelfModel.*

**Size**: `42` lines (`1301` bytes)

**Classes:**
- `class TestSelfModel`
  - Method `.test_initial_snapshot()`
  - Method `.test_record_ok_and_fail()`
  - Method `.test_reset()`

---

### [`tests/test_selfmodel_size.py`](tests/test_selfmodel_size.py)
> *Self-model history size must be readable without copying the history.*

**Size**: `119` lines (`4171` bytes)

**Classes:**
- `class TestSelfModelSize`
  - Method `.test_size_matches_history_length()`
  - Method `.test_size_does_not_copy_the_history()`
  - Method `.test_size_is_constant_time_relative_to_history()`
  - Method `.test_default_agent_uses_the_cheap_path()`
  - Method `.test_actions_and_rewards_unchanged()`

**Functions:**
- `def _state(i)`

---

### [`tests/test_snapshot.py`](tests/test_snapshot.py)
> *Snapshot capture and diff (lattice transfer).*

**Size**: `85` lines (`3773` bytes)

**Classes:**
- `class TestSnapshotDiff`
  - Method `.test_added_removed_changed_and_volatile()`
  - Method `.test_volatile_only_change_is_unchanged()`
  - Method `.test_same_records_empty_diff()`
  - Method `.test_export_read_roundtrip_is_atomic()`
  - Method `.test_run_record_fields()`
  - Method `.test_capture_same_battery_diffs_empty()`

**Functions:**
- `def _record(identifier, steps, created)`

---

### [`tests/test_snapshot_digest.py`](tests/test_snapshot_digest.py)
> *Content-vs-graph snapshot digests and meta verification.*

**Size**: `94` lines (`4074` bytes)

**Classes:**
- `class TestSnapshotDigest`
  - Method `.test_graph_changes_content_stable_on_volatile()`
  - Method `.test_real_change_changes_both_digests()`
  - Method `.test_digests_shape()`
  - Method `.test_meta_roundtrip_and_verify()`
  - Method `.test_changed_record_breaks_meta_verify()`
  - Method `.test_capture_graph_differs_content_matches()`

**Functions:**
- `def _record(identifier, steps, captured, syn)`

---

### [`tests/test_snapshot_evidence.py`](tests/test_snapshot_evidence.py)
> *Snapshot records must carry the integrity evidence, not just the score.*

**Size**: `88` lines (`3787` bytes)

**Classes:**
- `class TestSnapshotEvidence`
  - Method `.test_run_record_carries_the_integrity_fields()`
  - Method `.test_existing_fields_are_unchanged()`
  - Method `.test_a_changed_scope_is_visible_to_the_diff()`
  - Method `.test_a_failed_replay_is_visible_to_the_diff()`
  - Method `.test_capture_snapshot_includes_the_evidence()`
  - Method `.test_absent_stats_leave_the_evidence_null()`

**Functions:**
- `def _trace(steps, reward)`

---

### [`tests/test_state_machines.py`](tests/test_state_machines.py)
> *Explicit state-machine registry: consistency, CLI contract and live drift.*

**Size**: `110` lines (`5117` bytes)

**Classes:**
- `class TestStateMachineRegistry`
  - Method `.test_registry_is_internally_consistent()`
  - Method `.test_every_machine_renders_and_checks_every_state()`
  - Method `.test_cli_matches_the_transition_table_for_every_machine()`
  - Method `.test_list_json_and_representative_transitions()`
  - Method `.test_misuse_and_unknown_names_exit_two()`
  - Method `.test_live_vocabularies_match_declared_states()`

---

### [`tests/test_store_capability_use.py`](tests/test_store_capability_use.py)
> *The agent must declare whether its store writes are consumed.*

**Size**: `115` lines (`4784` bytes)

**Classes:**
- `class TestStoreCapabilityUse`
  - Method `.test_the_agent_writes_content_every_step()`
  - Method `.test_recall_has_no_production_caller()`
  - Method `.test_the_measured_capabilities_are_the_documented_ones()`
  - Method `.test_the_index_is_populated_and_queryable_even_though_unread()`
  - Method `.test_the_tokeniser_is_the_documented_one()`

**Functions:**
- `def _production_sources()`
- `def store_capability_use()` - *Report which MemoryStore read paths production code calls.*

---

### [`tests/test_store_recovery.py`](tests/test_store_recovery.py)
> *Store recovery: a corrupt database file is quarantined, never fatal.*

**Size**: `52` lines (`1917` bytes)

**Classes:**
- `class TestStoreRecovery`
  - Method `.test_corrupt_file_quarantined_and_store_functional()`
  - Method `.test_healthy_file_never_quarantined()`

---

### [`tests/test_store_schema.py`](tests/test_store_schema.py)
> *Layouts schema: the declared shape matches the migrated shape.*

**Size**: `65` lines (`2475` bytes)

**Classes:**
- `class TestLayoutSchema`
  - Method `.test_declared_schema_includes_fingerprint()`
  - Method `.test_fresh_store_needs_no_migration()`
  - Method `.test_legacy_store_is_migrated_and_row_survives()`

**Functions:**
- `def _layout_columns(conn)`

---

### [`tests/test_substrate_errors.py`](tests/test_substrate_errors.py)
> *Substrate error visibility: counters exist, ok reflects reward, faults counted.*

**Size**: `80` lines (`3261` bytes)

**Classes:**
- `class FaultyStore` - *Minimal memory_store double whose save always raises.*
  - Method `.bind_hub(getter)`
  - Method `.save(key, content, conf)`
  - Method `.count()`
- `class TestSubstrateErrors`
  - Method `.test_exposes_zero_counters_after_clean_run()`
  - Method `.test_persistent_ok_reflects_reward()`
  - Method `.test_faulty_store_counted_and_run_continues()`

---

### [`tests/test_synergy_cost.py`](tests/test_synergy_cost.py)
> *Synergy estimator cost: the c1 discretization is computed once.*

**Size**: `41` lines (`1436` bytes)

**Classes:**
- `class TestSynergyCost`
  - Method `.test_discretize_is_not_per_row()`
  - Method `.test_synergy_values_preserved()`

---

### [`tests/test_synergy_duplicate_mechanism.py`](tests/test_synergy_duplicate_mechanism.py)
> *Equal scope columns: state the real mechanism, not the wrong one.*

**Size**: `84` lines (`3325` bytes)

**Classes:**
- `class TestEqualColumnsMechanism`
  - Method `.test_the_joint_code_is_injective_in_the_column()`
  - Method `.test_coarse_joint_binning_inflates_the_joint()`
  - Method `.test_a_positive_gap_is_an_artifact_not_integration()`
  - Method `.test_a_small_range_gives_the_exact_minus_mi_result()`
  - Method `.test_both_regimes_exist_so_the_claim_must_be_about_independence()`

**Functions:**
- `def _fixture_15()`
- `def _fixture_4()`

---

### [`tests/test_synergy_null.py`](tests/test_synergy_null.py)
> *A ``syn`` value needs its null, or it is a number without a verdict.*

**Size**: `102` lines (`4459` bytes)

**Classes:**
- `class TestPermutationNull`
  - Method `.test_the_null_is_deterministic_for_a_seed()`
  - Method `.test_the_null_keeps_the_trace_and_permutes_the_target()`
  - Method `.test_a_negative_trace_is_reported_as_anti_synergistic()`
  - Method `.test_the_positive_trace_is_not_distinguishable()`
  - Method `.test_the_verdict_carries_the_null_it_used()`
  - Method `.test_degenerate_input_degrades_without_raising()`
  - Method `.test_a_bad_trial_count_is_rejected()`

**Functions:**
- `def _rows(task, seed)`

---

### [`tests/test_synergy_null_wiring.py`](tests/test_synergy_null_wiring.py)
> *The synergy null must reach every place ``syn`` is reported.*

**Size**: `80` lines (`3321` bytes)

**Classes:**
- `class TestSynergyNullWiring`
  - Method `.test_trace_slot_carries_the_null()`
  - Method `.test_trace_slot_defaults_to_none()`
  - Method `.test_trace_slot_keeps_every_existing_field()`
  - Method `.test_run_record_carries_the_null()`
  - Method `.test_run_record_defaults_to_none()`
  - Method `.test_the_real_run_reaches_the_slot_with_a_verdict()`

---

### [`tests/test_synergy_scope.py`](tests/test_synergy_scope.py)
> *Synergy scope: the criterion must report which trace columns it reads.*

**Size**: `98` lines (`4093` bytes)

**Classes:**
- `class TestSynergyScope`
  - Method `.test_scope_pins_the_two_columns_the_estimator_reads()`
  - Method `.test_scope_names_the_columns_it_ignores()`
  - Method `.test_appending_a_column_cannot_change_the_estimate()`
  - Method `.test_constant_leading_column_is_flagged_insufficient()`
  - Method `.test_sufficient_scope_is_reported_for_a_varying_pair()`
  - Method `.test_empty_trace_degrades_without_raising()`
  - Method `.test_recompute_reports_scope_with_the_estimate()`

**Functions:**
- `def _rows(width, n)`

---

### [`tests/test_synergy_scope_duplicate.py`](tests/test_synergy_scope_duplicate.py)
> *A duplicated scope pair cannot decide, and the scope must say so.*

**Size**: `76` lines (`3672` bytes)

**Classes:**
- `class TestDuplicateScopeColumns`
  - Method `.test_a_duplicated_pair_is_not_sufficient()`
  - Method `.test_a_small_range_duplicate_gives_the_exact_minus_mi_result()`
  - Method `.test_syn_n_of_minus_one_marks_the_exact_collapse()`
  - Method `.test_an_independent_pair_stays_sufficient()`
  - Method `.test_a_constant_column_is_still_named_first()`
  - Method `.test_a_single_column_trace_has_no_duplicate()`
  - Method `.test_empty_and_mismatched_inputs_still_degrade()`

---

### [`tests/test_synergy_sign.py`](tests/test_synergy_sign.py)
> *A negative synergy gap must be reported as such, not as a strong one.*

**Size**: `69` lines (`2931` bytes)

**Classes:**
- `class TestSynergySign`
  - Method `.test_a_positive_gap_is_reported_positive()`
  - Method `.test_a_negative_ratio_at_minus_one_is_reported_negative()`
  - Method `.test_a_small_negative_is_still_negative()`
  - Method `.test_zero_is_reported_zero()`
  - Method `.test_the_classification_uses_the_gap_not_the_ratio()`
  - Method `.test_the_estimator_keeps_its_values()`

---

### [`tests/test_synergy_sign_wiring.py`](tests/test_synergy_sign_wiring.py)
> *The synergy sign must reach every place ``syn`` is reported.*

**Size**: `72` lines (`2770` bytes)

**Classes:**
- `class TestSynergySignWiring`
  - Method `.test_trace_slot_carries_the_sign()`
  - Method `.test_trace_slot_defaults_to_none()`
  - Method `.test_trace_slot_keeps_every_existing_field()`
  - Method `.test_run_record_carries_the_sign()`
  - Method `.test_run_record_defaults_to_none()`
  - Method `.test_the_real_negative_case_reaches_the_slot()`

---

### [`tests/test_telemetry.py`](tests/test_telemetry.py)
> *Telemetry roundtrip checks.*

**Size**: `150` lines (`6580` bytes)

**Classes:**
- `class TestTelemetry`
  - Method `.test_read_headers_matches_filtered_read_all()`
  - Method `.test_read_headers_missing_file_is_empty()`
  - Method `.test_read_headers_raises_on_malformed_line()`
  - Method `.test_append_read_roundtrip()`
  - Method `.test_fsync_file_exists_and_valid()`
  - Method `.test_verdict_and_bins()`
  - Method `.test_head_digest_tail_read_equivalence()`
  - Method `.test_head_digest_reads_tail_not_whole_file()`

---

### [`tests/test_telemetry_concurrency.py`](tests/test_telemetry_concurrency.py)
> *Concurrent telemetry writers must preserve the hash chain.*

**Size**: `95` lines (`3681` bytes)

**Classes:**
- `class TestTelemetryConcurrency`
  - Method `.test_two_writers_keep_one_valid_chain()`
  - Method `.test_single_writer_chain_still_valid()`
  - Method `.test_lock_timeout_surfaces_instead_of_interleaving()`
  - Method `.test_stale_lock_is_broken()`

---

### [`tests/test_telemetry_mac.py`](tests/test_telemetry_mac.py)
> *Optional HMAC-signed telemetry: keyed records and tamper findings.*

**Size**: `109` lines (`4472` bytes)

**Classes:**
- `class TestTelemetryMac`
  - Method `.test_keyed_records_verify_with_key()`
  - Method `.test_wrong_key_reports_bad_mac()`
  - Method `.test_missing_mac_reported()`
  - Method `.test_tampered_payload_with_recomputed_digest_reports_bad_mac()`
  - Method `.test_unkeyed_log_with_key_reports_missing_mac()`
  - Method `.test_invalid_hmac_key_rejected()`

**Functions:**
- `def _build(path, key)`

---

### [`tests/test_three_blocker.py`](tests/test_three_blocker.py)
> *Three-blocker snapshot matrix: pin the audited two-detour family.*

**Size**: `83` lines (`3501` bytes)

**Classes:**
- `class _ForcedThreeWorld`
  - Method `.__init__(target, obstacles)`
  - Method `._build_layout(rng)`
- `class BlindPlanner`
  - Method `.plan(state, memories)`
- `class TestThreeBlocker`
  - Method `.test_three_blocker_pins()`
  - Method `.test_blind_kills_three_blocker()`

**Functions:**
- `def _three_steps(target, obstacles, planner, max_steps)`

---

### [`tests/test_three_goldens.py`](tests/test_three_goldens.py)
> *Three-blocker golden paths: exact action sequences for the family.*

**Size**: `48` lines (`2142` bytes)

**Classes:**
- `class TestThreeGoldens`
  - Method `.test_three_paths_match_golden_hashes()`

**Functions:**
- `def _fingerprint(trace)`

---

### [`tests/test_tour_order.py`](tests/test_tour_order.py)
> *Forage tour ordering: optimal 3-item tour beats nearest-greedy traps.*

**Size**: `31` lines (`904` bytes)

**Classes:**
- `class TestTourOrder`
  - Method `.test_greedy_trap_seeds_optimal()`
  - Method `.test_t1_100_seed_total()`

**Functions:**
- `def _steps(task, seed, max_steps)`

---

### [`tests/test_trace_slot_scope.py`](tests/test_trace_slot_scope.py)
> *Every battery's trace slot must carry the synergy scope.*

**Size**: `70` lines (`2842` bytes)

**Classes:**
- `class TestTraceSlotScope`
  - Method `.test_slot_carries_the_scope()`
  - Method `.test_slot_keeps_every_existing_field()`
  - Method `.test_missing_scope_is_none_not_absent()`
  - Method `.test_a_scope_insufficiency_survives_the_slot()`
  - Method `.test_the_coldstart_battery_reports_the_scope()`

---

### [`tests/test_trap_escape.py`](tests/test_trap_escape.py)
> *Obstacle-trap escape: planner avoids dead-end entries, pinned step totals.*

**Size**: `67` lines (`2464` bytes)

**Classes:**
- `class BlindPlanner` - *Integration cut: same rules, memory input severed.*
  - Method `.plan(state, memories)`
- `class TestTrapEscape`
  - Method `.test_seed15_takes_optimal_13()`
  - Method `.test_seed65_takes_optimal_6()`
  - Method `.test_ablation_blind_memory_truncates_trap()`
  - Method `.test_pinned_step_totals_no_regression()`

**Functions:**
- `def _steps(task, seed, max_steps)`

---

### [`tests/test_vector_audit.py`](tests/test_vector_audit.py)
> *Vector independence: the M/P/S/hub blocks are not independent readouts.*

**Size**: `175` lines (`6829` bytes)

**Classes:**
- `class TestVectorAudit`
  - Method `.test_block_labels_match_the_agent_layout()`
  - Method `.test_column_report_names_constants()`
  - Method `.test_duplicate_pairs_are_named()`
  - Method `.test_distinct_nonconstant_columns_collapse_to_zero()`
  - Method `.test_independent_blocks_report_no_degeneracy()`
  - Method `.test_identical_column_content_is_detected_not_assumed()`
  - Method `.test_empty_rows_degrade_without_raising()`
- `class TestLiveVectorDegeneracy` - *Pin the real substrate's vector structure, measured not assumed.*
  - Method `._rows(agent, task, seed)`
  - Method `.test_default_agent_store_path_has_three_constant_columns()`
  - Method `.test_full_wiring_collapses_four_counters_onto_one()`

**Functions:**
- `def _rows(vectors)` - *Expand (M, P, S, hub) tuples into flat 9-column rows.*

---

### [`tests/test_vector_audit_adapter.py`](tests/test_vector_audit_adapter.py)
> *The vector-audit adapter must agree with the row-level audit.*

**Size**: `103` lines (`4104` bytes)

**Classes:**
- `class TestAuditVectors`
  - Method `.test_adapter_equals_the_row_audit()`
  - Method `.test_adapter_flattens_in_block_order()`
  - Method `.test_block_order_is_observable()`
  - Method `.test_a_degenerate_matrix_is_reported_through_the_adapter()`
  - Method `.test_an_independent_matrix_is_sufficient_through_the_adapter()`
  - Method `.test_empty_degrades_without_raising()`
  - Method `.test_tuples_and_lists_flatten_identically()`

**Functions:**
- `def _flat(vectors)`

---

### [`tests/test_verdict.py`](tests/test_verdict.py)
> *Verdict facts: a step-cap run is truncated, not a success.*

**Size**: `67` lines (`2554` bytes)

**Classes:**
- `class WaitingBackend`
  - Method `.generate(observation)`
- `class TestVerdictFacts`
  - Method `.test_success_before_cap_is_done()`
  - Method `.test_cap_is_truncated_not_done()`
  - Method `.test_legacy_predicate_ablation_labels_cap_done()`

**Functions:**
- `def _run_logged(trust_window, noop_guard, waiting, task, seed)`

---

### [`tests/test_verdict_claim.py`](tests/test_verdict_claim.py)
> *Verdict claims must be checked against the replayed trajectory.*

**Size**: `148` lines (`7047` bytes)

**Classes:**
- `class TestVerdictClaim`
  - Method `.test_parse_verdict_reason_reads_the_machine_claim()`
  - Method `.test_parse_rejects_a_reason_without_the_fields()`
  - Method `.test_honest_log_passes_verdict_check()`
  - Method `.test_inflated_reward_claim_is_rejected()`
  - Method `.test_step_count_claim_is_checked_separately()`
  - Method `.test_verdict_check_is_opt_in()`
  - Method `.test_missing_verdict_is_named_when_requested()`

**Functions:**
- `def _write_log(directory, name, task, seed)`
- `def _rewrite_verdict(log_path, out_path, verdict, reason)` - *Re-emit a log through Telemetry with a replaced verdict record.*

---

### [`tests/test_verdict_word.py`](tests/test_verdict_word.py)
> *The verdict word must agree with the trajectory and the budget.*

**Size**: `123` lines (`5764` bytes)

**Classes:**
- `class TestVerdictWord`
  - Method `.test_pre_cap_completion_is_done_and_clean()`
  - Method `.test_budget_exhaustion_is_truncated_and_clean()`
  - Method `.test_truncated_run_relabelled_done_is_named()`
  - Method `.test_done_relabelled_truncated_is_named()`
  - Method `.test_unknown_verdict_word_is_named()`

**Functions:**
- `def _write_log(directory, name, task, seed, max_steps)`
- `def _rewrite_verdict(log_path, out_path, verdict, reason)`

---

### [`tests/test_verify_run.py`](tests/test_verify_run.py)
> *One aggregate verifier must compose every shipped check.*

**Size**: `142` lines (`6253` bytes)

**Classes:**
- `class TestVerifyRun`
  - Method `.test_honest_log_passes_every_layer()`
  - Method `.test_a_forged_action_is_rejected_by_the_aggregate()`
  - Method `.test_a_rewritten_result_is_rejected_by_the_results_layer()`
  - Method `.test_a_wrong_model_pin_is_rejected_by_the_episode_layer()`
  - Method `.test_a_raising_layer_does_not_hide_the_others()`
  - Method `.test_a_missing_log_is_reported_not_raised()`

**Functions:**
- `def _write_log(directory, name, task, seed)`
- `def _rewrite(log_path, out_path, transform)` - *Re-emit a log through Telemetry, letting ``transform`` edit records.*

---

### [`tests/test_verify_run_cli.py`](tests/test_verify_run_cli.py)
> *The aggregate verifier needs a command line, not just a function.*

**Size**: `93` lines (`3511` bytes)

**Classes:**
- `class TestVerifyRunCli`
  - Method `.test_a_clean_log_exits_zero()`
  - Method `.test_a_failing_log_exits_one_and_names_the_layer()`
  - Method `.test_a_missing_log_is_misuse()`
  - Method `.test_no_arguments_is_misuse()`
  - Method `.test_the_json_flag_prints_the_full_report()`
  - Method `.test_format_report_names_each_layer()`

**Functions:**
- `def _write_log(directory, name, task, seed)`
- `def _run(args)`

---

### [`tests/test_wiring.py`](tests/test_wiring.py)
> *Wiring check: real substrate roundtrip through JSONL log to recompute.*

**Size**: `135` lines (`6682` bytes)

**Classes:**
- `class TestWiring`
  - Method `._run_logged(tmp, task, seed, max_steps)`
  - Method `.test_roundtrip_recompute_parity()`
  - Method `.test_hub_zero_null_and_lesion_isolates()`

**Functions:**
- `def _pad(rows)`

---

### [`tests/test_wiring_independence.py`](tests/test_wiring_independence.py)
> *Wiring the modules makes them independent, and then anti-synchronous.*

**Size**: `132` lines (`5826` bytes)

**Classes:**
- `class TestWiringIndependence`
  - Method `.test_the_defaults_leave_columns_constant()`
  - Method `.test_wiring_makes_every_column_vary()`
  - Method `.test_wiring_does_not_reduce_dependence()`
  - Method `.test_wiring_produces_independent_pairs()`
  - Method `.test_every_independent_pair_is_refused_as_a_target_leak()`
  - Method `.test_every_independent_pair_has_no_single_pair_null()`
  - Method `.test_no_interaction_under_either_configuration()`
  - Method `.test_anti_interactions_are_empty_at_correct_n()`

**Functions:**
- `def _vectors(full_wiring)`

---

### [`tests/test_workspace.py`](tests/test_workspace.py)
> *Workspace source hash and run-header binding (harness transfer).*

**Size**: `107` lines (`4274` bytes)

**Classes:**
- `class TestWorkspaceHash`
  - Method `.test_file_map_excludes_noise()`
  - Method `.test_digest_stable_and_sensitive()`
  - Method `.test_missing_root_rejected()`
  - Method `.test_logged_header_binds_workspace()`
  - Method `.test_header_workspace_is_optional()`

**Functions:**
- `def _workspace(root)`

---

### [`tests/test_worlds.py`](tests/test_worlds.py)
> *World determinism and viability checks.*

**Size**: `87` lines (`3041` bytes)

**Classes:**
- `class TestDeterminism`
  - Method `.test_same_seed_same_hash()`
  - Method `.test_reset_reproducible()`
  - Method `.test_seed_sensitivity()`
  - Method `.test_base_state_keys_and_actions()`
  - Method `.test_viability_bounds()`
  - Method `.test_tempdir_hash_log()`

---

### [`workspace.py`](workspace.py)
> *Deterministic workspace source hash for run/evidence binding.*

**Size**: `58` lines (`1990` bytes)

**Functions:**
- `def workspace_files(root)` - *Return ``{relative_path: sha256}`` for the workspace source tree.*
- `def workspace_digest(root)` - *Return one SHA-256 over the sorted relative-path/file-digest map.*

---

### [`worlds/__init__.py`](worlds/__init__.py)
> *Brain grid worlds package: deterministic fixed-step 8x8 tasks.*

**Size**: `5` lines (`275` bytes)

---

### [`worlds/grid.py`](worlds/grid.py)
> *Deterministic 8x8 grid worlds with fixed-step updates.*

**Size**: `224` lines (`7687` bytes)

**Classes:**
- `class GridWorld` - *Deterministic grid world for one task id and seed.*
  - Method `.__init__(task_id, seed)`
  - Method `._all_cells()`
  - Method `._build_layout(rng)`
  - Method `._state()`
  - Method `.layout_fingerprint()` - *Return a deterministic SHA-256 over this world's task geometry.*
  - Method `.is_viable()` - *Return True while energy > 0 and steps < 200.*
  - Method `.reset()` - *Rebuild layout from seed and return the initial state dict.*
  - Method `._blocked(nx, ny)`
  - Method `.step(action)` - *Apply one fixed-step action.*

**Functions:**
- `def stable_hash(state)` - *Return sha256 hex digest of JSON state with sorted keys.*
- `def viability(state)` - *Vc viability predicate: energy > 0 and steps < 200.*
- `def _manhattan(a, b)`

---
