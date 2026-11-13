#!/usr/bin/env python3
"""Brain, the way a person actually uses it.

    python brain.py                 talk to a local model (auto-discovered)
    python brain.py chat            same, explicit
    python brain.py doctor          check model access and say how to fix it
    python brain.py run T3_navigate run a task with a readable transcript

Model access is the point of this file. It finds whatever local server you
already have (llama-server, LM Studio, Ollama, vLLM), says plainly what it
is talking to, and when nothing is running it prints the exact command to
start one instead of failing with a stack trace. ``run`` still works with
no model at all, using the offline rule agent.

Nothing here needs a network unless you ask for a model. Exit codes:
0 success, 1 the model or task failed, 2 misuse.
"""

import argparse
import sys

from chat_session import ChatSession
from models.openai_compat import EndpointUnavailable, resolve
from worlds.grid import TASKS


def _connect(args):
    """Resolve a live model; return ``(client, source)`` or ``(None, None)``."""
    try:
        return resolve(endpoint=args.endpoint, model=args.model)
    except EndpointUnavailable as problem:
        print(str(problem), file=sys.stderr)
        return None, None


def _chat(args):
    """Interactive (or piped) conversation; returns an exit code."""
    client, source = _connect(args)
    if client is None:
        return 1
    session = ChatSession(client, max_turns=args.max_turns)
    print(session.banner(client, source))
    for command in _input_lines(args.prompt):
        command = command.strip()
        if not command:
            continue
        if command in ("/quit", "/exit"):
            break
        if command == "/help":
            print(ChatSession.help_text())
            continue
        if command == "/reset":
            print("forgot %d messages" % session.reset())
            continue
        if command == "/model":
            model, base = client.identify()
            print("%s at %s" % (model or "server default model", base))
            continue
        print("you: %s" % command)
        try:
            result = session.ask(command, max_tokens=args.max_tokens)
        except (EndpointUnavailable, ValueError) as problem:
            print("error: %s" % problem, file=sys.stderr)
            return 1
        print("model: %s" % result["text"])
        print(ChatSession.footer(result))
    return 0


def _input_lines(prompt):
    """Yield one prompt when given, otherwise every stdin line.

    A terminal user types and sees the echo they already typed; a piped or
    redirected user gets the same turns with no prompt noise, so scripted
    and interactive use share one path.
    """
    if prompt is not None:
        yield prompt
        return
    interactive = sys.stdin.isatty()
    while True:
        try:
            line = sys.stdin.readline()
        except KeyboardInterrupt:
            return
        if not line:
            return
        if interactive:
            pass
        yield line.rstrip("\r\n")


def _doctor(args):
    """Report model access in plain language; returns an exit code."""
    print("Brain doctor")
    try:
        client, source = resolve(endpoint=args.endpoint, model=args.model)
    except EndpointUnavailable as problem:
        print("model access: NOT AVAILABLE")
        print(str(problem))
        return 1
    model, base = client.identify()
    print("model access: ok")
    print("  endpoint: %s (%s)" % (base, source))
    print("  model:    %s" % (model or "server default"))
    available = client.models()
    if available:
        print("  served:   %s" % ", ".join(available[:5]))
    if args.say:
        try:
            result = client.chat(
                [{"role": "user", "content": args.say}], max_tokens=64)
        except EndpointUnavailable as problem:
            print("  chat:     FAILED - %s" % problem)
            return 1
        print("  chat:     %r %s" % (result["text"][:80],
                                     ChatSession.footer(result)))
    return 0


def _run(args):
    """Run one task with a readable transcript; returns an exit code."""
    from agent import Agent, Planner, model_label
    from models.registry import build

    planner = None
    backend_name = getattr(args, "backend", "rule")
    if backend_name != "rule":
        try:
            backend = build("openai", endpoint=args.endpoint, model=args.model)
        except KeyError as problem:
            print("error: %s" % problem, file=sys.stderr)
            return 2
        planner = Planner(backend=backend)
    agent = Agent(planner=planner) if planner is not None else Agent()
    try:
        trace = agent.run_task(args.task, args.seed, max_steps=args.max_steps)
    except ValueError as problem:
        print("error: %s" % problem, file=sys.stderr)
        return 2
    label = backend_name
    if planner is not None:
        label += " (%s)" % model_label(planner.backend)
    print("task %s, seed %d, policy %s" % (args.task, args.seed, label))
    for index, step in enumerate(trace, 1):
        state = step.get("state") or {}
        position = "[%s,%s]" % (state.get("x"), state.get("y"))
        reward = float(step.get("reward", 0.0))
        mark = "  reward %.1f" % reward if reward > 0 else ""
        print("%3d  %-8s %s%s" % (index, step.get("action"), position, mark))
    verdict, reason = agent._episode_verdict(trace, args.max_steps)
    total = sum(float(step.get("reward", 0.0)) for step in trace)
    print("%s (%s), reward %.1f" % (verdict, reason, total))
    return 0 if verdict == "done" else 1


def main(argv=None):
    """Parse arguments and dispatch; returns the process exit code."""
    parser = argparse.ArgumentParser(
        prog="brain",
        description="Talk to a local model, or run an agent task.",
        epilog="Model: --endpoint, $BRAIN_ENDPOINT, or a local server on "
               "8080/1234/11434/8000.")
    parser.add_argument("--endpoint", default=None,
                        help="base URL of an OpenAI-compatible server")
    parser.add_argument("--model", default=None,
                        help="model id when the server hosts several")
    parser.add_argument("--max-turns", type=int, default=24,
                        help="turns kept in context (default 24)")
    parser.add_argument("--max-tokens", type=int, default=512,
                        help="reply token cap (default 512)")

    modes = parser.add_subparsers(dest="mode")
    chat = modes.add_parser("chat", help="talk to the model (default)")
    chat.add_argument("--prompt", default=None,
                      help="ask one question and exit")
    doctor = modes.add_parser("doctor", help="check model access")
    doctor.add_argument("--say", default=None,
                        help="also send one test message")

    run = modes.add_parser("run", help="run an agent task (model optional)")
    run.add_argument("task", choices=TASKS,
                     help="task id, one of %s" % ", ".join(TASKS))
    run.add_argument("--seed", type=int, default=0)
    run.add_argument("--max-steps", type=int, default=200)
    run.add_argument("--backend", choices=("rule", "openai"), default="rule",
                     help="policy: rule (offline, default) or openai (ask the "
                          "local model for each action)")

    args = parser.parse_args(argv)
    if args.mode == "run":
        return _run(args)
    if not hasattr(args, "prompt"):
        args.prompt = None
    if args.mode == "doctor":
        return _doctor(args)
    return _chat(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print()
        raise SystemExit(130)
