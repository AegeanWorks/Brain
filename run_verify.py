"""One call that runs every shipped verifier over a finished log.

Cycles 110-117 produced six independent checks: chain, anchor/journal,
episode digest, action replay, result pairing, and the verdict claim.
Nothing composed them, so a consumer had to know to call each one, and a
forgotten check silently weakened the verdict — exactly the failure mode
the individual cycles were fixing.

``verify_run`` runs them all and reports the union of findings, with each
check's own result kept so a caller can see which layer spoke. It is a
composition, not a new check: no verifier is reimplemented, and every
finding is passed through verbatim.
"""

from episode_replay import verify_action_replay, verify_result_records
from episode_verify import verify_episode_header
from telemetry.log import verify_chain

#: The layers ``verify_run`` composes, in the order they are reported.
LAYERS = ("chain", "episode", "replay", "results")


def verify_run(log_path, expected_policy_sha256=None,
               expected_workspace_sha256=None, expected_model=None,
               hmac_key=None, anchor_path=None, journal_path=None):
    """Run every shipped verifier over one log; return the union.

    ``chain`` verifies the hash chain (plus an optional HMAC key and an
    optional anchor or anchor journal). ``episode`` recomputes the header
    digest and applies the optional policy/workspace/model pins.
    ``replay`` replays the actions through the world and checks the verdict
    claim and word. ``results`` pairs each result record with its step.

    A raising layer is caught and reported as ``<layer>:<error>`` so one
    defect does not hide the others; a structural failure like a missing
    header is left to the layer that names it.
    """
    results = {}
    findings = []

    def _run(name, call):
        try:
            value = call()
        except Exception as exc:  # every verifier raises ValueError by contract
            findings.append("%s:%s" % (name, exc))
            results[name] = {"ok": False, "findings": ["%s" % exc]}
            return
        results[name] = value
        if not value.get("ok"):
            findings.extend(value.get("findings") or [])

    _run("chain", lambda: verify_chain(
        log_path, anchor_path=anchor_path, journal_path=journal_path,
        hmac_key=hmac_key))
    _run("episode", lambda: verify_episode_header(
        log_path, expected_policy_sha256=expected_policy_sha256,
        expected_workspace_sha256=expected_workspace_sha256,
        expected_model=expected_model))
    _run("replay", lambda: verify_action_replay(log_path,
                                                check_verdict=True))
    _run("results", lambda: verify_result_records(log_path))
    return {
        "ok": not findings,
        "log": str(log_path),
        "findings": findings,
        "layers": results,
        "checked": [name for name in LAYERS if name in results],
    }


def format_report(report):
    """Render one aggregate report as terse, greppable lines.

    One line per layer so a failing layer is visible without reading JSON,
    then the union of findings. ``OK`` prefixes a clean report.
    """
    lines = []
    status = "OK" if report.get("ok") else "FAIL"
    lines.append("%s %s" % (status, report.get("log")))
    for name in report.get("checked") or ():
        layer = report["layers"].get(name) or {}
        mark = "ok" if layer.get("ok") else "FAIL"
        lines.append("  %-8s %s" % (name, mark))
    for finding in report.get("findings") or ():
        lines.append("  ! %s" % finding)
    return "\n".join(lines) + "\n"


def main(argv=None):
    """CLI: exit 0 clean, 1 a finding, 2 misuse."""
    import argparse
    import json
    import os

    parser = argparse.ArgumentParser(
        prog="run_verify",
        description="Run every evidence verifier over one telemetry log.")
    parser.add_argument("--log", required=True, help="path to a logged run")
    parser.add_argument("--json", action="store_true",
                        help="print the full report as JSON")
    parser.add_argument("--policy", default=None,
                        help="pin the producing policy digest (64-hex)")
    parser.add_argument("--workspace", default=None,
                        help="pin the source-tree digest (64-hex)")
    parser.add_argument("--model", default=None,
                        help="pin the backend label")
    parser.add_argument("--anchor", default=None,
                        help="path to a .anchor sidecar")
    parser.add_argument("--journal", default=None,
                        help="path to a .anchors journal")
    args = parser.parse_args(argv)

    if not os.path.isfile(args.log):
        print("run_verify: FAIL %s does not exist" % args.log)
        print("  Fix: pass --log pointing at a logged run.")
        return 2
    report = verify_run(args.log, expected_policy_sha256=args.policy,
                        expected_workspace_sha256=args.workspace,
                        expected_model=args.model,
                        anchor_path=args.anchor, journal_path=args.journal)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(format_report(report), end="")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
