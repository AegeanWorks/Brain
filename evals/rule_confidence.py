"""Rule-confidence battery: BFS move ties with the action held fixed.

Across the nine pin seeds, the readout-on and readout-off traces must
have identical actions/steps/rewards. The on mode counts steps with a
readout, ambiguous steps (confidence < 1.0), non-optimal steps, and the
tie histogram. Synthetic unique/tie/collect states pin the exact values.
"""

import argparse
import json
import os
import tempfile

from agent import Agent, Planner
from telemetry.log import Telemetry

MODES = ("on", "off", "seeds", "unique", "tie", "collect", "tour")
PIN_SEEDS = (
    ("T1_forage", 71, 16, 3.0),
    ("T2_delayed_match", 3, 8, 1.0),
    ("T3_navigate", 15, 13, 1.0),
    ("T3_navigate", 65, 6, 1.0),
    ("T3_navigate", 74, 9, 1.0),
    ("T3_navigate", 202, 7, 1.0),
    ("T3_navigate", 272, 14, 1.0),
    ("T3_navigate", 307, 6, 1.0),
    ("T3_navigate", 479, 10, 1.0),
)


def _state(x, y, target=None, task="T3_navigate", items=None):
    state = {"task": task, "x": x, "y": y, "steps": 0}
    if target is not None:
        state["target"] = target
    if items is not None:
        state["items_positions"] = items
    return state


def _readout_stats(rules):
    present = [rule for rule in rules if isinstance(rule, dict)]
    ties = {}
    for rule in present:
        key = str(rule.get("ties"))
        ties[key] = ties.get(key, 0) + 1
    return {
        "readout_steps": len(present),
        "ambiguous_steps": sum(1 for rule in present
                               if rule.get("confidence", 1.0) < 1.0),
        "nonoptimal_steps": sum(1 for rule in present
                                if rule.get("optimal") is False),
        "ties": dict(sorted(ties.items())),
    }


def _tie_stats(pairs):
    alternatives_total = 0
    tie_steps = 0
    spread_steps = 0
    chosen_least = 0
    chosen_not_least = 0
    not_in_alternatives = 0
    for action, rule, _tour in pairs:
        if not isinstance(rule, dict):
            continue
        alternatives = rule.get("alternatives") or []
        alternatives_total += len(alternatives)
        if rule.get("ties", 1) <= 1 or not alternatives:
            continue
        tie_steps += 1
        visits = [item.get("visits", 0) for item in alternatives]
        if len(set(visits)) > 1:
            spread_steps += 1
        chosen = next((item for item in alternatives
                       if item.get("action") == action), None)
        if chosen is None:
            not_in_alternatives += 1
        elif chosen.get("visits", 0) == min(visits):
            chosen_least += 1
        else:
            chosen_not_least += 1
    return {
        "alternatives_total": alternatives_total,
        "tie_steps": tie_steps,
        "visit_spread_steps": spread_steps,
        "chosen_least_visited": chosen_least,
        "chosen_not_least_visited": chosen_not_least,
        "chosen_not_in_alternatives": not_in_alternatives,
    }


def _tour_stats(tours):
    present = [tour for tour in tours if isinstance(tour, dict)]
    return {
        "tour_steps": len(present),
        "tour_tie_steps": sum(1 for tour in present
                              if tour.get("tie_count", 1) > 1),
        "tour_extra_tied_firsts": sum(
            max(0, tour.get("tie_count", 1) - 1) for tour in present),
        "tour_chosen_optimal": sum(1 for tour in present
                                   if tour.get("optimal") is True),
        "tour_not_optimal": sum(1 for tour in present
                                if tour.get("optimal") is False),
    }


def _run_seed(task, seed, readout, directory, suffix):
    log_path = os.path.join(directory, "%s-%d-%s.jsonl"
                            % (task, seed, suffix))
    planner = Planner(rule_readout=readout)
    trace = Agent(planner=planner).run_task_logged(
        task, seed, max_steps=200, log_path=log_path)
    records = Telemetry(log_path).read_all()
    pairs = [(record.get("args", {}).get("action"),
              record.get("args", {}).get("probe", {}).get("rule"),
              record.get("args", {}).get("probe", {}).get("tour"))
             for record in records
             if record.get("type") == "action"
             and record.get("kind") == "step"]
    return trace, pairs


def measure_seeds(mode, directory):
    result = {"mode": mode, "steps": 0, "reward": 0.0,
              "actions_match": True, "seeds": [],
              "readout_steps": 0, "ambiguous_steps": 0,
              "nonoptimal_steps": 0, "ties": {},
              "alternatives_total": 0, "tie_steps": 0,
              "visit_spread_steps": 0, "chosen_least_visited": 0,
              "chosen_not_least_visited": 0,
              "chosen_not_in_alternatives": 0,
              "tour_steps": 0, "tour_tie_steps": 0,
              "tour_extra_tied_firsts": 0, "tour_chosen_optimal": 0,
              "tour_not_optimal": 0}
    totals = {"readout_steps": 0, "ambiguous_steps": 0,
              "nonoptimal_steps": 0, "ties": {}}
    for task, seed, _steps, _reward in PIN_SEEDS:
        on_trace, on_pairs = _run_seed(task, seed, True, directory,
                                       "%s-on" % mode)
        off_trace, off_pairs = _run_seed(task, seed, False, directory,
                                         "%s-off" % mode)
        pairs = on_pairs if mode != "off" else off_pairs
        stats = _readout_stats([rule for _action, rule, _tour in pairs])
        tie_stats = _tie_stats(pairs)
        tour_stats = _tour_stats([tour for _action, _rule, tour in pairs])
        result["steps"] += len(on_trace)
        result["reward"] += sum(record["reward"] for record in on_trace)
        result["actions_match"] = result["actions_match"] and (
            [record["action"] for record in on_trace]
            == [record["action"] for record in off_trace])
        result["seeds"].append({
            "task": task, "seed": seed, "steps": len(on_trace),
            "readout_steps": stats["readout_steps"],
            "ambiguous_steps": stats["ambiguous_steps"],
            "nonoptimal_steps": stats["nonoptimal_steps"],
            "tie_steps": tie_stats["tie_steps"],
            "visit_spread_steps": tie_stats["visit_spread_steps"],
            "chosen_least_visited": tie_stats["chosen_least_visited"],
            "chosen_not_least_visited":
                tie_stats["chosen_not_least_visited"],
            "tour_steps": tour_stats["tour_steps"],
            "tour_tie_steps": tour_stats["tour_tie_steps"],
            "tour_chosen_optimal": tour_stats["tour_chosen_optimal"],
        })
        for key in ("readout_steps", "ambiguous_steps", "nonoptimal_steps"):
            totals[key] += stats[key]
        for key in ("alternatives_total", "tie_steps", "visit_spread_steps",
                    "chosen_least_visited", "chosen_not_least_visited",
                    "chosen_not_in_alternatives", "tour_steps",
                    "tour_tie_steps", "tour_extra_tied_firsts",
                    "tour_chosen_optimal", "tour_not_optimal"):
            if key in tie_stats:
                result[key] += tie_stats[key]
            else:
                result[key] += tour_stats[key]
        for tie, count in stats["ties"].items():
            totals["ties"][tie] = totals["ties"].get(tie, 0) + count
    result.update(totals)
    result["ties"] = dict(sorted(totals["ties"].items()))
    return result


def measure_case(mode="on", directory=None):
    if directory is None:
        raise ValueError("directory is required")
    if mode in ("on", "off", "seeds"):
        return measure_seeds(mode, directory)
    planner = Planner(rule_readout=True)
    if mode == "tour":
        action = planner.plan(
            _state(0, 0, task="T1_forage", items=[[1, 0], [0, 1]]), [])
        return {"mode": mode, "action": action,
                "tour": planner.last_probe.get("tour")}
    if mode == "unique":
        action = planner.plan(_state(0, 0, [2, 0]), [])
    elif mode == "tie":
        action = planner.plan(_state(0, 0, [2, 2]), [])
    else:
        action = planner.plan(_state(2, 2, [2, 2]), [])
    rule = planner.last_probe.get("rule")
    return {"mode": mode, "action": action, "rule": rule}


def run_battery(modes=MODES):
    with tempfile.TemporaryDirectory() as directory:
        return {"model": "rule", "modes": list(modes),
                "cases": [measure_case(mode, directory)
                          for mode in modes]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", action="append", choices=MODES, default=[],
                        help="repeatable (default: all modes)")
    args = parser.parse_args()
    modes = tuple(args.mode) if args.mode else MODES
    print(json.dumps(run_battery(modes), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
