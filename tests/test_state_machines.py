"""Explicit state-machine registry: consistency, CLI contract and live drift.

The registry is data-only, so these tests pin the two things that can
break a reader: an inconsistent transition table, and declared states
that have drifted from the product constants they describe.
"""

import contextlib
import io
import json
import unittest

from state_machines import BY_NAME, MACHINES, check_live, main


class TestStateMachineRegistry(unittest.TestCase):
    def test_registry_is_internally_consistent(self):
        self.assertGreaterEqual(len(MACHINES), 20)
        names = [machine.name for machine in MACHINES]
        self.assertEqual(len(names), len(set(names)))
        for machine in MACHINES:
            self.assertEqual(set(machine.transitions), set(machine.states),
                             machine.name)
            for source, targets in machine.transitions.items():
                for target in targets:
                    self.assertIn(target, machine.states,
                                  f"{machine.name}: {source} -> {target}")

    def test_every_machine_renders_and_checks_every_state(self):
        for machine in MACHINES:
            with contextlib.redirect_stdout(io.StringIO()) as rendered:
                self.assertEqual(main(["--machine", machine.name]), 0,
                                 machine.name)
            self.assertIn(machine.name, rendered.getvalue())
            self.assertIn("States:", rendered.getvalue())
            for state in machine.states:
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(
                        main(["--machine", machine.name, "--check-status", state]),
                        0, f"{machine.name}: {state}")

    def test_cli_matches_the_transition_table_for_every_machine(self):
        for machine in MACHINES:
            for source, targets in machine.transitions.items():
                for target in targets:
                    with contextlib.redirect_stdout(io.StringIO()):
                        self.assertEqual(
                            main(["--machine", machine.name, "--from", source,
                                  "--to", target]), 0,
                            f"{machine.name}: {source} -> {target}")
                disallowed = [state for state in machine.states
                              if state not in targets]
                if disallowed:
                    with contextlib.redirect_stdout(io.StringIO()), \
                            contextlib.redirect_stderr(io.StringIO()):
                        self.assertEqual(
                            main(["--machine", machine.name, "--from", source,
                                  "--to", disallowed[0]]), 1,
                            f"{machine.name}: {source} -> {disallowed[0]}")

    def test_list_json_and_representative_transitions(self):
        with contextlib.redirect_stdout(io.StringIO()) as listing:
            self.assertEqual(main([]), 0)
        self.assertIn("episode-verdict", listing.getvalue())

        with contextlib.redirect_stdout(io.StringIO()) as payload:
            self.assertEqual(main(["--json"]), 0)
        self.assertEqual(len(json.loads(payload.getvalue())["machines"]),
                         len(MACHINES))

        checks = [
            ("episode-verdict", "running", "done", True),
            ("episode-verdict", "done", "running", False),
            ("model-decision", "pending", "accepted", True),
            ("model-decision", "accepted", "pending", False),
            ("claim-status", "proposed", "supported", True),
            ("claim-status", "supported", "proposed", False),
            ("planner-tracker", "pending", "ok", True),
            ("planner-tracker", "drained", "pending", False),
            ("execution-budget", "active", "exhausted", True),
            ("execution-budget", "exhausted", "active", False),
        ]
        for name, source, target, expected in checks:
            self.assertEqual(BY_NAME[name].allows(source, target), expected,
                             f"{name}: {source} -> {target}")

    def test_misuse_and_unknown_names_exit_two(self):
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["--machine", "nope"]), 2)
        with self.assertRaises(SystemExit) as raised:
            with contextlib.redirect_stderr(io.StringIO()):
                main(["--bogus"])
        self.assertEqual(raised.exception.code, 2)
        with self.assertRaises(SystemExit):
            with contextlib.redirect_stderr(io.StringIO()):
                main(["--from", "a", "--to", "b"])

    def test_live_vocabularies_match_declared_states(self):
        rows = check_live()
        self.assertTrue(rows)
        for row in rows:
            self.assertTrue(row["ok"], row)
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(["--check"]), 0)
        self.assertIn("ok: claim-status", output.getvalue())


if __name__ == "__main__":
    unittest.main()
