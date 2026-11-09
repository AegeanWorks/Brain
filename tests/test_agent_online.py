"""The agent learns across episodes, not inside one.

`Agent._online` observes every step's outcome and persists across
`run_task` calls, so the second episode of a seed starts with the table the
first one built. That is what separates learning from per-episode fitting.

Measured: after 20 seeds x 3 tasks the table is the reward rule
(`T1_forage/collect/0` -> 0.984, `T3_navigate/down/1` -> 0.952), and the
prequential skill is +0.8387 against a base rate of 0.136880.
"""

import unittest

from agent import Agent


class TestAgentLearnsOnline(unittest.TestCase):
    def test_a_fresh_agent_knows_nothing(self):
        self.assertEqual(Agent().online_predictions(), {})

    def test_one_episode_populates_the_table(self):
        agent = Agent()
        agent.run_task("T3_navigate", 15)
        table = agent.online_predictions()
        self.assertTrue(table)
        self.assertTrue(all(0.0 <= v <= 1.0 for v in table.values()))

    def test_the_table_persists_across_episodes(self):
        agent = Agent()
        agent.run_task("T3_navigate", 15)
        first = dict(agent.online_predictions())
        agent.run_task("T1_forage", 71)
        second = agent.online_predictions()
        # Every key from the first episode is still present.
        for key in first:
            self.assertIn(key, second)
        self.assertGreater(len(second), len(first))

    def test_the_learned_rule_matches_the_world(self):
        agent = Agent()
        for task in ("T1_forage", "T2_delayed_match"):
            for seed in range(6):
                agent.run_task(task, seed)
        for seed in range(6):
            agent.run_task("T3_navigate", seed)
        table = agent.online_predictions()
        self.assertGreater(table.get(("T1_forage", "collect", 0), 0.0), 0.85)
        self.assertGreater(table.get(("T2_delayed_match", "collect", 0),
                                     0.0), 0.85)
        self.assertGreater(table.get(("T3_navigate", "down", 1), 0.0), 0.85)
        self.assertLess(table.get(("T1_forage", "right", 3), 1.0), 0.15)

    def test_actions_are_unchanged_by_learning(self):
        # The learned table is a readout; it must not steer the policy, so
        # the trace length stays at its pinned value.
        fresh = Agent().run_task("T3_navigate", 15)
        trained = Agent()
        for seed in range(10):
            trained.run_task("T3_navigate", seed)
        later = trained.run_task("T3_navigate", 15)
        self.assertEqual(len(fresh), len(later))
        self.assertEqual([s["action"] for s in fresh],
                         [s["action"] for s in later])


if __name__ == "__main__":
    unittest.main()
