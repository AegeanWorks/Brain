"""Shipped public API must be reachable or it is dead weight.

`budget.py` exports `push_budget`/`pop_budget` beside `use_budget`. They are
exactly the two lines `use_budget` already performs, no module calls them,
no test calls them, and the README never mentions them. A public name that
nothing reaches is a maintenance claim nobody checks: a reader must decide
whether it is supported, and a refactor can break it silently.

Cycle 130 removes them. `use_budget` is the only supported way to install a
budget, and these tests pin that it is.
"""

import ast
import os
import unittest

import budget

BRAIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestBudgetSurface(unittest.TestCase):
    def test_push_and_pop_are_gone(self):
        self.assertFalse(hasattr(budget, "push_budget"))
        self.assertFalse(hasattr(budget, "pop_budget"))

    def test_use_budget_is_the_supported_installer(self):
        self.assertTrue(hasattr(budget, "use_budget"))
        self.assertTrue(hasattr(budget, "current_budget"))
        self.assertTrue(hasattr(budget, "spend"))

    def test_use_budget_nests_and_restores(self):
        outer = budget.budget_from_limits({"max_steps": 5})
        inner = budget.budget_from_limits({"max_steps": 9})
        self.assertIsNone(budget.current_budget())
        with budget.use_budget(outer):
            self.assertIs(budget.current_budget(), outer)
            with budget.use_budget(inner):
                self.assertIs(budget.current_budget(), inner)
            self.assertIs(budget.current_budget(), outer)
        self.assertIsNone(budget.current_budget())

    def test_use_budget_restores_on_exception(self):
        installed = budget.budget_from_limits({"max_steps": 5})
        with self.assertRaises(RuntimeError):
            with budget.use_budget(installed):
                raise RuntimeError("boom")
        self.assertIsNone(budget.current_budget())

    def test_no_module_in_the_tree_references_the_removed_names(self):
        # This test file is the only place the removed names may appear; it
        # names them once to assert their absence.
        offenders = []
        here = os.path.abspath(__file__)
        for root, dirs, files in os.walk(BRAIN):
            dirs[:] = [d for d in dirs if d not in
                       {"__pycache__", ".git", "scratch"}]
            for name in files:
                if not name.endswith(".py"):
                    continue
                path = os.path.join(root, name)
                if os.path.abspath(path) == here:
                    continue
                with open(path, encoding="utf-8") as handle:
                    body = handle.read()
                if "push_budget" in body or "pop_budget" in body:
                    offenders.append(os.path.relpath(path, BRAIN))
        self.assertEqual(offenders, [])

    def test_budget_module_still_parses_and_exports_its_contract(self):
        path = os.path.join(BRAIN, "budget.py")
        with open(path, encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        names = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
        for required in ("current_budget", "use_budget", "spend",
                         "budget_from_limits"):
            self.assertIn(required, names)


if __name__ == "__main__":
    unittest.main()
