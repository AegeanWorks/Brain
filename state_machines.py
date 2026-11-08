#!/usr/bin/env python3
"""Explicit state-machine registry for Brain (PRINCIPLE-009, PRINCIPLE-016).

Brain encodes many lifecycles in JSON fields, string verdicts and file
presence. This module makes them readable in one place: states, allowed
transitions, the code that persists them, and the gap a reader should
know. It is data-only: importing it changes nothing, and every CLI mode
is read-only.

The CLI follows the universal contract: ``--help`` exits 0 and writes
nothing, exit 0 means success, 1 a refused transition, unknown status or
live drift, and 2 misuse.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from dataclasses import dataclass
from typing import Dict, Mapping, Optional, Sequence, Tuple


@dataclass(frozen=True)
class Machine:
    """One lifecycle as data: states, intended transitions, and its source."""

    name: str
    purpose: str
    states: Tuple[str, ...]
    transitions: Mapping[str, Tuple[str, ...]]
    source: str
    gap: str = ""

    def allows(self, source: str, target: str) -> bool:
        """Return True when ``source -> target`` is a declared transition."""
        return target in self.transitions.get(source, ())


MACHINES: Tuple[Machine, ...] = (
    Machine(
        name="episode-verdict",
        purpose="How one agent episode ends: no terminal record yet, done, or truncated.",
        states=("running", "done", "truncated"),
        transitions={"running": ("done", "truncated"), "done": (), "truncated": ()},
        source="agent.py: _episode_verdict, run_task_logged; "
               "telemetry/log.py: write_verdict",
        gap="The world sets done at the step cap too; only the verdict separates "
            "completion from truncation, and a trace cut before write_verdict leaves a "
            "header with no terminal state.",
    ),
    Machine(
        name="world-step",
        purpose="Why the grid world stopped: task complete or a hard budget.",
        states=("active", "task-complete", "energy-exhausted", "step-exhausted"),
        transitions={
            "active": ("task-complete", "energy-exhausted", "step-exhausted"),
            "task-complete": (),
            "energy-exhausted": (),
            "step-exhausted": (),
        },
        source="worlds/grid.py: step",
        gap="`done` conflates task completion with energy/step exhaustion and carries no "
            "reason, so a reader must infer the cause from reward and steps.",
    ),
    Machine(
        name="model-decision",
        purpose="The planner's verdict on one backend proposal for one step.",
        states=("pending", "accepted", "invalid", "no-op", "no-progress",
                "stall", "distrusted", "skipped", "skipped-progress"),
        transitions={
            "pending": ("accepted", "invalid", "no-op", "no-progress",
                        "stall", "distrusted", "skipped", "skipped-progress"),
            "accepted": (),
            "invalid": (),
            "no-op": (),
            "no-progress": (),
            "stall": (),
            "distrusted": (),
            "skipped": (),
            "skipped-progress": (),
        },
        source="agent.py: Planner.plan model_decision block; "
               "probe.model_decision reason field",
        gap="Reason strings are inline literals in an ordered conditional ladder; the "
            "order decides which label wins and no constant declares the vocabulary.",
    ),
    Machine(
        name="backend-trust",
        purpose="How much a per-episode planner trusts backend proposals.",
        states=("trusted", "stalled", "distrusted"),
        transitions={
            "trusted": ("trusted", "stalled"),
            "stalled": ("trusted", "stalled", "distrusted"),
            "distrusted": ("distrusted",),
        },
        source="agent.py: Planner._backend_distrusted, trust_window, reset_trust",
        gap="Distrust is episode-scoped and monotonic; a later reward does not restore "
            "trust and only reset_trust (a new episode) returns to trusted.",
    ),
    Machine(
        name="progress-guard",
        purpose="The consecutive wrong-way rejection streak and its distrust.",
        states=("watching", "streak", "distrusted"),
        transitions={
            "watching": ("watching", "streak"),
            "streak": ("watching", "streak", "distrusted"),
            "distrusted": ("distrusted",),
        },
        source="agent.py: Planner._progress_streak, _progress_distrusted, "
               "progress_skip_after, reset_trust",
        gap="Any non-progress outcome resets the streak, so an alternating backend never "
            "accumulates distrust; distrust is episode-scoped.",
    ),
    Machine(
        name="layout-store",
        purpose="Opening the persistent store and recovering a corrupt file.",
        states=("opening", "valid", "corrupt", "quarantined", "fresh"),
        transitions={
            "opening": ("valid", "corrupt"),
            "valid": ("valid",),
            "corrupt": ("quarantined",),
            "quarantined": ("fresh",),
            "fresh": ("fresh",),
        },
        source="memory/store.py: MemoryStore.__init__, _connect_validated, "
               "_quarantine_corrupt",
        gap="A recovered store is silently empty; recovery_notes is in-memory only and "
            "an in-memory store cannot be quarantined.",
    ),
    Machine(
        name="layout-recall",
        purpose="Whether the cold-start layout channel was consulted and what it returned.",
        states=("unconsulted", "disabled", "miss", "hit"),
        transitions={
            "unconsulted": ("disabled", "miss", "hit"),
            "disabled": ("disabled",),
            "miss": ("miss",),
            "hit": ("hit",),
        },
        source="agent.py: Planner._persistent_state, _persistent_layout, "
               "bind_recall_source; probe.store_reads/persistent",
        gap="A raising recall source is cached as a miss for the rest of the episode, and "
            "store_reads increments before the call, so a failed read still counts.",
    ),
    Machine(
        name="layout-freshness",
        purpose="What a persisted layout row says about the world that wrote it.",
        states=("absent", "incomplete", "legacy-complete", "current", "mismatched"),
        transitions={
            "absent": ("incomplete", "current"),
            "incomplete": ("current",),
            "legacy-complete": ("current",),
            "current": ("current", "mismatched"),
            "mismatched": ("current",),
        },
        source="agent.py: _layout_complete, _remember_layout; "
               "memory/store.py: save_layout, get_layout, layout_fingerprint",
        gap="A cold-first row may be incomplete; only a warm run writes a fingerprint, and "
            "a NULL legacy row is upgraded only when a complete run with a fingerprint "
            "reaches it.",
    ),
    Machine(
        name="telemetry-chain",
        purpose="Integrity of one append-only telemetry log.",
        states=("absent", "valid", "legacy-anchored", "corrupt", "edited",
                "reordered", "broken", "unchained"),
        transitions={
            "absent": ("valid", "legacy-anchored"),
            "valid": ("valid", "corrupt", "edited", "reordered", "broken",
                      "unchained"),
            "legacy-anchored": ("valid",),
            "corrupt": ("corrupt",),
            "edited": ("edited",),
            "reordered": ("reordered",),
            "broken": ("broken",),
            "unchained": ("unchained",),
        },
        source="telemetry/log.py: verify_chain",
        gap="Findings are free-form strings such as edited-record:3; there is no enum, "
            "and verification keeps scanning after a defect so several classes can "
            "describe one edit.",
    ),
    Machine(
        name="telemetry-anchor",
        purpose="Whether a log head/count has an external single-anchor witness.",
        states=("unanchored", "anchored", "missing", "truncated", "mismatch"),
        transitions={
            "unanchored": ("anchored",),
            "anchored": ("anchored", "missing", "truncated", "mismatch"),
            "missing": ("missing",),
            "truncated": ("truncated",),
            "mismatch": ("mismatch",),
        },
        source="telemetry/log.py: write_anchor, read_anchor, verify_chain(anchor_path=)",
        gap="The sidecar is mutable and must live outside the tampered log's control; "
            "deleting tail anchors leaves no internal evidence.",
    ),
    Machine(
        name="anchor-journal",
        purpose="An append-only chain of telemetry anchors.",
        states=("missing", "chained", "broken-prev", "rewound", "truncated"),
        transitions={
            "missing": ("chained",),
            "chained": ("chained", "broken-prev", "rewound", "truncated"),
            "broken-prev": ("broken-prev",),
            "rewound": ("rewound",),
            "truncated": ("truncated",),
        },
        source="telemetry/log.py: append_anchor, verify_anchor_journal",
        gap="Deleting tail anchors yields a shorter but internally valid journal unless the "
            "latest anchor is known externally.",
    ),
    Machine(
        name="merkle-batch",
        purpose="A Merkle commitment over the latest telemetry records.",
        states=("absent", "anchored", "proof-valid", "truncated", "root-mismatch"),
        transitions={
            "absent": ("anchored",),
            "anchored": ("anchored", "proof-valid", "truncated", "root-mismatch"),
            "proof-valid": ("proof-valid",),
            "truncated": ("truncated",),
            "root-mismatch": ("root-mismatch",),
        },
        source="telemetry/merkle.py: write_merkle_anchor, verify_merkle_anchor, "
               "verify_merkle_proof",
        gap="The root is a separate witness that can be rewritten with the log; membership "
            "is proven only for the committed batch, not global order.",
    ),
    Machine(
        name="merkle-journal",
        purpose="The hash-chained journal of Merkle batches and its compaction.",
        states=("missing", "chained", "rollback-refused", "truncated-batch",
                "compacted"),
        transitions={
            "missing": ("chained",),
            "chained": ("chained", "rollback-refused", "truncated-batch", "compacted"),
            "rollback-refused": ("rollback-refused",),
            "truncated-batch": ("truncated-batch",),
            "compacted": ("compacted",),
        },
        source="telemetry/merkle.py: append_merkle_anchor, verify_merkle_journal, "
               "compact_merkle_journal",
        gap="Appends are not locked against compaction, so compaction is an offline "
            "single-writer operation.",
    ),
    Machine(
        name="claim-status",
        purpose="The status a claim's verdict history currently implies.",
        states=("proposed", "supported", "refuted", "inconclusive"),
        transitions={
            "proposed": ("supported", "refuted", "inconclusive"),
            "supported": ("supported", "refuted", "inconclusive"),
            "refuted": ("refuted", "supported", "inconclusive"),
            "inconclusive": ("inconclusive", "supported", "refuted"),
        },
        source="claims.py: CLAIM_STATUSES, ClaimLedger.record, _validate_claim",
        gap="Status is derived from the last verdict, so it is not terminal; a later "
            "verdict silently overwrites the status a reader saw.",
    ),
    Machine(
        name="verdict-event",
        purpose="One immutable supports/refutes/inconclusive verdict record.",
        states=("supports", "refutes", "inconclusive"),
        transitions={
            "supports": ("supports", "refutes", "inconclusive"),
            "refutes": ("supports", "refutes", "inconclusive"),
            "inconclusive": ("supports", "refutes", "inconclusive"),
        },
        source="claims.py: VERDICT_STATUSES, Verdict, record_verdict",
        gap="inconclusive is both a verdict event and a claim status, so a reader cannot "
            "tell the level from the token alone.",
    ),
    Machine(
        name="claim-store",
        purpose="Durability and recovery of a checksummed claim snapshot.",
        states=("absent", "valid", "mac-error", "corrupt", "quarantined",
                "backup-loaded", "empty"),
        transitions={
            "absent": ("valid", "empty"),
            "valid": ("valid", "mac-error", "corrupt"),
            "mac-error": ("mac-error",),
            "corrupt": ("quarantined",),
            "quarantined": ("backup-loaded", "empty"),
            "backup-loaded": ("backup-loaded",),
            "empty": ("empty",),
        },
        source="claims_store.py: save_ledger, load_ledger, verify_ledger_file",
        gap="A MAC error deliberately does not quarantine, while a checksum defect does; "
            "the two failures therefore have different recovery outcomes.",
    ),
    Machine(
        name="calibration-journal",
        purpose="The append-only forecast journal, its archive rotation and key state.",
        states=("absent", "live", "rotated", "archived", "corrupt",
                "keyed-refused"),
        transitions={
            "absent": ("live",),
            "live": ("live", "rotated", "corrupt", "keyed-refused"),
            "rotated": ("live", "archived"),
            "archived": ("archived",),
            "corrupt": ("corrupt",),
            "keyed-refused": ("keyed-refused",),
        },
        source="calibration_store.py: append_forecasts, rotate_forecast_journal, "
               "_rotate_locked, load_all_forecasts",
        gap="Rotation is idempotent by id, but an unkeyed rotation over keyed evidence is "
            "refused and leaves the live journal unbounded until a keyed caller rotates it.",
    ),
    Machine(
        name="resume-decision",
        purpose="Whether a stored episode may resume under the current request.",
        states=("resume", "new", "ask"),
        transitions={
            "resume": ("resume", "new", "ask"),
            "new": ("resume", "new", "ask"),
            "ask": ("resume", "new", "ask"),
        },
        source="identity.py: resume_decision, resume_guard, prepare_resume",
        gap="A missing digest asks under strict/ask but resumes under any; the decision "
            "depends on the declared policy, not only on the digests.",
    ),
    Machine(
        name="resume-policy",
        purpose="The declared resume policy; unknown values normalise to strict.",
        states=("strict", "ask", "any"),
        transitions={
            "strict": ("strict", "ask", "any"),
            "ask": ("strict", "ask", "any"),
            "any": ("strict", "ask", "any"),
        },
        source="identity.py: RESUME_POLICIES, normalise_policy",
        gap="An unknown policy string silently becomes strict; the caller is not told.",
    ),
    Machine(
        name="planner-tracker",
        purpose="One linear plan's cursor and per-step marks.",
        states=("pending", "ok", "failed", "drained"),
        transitions={
            "pending": ("ok", "failed"),
            "ok": ("pending", "drained"),
            "failed": ("drained",),
            "drained": ("drained",),
        },
        source="planner/plan.py: Planner.add_step, mark_ok, mark_fail, recover, state",
        gap="state()['done'] is true when the cursor passes the last step even if that "
            "step failed, so done does not mean every step is ok.",
    ),
    Machine(
        name="execution-budget",
        purpose="The opt-in per-run step/LLM/token/time allowance.",
        states=("inactive", "active", "exhausted"),
        transitions={
            "inactive": ("active",),
            "active": ("active", "exhausted"),
            "exhausted": ("exhausted",),
        },
        source="budget.py: ExecutionBudget, use_budget, spend, BudgetExceeded",
        gap="exceeded names only the first dimension that tripped; it cannot be cleared, "
            "and wall time is checked only when a spend happens.",
    ),
)

BY_NAME: Dict[str, Machine] = {machine.name: machine for machine in MACHINES}

# Machines whose state vocabulary is also a live product constant. The check
# imports the module lazily so a listing stays cheap and dependency-free.
_LIVE_VOCABULARIES: Mapping[str, Tuple[str, str]] = {
    "claim-status": ("claims", "CLAIM_STATUSES"),
    "verdict-event": ("claims", "VERDICT_STATUSES"),
    "resume-policy": ("identity", "RESUME_POLICIES"),
}


def as_dict() -> Dict[str, object]:
    """Return a deterministic JSON-ready view of the whole registry."""
    return {
        "schema": 1,
        "machines": [
            {
                "name": machine.name,
                "purpose": machine.purpose,
                "states": list(machine.states),
                "transitions": {
                    state: list(targets)
                    for state, targets in machine.transitions.items()
                },
                "source": machine.source,
                "gap": machine.gap,
            }
            for machine in MACHINES
        ],
    }


def check_live() -> list:
    """Compare declared states with live product constants.

    Returns one ``{machine, declared, live, ok, error}`` row per checked
    machine. A missing module or attribute is reported as an error, not a
    crash, so the check stays a read-only diagnostic.
    """
    rows = []
    for name, (module_name, attribute) in sorted(_LIVE_VOCABULARIES.items()):
        declared = list(BY_NAME[name].states)
        try:
            module = importlib.import_module(module_name)
            live = list(getattr(module, attribute))
        except (ImportError, AttributeError) as exc:
            rows.append({"machine": name, "declared": declared, "live": None,
                         "ok": False, "error": "%s: %s" % (type(exc).__name__, exc)})
            continue
        rows.append({
            "machine": name,
            "declared": declared,
            "live": live,
            "ok": set(declared) == set(live),
            "error": None,
        })
    return rows


def run_transition(machine: Machine, source: str, target: str) -> int:
    """Print and return the triad verdict for one declared transition."""
    if source not in machine.states:
        print(f"Why: '{source}' is not a state of {machine.name}.", file=sys.stderr)
        print(f"Fix: choose one of {', '.join(machine.states)}.", file=sys.stderr)
        return 2
    if target not in machine.states:
        print(f"Why: '{target}' is not a state of {machine.name}.", file=sys.stderr)
        print(f"Fix: choose one of {', '.join(machine.states)}.", file=sys.stderr)
        return 2
    if machine.allows(source, target):
        print(f"allowed: {machine.name}: {source} -> {target}")
        return 0
    print(f"refused: {machine.name}: {source} -> {target}")
    print(f"Why: the {machine.name} machine has no such transition.", file=sys.stderr)
    targets = machine.transitions.get(source, ())
    print(f"Fix: from '{source}' use one of {', '.join(targets) or 'none'}.",
          file=sys.stderr)
    return 1


def print_machine(machine: Machine) -> None:
    """Render one machine for a human or agent reader."""
    print(f"{machine.name} - {machine.purpose}")
    print(f"Source: {machine.source}")
    print("States:")
    for state in machine.states:
        targets = machine.transitions.get(state, ())
        print(f"  {state} -> {', '.join(targets) if targets else '(terminal)'}")
    if machine.gap:
        print(f"Known gap: {machine.gap}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the read-only registry CLI."""
    parser = argparse.ArgumentParser(
        description="Inspect Brain's implicit state machines as explicit data (read-only).")
    parser.add_argument("--list", action="store_true", help="list machines (default)")
    parser.add_argument("--json", action="store_true", help="print the registry as JSON")
    parser.add_argument("--machine", help="show one machine by name")
    parser.add_argument("--from", dest="source", help="transition source state")
    parser.add_argument("--to", dest="target", help="transition target state")
    parser.add_argument("--check-status", dest="status",
                        help="check whether a state is known")
    parser.add_argument("--check", action="store_true",
                        help="compare declared states with live product constants")
    args = parser.parse_args(argv)

    if args.source is not None or args.target is not None:
        if not (args.machine and args.source is not None and args.target is not None):
            parser.error("--from and --to require --machine")
        machine = BY_NAME.get(args.machine)
        if machine is None:
            parser.error(f"unknown machine '{args.machine}'")
        return run_transition(machine, args.source, args.target)

    if args.status is not None:
        if not args.machine:
            parser.error("--check-status requires --machine")
        machine = BY_NAME.get(args.machine)
        if machine is None:
            parser.error(f"unknown machine '{args.machine}'")
        if args.status in machine.states:
            print(f"known: {machine.name}: {args.status}")
            return 0
        print(f"unknown: {machine.name}: {args.status}", file=sys.stderr)
        print(f"Fix: choose one of {', '.join(machine.states)}.", file=sys.stderr)
        return 1

    if args.check:
        rows = check_live()
        for row in rows:
            status = "ok" if row["ok"] else "drift"
            print(f"{status}: {row['machine']} declared={row['declared']} "
                  f"live={row['live']} error={row['error']}")
        return 0 if all(row["ok"] for row in rows) else 1

    if args.machine:
        machine = BY_NAME.get(args.machine)
        if machine is None:
            print(f"Why: unknown machine '{args.machine}'.", file=sys.stderr)
            print(f"Fix: choose one of {', '.join(BY_NAME)}.", file=sys.stderr)
            return 2
        print_machine(machine)
        return 0

    if args.json:
        print(json.dumps(as_dict(), indent=2))
        return 0

    print(f"{len(MACHINES)} explicit state machines (read-only):")
    for machine in MACHINES:
        print(f"  {machine.name:<20} {len(machine.states):>2} states  {machine.purpose}")
    print("Use --machine <name>, --json, --check, or --machine <name> "
          "--from <state> --to <state>.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
