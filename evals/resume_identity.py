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
from identity import input_digest, resume_decision
from telemetry.log import Telemetry
from worlds.grid import GridWorld

MODES = ("same", "changed-seed", "changed-target", "volatile",
         "legacy", "policy-any")


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", action="append", choices=MODES, default=[],
                        help="repeatable (default: all modes)")
    args = parser.parse_args()
    modes = tuple(args.mode) if args.mode else MODES
    print(json.dumps(run_battery(modes), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
