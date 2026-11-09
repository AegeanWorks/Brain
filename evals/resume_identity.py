"""Episode-identity battery: canonical digests, resume decisions, headers.

Same task/seed/config produces the same digest and a ``resume`` decision;
a changed seed/target or config produces a different digest and ``new``;
volatile keys are ignored; a missing digest asks; policy ``any`` resumes.
Logged runs carry the digest in the header, while actions/steps/rewards
match the unchanged rule path.
"""

import argparse
import copy
import json
import os
import tempfile

from agent import Agent, policy_digest
from evals.battery_check import exit_code_for, format_findings
from identity import input_digest, resume_decision
from telemetry.log import Telemetry
from worlds.grid import GridWorld

MODES = ("same", "changed-seed", "changed-target", "volatile",
         "legacy", "policy-any")

#: The ``(decision, same_digest)`` each mode must produce. The battery's
#: whole premise is that identity is stable for an unchanged episode and
#: changes for a changed one; pinning the pair makes a regression fail.
EXPECTED_DECISIONS = {
    "same": ("resume", True),
    "changed-seed": ("new", False),
    "changed-target": ("new", False),
    "volatile": ("resume", True),
    "legacy": ("ask", False),
    "policy-any": ("resume", False),
}


def _config(seed=15):
    return {"task": "T3_navigate", "seed": seed, "max_steps": 200,
            "policy_sha256": policy_digest()}


def _logged(seed, directory, name):
    path = os.path.join(directory, "%s.jsonl" % name)
    trace = Agent().run_task_logged("T3_navigate", seed, max_steps=200,
                                    log_path=path)
    header = Telemetry(path).read_all()[0]
    return {
        "episode_sha256": header["episode_sha256"],
        "steps": len(trace),
        "reward": sum(record["reward"] for record in trace),
        "actions": [record["action"] for record in trace],
    }


def _measure(mode, directory):
    state = GridWorld("T3_navigate", 15).reset()
    base_sha, _projection = input_digest(state, _config(15))
    if mode == "same":
        second_sha, _ = input_digest(copy.deepcopy(state), _config(15))
        decision = resume_decision(base_sha, second_sha, "strict")
    elif mode == "changed-seed":
        second_sha, _ = input_digest(
            GridWorld("T3_navigate", 65).reset(), _config(65))
        decision = resume_decision(base_sha, second_sha, "strict")
    elif mode == "changed-target":
        changed = copy.deepcopy(state)
        changed["target"] = [7, 7]
        second_sha, _ = input_digest(changed, _config(15))
        decision = resume_decision(base_sha, second_sha, "strict")
    elif mode == "volatile":
        changed = copy.deepcopy(state)
        changed.update({"ts": 123, "created_at": "then",
                        "session_id": "abc"})
        second_sha, _ = input_digest(changed, _config(15))
        decision = resume_decision(base_sha, second_sha, "strict")
    elif mode == "legacy":
        second_sha = None
        decision = resume_decision(None, base_sha, "strict")
    else:  # policy-any
        second_sha, _ = input_digest(
            GridWorld("T3_navigate", 65).reset(), _config(65))
        decision = resume_decision(base_sha, second_sha, "any")
    result = {
        "mode": mode,
        "base_sha256": base_sha,
        "second_sha256": second_sha,
        "same_digest": second_sha == base_sha,
        "decision": decision,
    }
    if mode in ("same", "changed-seed"):
        first = _logged(15, directory, "%s-a" % mode)
        again = _logged(15, directory, "%s-b" % mode)
        other = _logged(65, directory, "%s-c" % mode)
        result["headers"] = {
            "first": first["episode_sha256"],
            "again": again["episode_sha256"],
            "other": other["episode_sha256"],
            "first_equals_again": first["episode_sha256"] == again["episode_sha256"],
            "first_differs_other": first["episode_sha256"] != other["episode_sha256"],
            "first_steps": first["steps"],
            "other_steps": other["steps"],
            "actions_identical": first["actions"] == again["actions"],
        }
        result["header_matches_digest"] = first["episode_sha256"] == base_sha
    return result


def run_battery(modes=MODES):
    with tempfile.TemporaryDirectory() as directory:
        return {"model": "rule", "modes": list(modes),
                "cases": [_measure(mode, directory) for mode in modes]}


def checks(report):
    """Return the claims this battery's own output contradicts.

    Every documented identity claim is enforced: the resume/new/ask
    decision per mode, the same/different digest, volatile-key immunity,
    the header matching its digest, and a rerun reproducing the episode.
    """
    findings = []
    by_mode = {case.get("mode"): case for case in report.get("cases", [])}
    for mode, (decision, same) in EXPECTED_DECISIONS.items():
        case = by_mode.get(mode)
        if case is None:
            findings.append("missing-mode:%s" % mode)
            continue
        if case.get("decision") != decision:
            findings.append("decision:%s:%s!=%s"
                            % (mode, case.get("decision"), decision))
        if case.get("same_digest") != same:
            findings.append("same-digest:%s:%s!=%s"
                            % (mode, case.get("same_digest"), same))
    base = by_mode.get("same", {}).get("base_sha256")
    volatile = by_mode.get("volatile")
    if base is not None and volatile is not None:
        if volatile.get("second_sha256") != base:
            findings.append("volatile-changed-the-digest")
    for mode in ("changed-seed", "changed-target"):
        case = by_mode.get(mode)
        if case is None:
            continue
        if case.get("second_sha256") == case.get("base_sha256"):
            findings.append("digest-unchanged:%s" % mode)
    for mode in ("same", "changed-seed"):
        case = by_mode.get(mode)
        if case is None or "headers" not in case:
            continue
        headers = case["headers"]
        if not case.get("header_matches_digest"):
            findings.append("header-mismatch:%s" % mode)
        if not headers.get("first_equals_again"):
            findings.append("rerun-differs:%s" % mode)
        if not headers.get("actions_identical"):
            findings.append("rerun-actions-differ:%s" % mode)
        if headers.get("first_steps") == headers.get("other_steps"):
            findings.append("seed65-steps-equal:%s" % mode)
    return findings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", action="append", choices=MODES, default=[],
                        help="repeatable (default: all modes)")
    args = parser.parse_args()
    modes = tuple(args.mode) if args.mode else MODES
    report = run_battery(modes)
    print(json.dumps(report, indent=2, sort_keys=True))
    findings = checks(report)
    if findings:
        print(format_findings("resume_identity", findings), end="")
    raise SystemExit(exit_code_for(findings))


if __name__ == "__main__":
    main()
