"""Execution budgets: steps, LLM calls, tokens and wall time.

Failing-first: Brain has max_steps but no shared budget, spend accounting
or pressure snapshot. The opt-in budget must stop an agent before the
next action when a dimension is exhausted, while a generous budget keeps
actions byte-identical and no budget remains a no-op.
"""

import unittest

from agent import Agent, Planner
from budget import (BudgetExceeded, ExecutionBudget, budget_from_limits,
                    current_budget, spend, use_budget)
from models.backend import ModelBackend


class WaitingBackend(ModelBackend):
    def __init__(self):
        self.calls = 0

    def generate(self, observation):
        self.calls += 1
        return "wait"


class PromptBackend(ModelBackend):
    """Decline but report a fixed prompt token cost."""

    def __init__(self, tokens=5):
        self.calls = 0
        self.last_prompt_stats = {"tokens": tokens, "omitted": 0}

    def generate(self, observation):
        self.calls += 1
        return None


class TestExecutionBudget(unittest.TestCase):
    def test_spend_pressure_and_snapshot(self):
        budget = budget_from_limits({"max_steps": 3, "max_llm_calls": 2,
                                     "max_tokens": 10, "max_seconds": 60})
        self.assertEqual(budget.remaining("steps"), 3)
        budget.spend("steps")
        budget.spend("llm_calls")
        self.assertEqual(budget.snapshot()["used"]["steps"], 1)
        self.assertEqual(budget.snapshot()["used"]["llm_calls"], 1)
        self.assertGreaterEqual(budget.pressure, 0.5)
        self.assertEqual(current_budget(), None)

    def test_step_limit_raises(self):
        budget = budget_from_limits({"max_steps": 1})
        budget.spend("steps")
        with self.assertRaises(BudgetExceeded) as context:
            budget.spend("steps")
        self.assertEqual(context.exception.kind, "steps")
        self.assertEqual(context.exception.limit, 1.0)

    def test_zero_seconds_raises(self):
        budget = budget_from_limits({"max_seconds": 0})
        with self.assertRaises(BudgetExceeded) as context:
            budget.spend("steps")
        self.assertEqual(context.exception.kind, "seconds")

    def test_context_scope_is_opt_in(self):
        budget = budget_from_limits({"max_steps": 2})
        spend("steps")
        self.assertEqual(budget.used["steps"], 0)
        with use_budget(budget):
            spend("steps")
            self.assertIs(current_budget(), budget)
            self.assertEqual(budget.used["steps"], 1)
        self.assertIsNone(current_budget())
        spend("steps")
        self.assertEqual(budget.used["steps"], 1)

    def test_invalid_limits_and_kind_rejected(self):
        with self.assertRaises(ValueError):
            budget_from_limits({"max_steps": 0})
        with self.assertRaises(ValueError):
            ExecutionBudget(limits={"max_steps": True})
        budget = budget_from_limits()
        with self.assertRaises(ValueError):
            budget.spend("unknown")
        with self.assertRaises(ValueError):
            budget.spend("steps", -1)

    def test_generous_budget_keeps_agent_actions(self):
        rule = Agent().run_task("T3_navigate", 15)
        budget = budget_from_limits({})
        bounded = Agent().run_task("T3_navigate", 15, budget=budget)
        self.assertEqual([record["action"] for record in bounded],
                         [record["action"] for record in rule])
        self.assertEqual(len(bounded), 13)
        self.assertEqual(sum(record["reward"] for record in bounded), 1.0)
        self.assertEqual(budget.used["steps"], 13)

    def test_step_budget_stops_before_next_action(self):
        agent = Agent()
        budget = budget_from_limits({"max_steps": 3})
        with self.assertRaises(BudgetExceeded) as context:
            agent.run_task("T3_navigate", 15, budget=budget)
        self.assertEqual(context.exception.kind, "steps")
        self.assertEqual(len(agent.telemetry.events()), 3)
        self.assertEqual(budget.used["steps"], 4)
        self.assertEqual(budget.exceeded, "steps")

    def test_llm_call_budget_stops_before_next_call(self):
        backend = WaitingBackend()
        agent = Agent(planner=Planner(backend=backend))
        budget = budget_from_limits({"max_llm_calls": 2})
        with self.assertRaises(BudgetExceeded) as context:
            agent.run_task("T3_navigate", 15, budget=budget)
        self.assertEqual(context.exception.kind, "llm_calls")
        self.assertEqual(backend.calls, 2)
        self.assertEqual(budget.used["llm_calls"], 3)
        self.assertEqual(budget.exceeded, "llm_calls")

    def test_token_budget_spends_prompt_stats(self):
        backend = PromptBackend(tokens=5)
        agent = Agent(planner=Planner(backend=backend))
        budget = budget_from_limits({"max_tokens": 8})
        with self.assertRaises(BudgetExceeded) as context:
            agent.run_task("T3_navigate", 15, budget=budget)
        self.assertEqual(context.exception.kind, "tokens")
        self.assertEqual(backend.calls, 2)
        self.assertEqual(budget.used["tokens"], 10)

    def test_elapsed_and_remaining(self):
        budget = budget_from_limits({"max_seconds": 60})
        self.assertGreaterEqual(budget.elapsed(), 0.0)
        self.assertLessEqual(budget.remaining("seconds"), 60.0)


if __name__ == "__main__":
    unittest.main()
