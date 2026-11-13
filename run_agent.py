"""Run one episode, optionally with a backend chosen by name.

The registry in ``models.registry`` was only reachable from Python, so
"pluggable" meant "edit a call site". This is the entry point that makes the
word true from a shell:

    python -m run_agent --task T3_navigate --seed 15
    python -m run_agent --task T3_navigate --backend stub \
        --stub-script right,right,right

Exit codes follow the repository convention: 0 a completed run, 2 misuse.
Misuse covers an unknown task, an unknown backend (the message lists the
registered names), and a stub backend with no script. A backend that is
registered but fails at run time is not misuse — the planner counts the
fallback and the run still completes, which is why the report names the
backend that was *asked for* separately from the label that was *pinned*.
"""

import argparse
import json
import sys

from agent import Agent, Planner, model_label
from models.registry import build, names
from worlds.grid import TASKS


def _parse_script(text):
    """Split a comma-separated action script, ignoring blanks."""
    return [token.strip() for token in text.split(",") if token.strip()]


def _build_backend(name, script, endpoint=None, model=None):
    """Build a registered backend, or exit 2 with the available names."""
    try:
        if name == "stub":
            if not script:
                print("run_agent: --backend stub requires --stub-script.\n"
                      "  Fix: --stub-script right,right,right", file=sys.stderr)
                raise SystemExit(2)
            return build(name, script=script)
        if name == "openai":
            return build(name, endpoint=endpoint, model=model)
        return build(name)
    except KeyError as exc:
        print("run_agent: %s\n  Available: %s"
              % (exc.args[0], ", ".join(names())), file=sys.stderr)
        raise SystemExit(2)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="run_agent",
        description="Run one deterministic episode and report the outcome.")
    parser.add_argument("--task", required=True, choices=TASKS,
                        help="task id, one of %s" % (", ".join(TASKS),))
    parser.add_argument("--seed", type=int, default=0,
                        help="episode seed (default 0)")
    parser.add_argument("--max-steps", type=int, default=200,
                        help="step cap (default 200)")
    parser.add_argument("--backend", default=None,
                        help="registered backend name; omit for the rule policy")
    parser.add_argument("--stub-script", default=None,
                        help="comma-separated action script for the stub backend")
    parser.add_argument("--endpoint", default=None,
                        help="OpenAI-compatible base URL for --backend openai")
    parser.add_argument("--model", default=None,
                        help="model id for --backend openai (default: server's)")
    args = parser.parse_args(argv)

    backend = None
    if args.backend is not None:
        script = _parse_script(args.stub_script or "")
        backend = _build_backend(args.backend, script,
                                 endpoint=args.endpoint, model=args.model)

    planner = Planner(backend=backend) if backend is not None else None
    agent = Agent(planner=planner) if planner is not None else Agent()
    trace = agent.run_task(args.task, args.seed, max_steps=args.max_steps)

    reward = float(trace[-1].get("reward", 0.0)) if trace else 0.0
    report = {
        "task": args.task,
        "seed": args.seed,
        "backend": args.backend or "rule",
        "model": model_label(backend),
        "steps": len(trace),
        "reward": reward,
        "done": bool(trace) and bool(trace[-1].get("done")),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
