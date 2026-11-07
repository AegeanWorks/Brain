"""Model-backend seam: replay fidelity, invalid, raising, no-op and stall fallbacks."""

import unittest

from agent import PLANNER_POLICY, Agent, Planner as RulePlanner, policy_digest
from models.backend import ModelBackend, StubBackend
from worlds.grid import SIZE


class RaisingBackend(ModelBackend):
    def generate(self, observation):
        raise RuntimeError("injected backend failure")


class WaitingBackend(ModelBackend):
    """Legal but stalled proposal: never moves or rewards."""

    def __init__(self):
        self.calls = 0

    def generate(self, observation):
        self.calls += 1
        return "wait"


class BlockedBackend(ModelBackend):
    """Propose a boundary/obstacle-blocked direction when one exists."""

    def __init__(self):
        self.calls = 0

    def generate(self, observation):
        self.calls += 1
        x, y = int(observation["x"]), int(observation["y"])
        obstacles = {tuple(cell) for cell in observation.get("obstacles", [])}
        for action, dx, dy in (("up", 0, -1), ("down", 0, 1),
                               ("left", -1, 0), ("right", 1, 0)):
            nx, ny = x + dx, y + dy
            if not (0 <= nx < SIZE and 0 <= ny < SIZE) or (nx, ny) in obstacles:
                return action
        return "wait"


class WrongWayBackend(ModelBackend):
    """Legal free-cell movement that maximises distance to the target."""

    def __init__(self):
        self.calls = 0

    @staticmethod
    def _distance(start, target, obstacles):
        blocked = {tuple(cell) for cell in obstacles}
        queue = [(tuple(start), 0)]
        seen = {tuple(start)}
        while queue:
            cell, dist = queue.pop(0)
            if cell == tuple(target):
                return dist
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                nxt = (cell[0] + dx, cell[1] + dy)
                if not (0 <= nxt[0] < SIZE and 0 <= nxt[1] < SIZE):
                    continue
                if nxt in blocked or nxt in seen:
                    continue
                seen.add(nxt)
                queue.append((nxt, dist + 1))
        return 10 ** 6

    def generate(self, observation):
        self.calls += 1
        target = observation.get("target")
        if target is None:
            items = observation.get("items_positions") or []
            target = items[0] if items else None
        if target is None:
            return "wait"
        x, y = int(observation["x"]), int(observation["y"])
        obstacles = observation.get("obstacles") or []
        blocked = {tuple(cell) for cell in obstacles}
        best = None
        for action, dx, dy in (("up", 0, -1), ("down", 0, 1),
                               ("left", -1, 0), ("right", 1, 0)):
            nx, ny = x + dx, y + dy
            if not (0 <= nx < SIZE and 0 <= ny < SIZE):
                continue
            if (nx, ny) in blocked:
                continue
            distance = self._distance((nx, ny), target, obstacles)
            if best is None or distance > best[0]:
                best = (distance, action)
        return best[1] if best is not None else "wait"


class AlternatingBackend(WrongWayBackend):
    """Wrong-way on odd calls, wait on even calls, breaking any streak."""

    def generate(self, observation):
        if self.calls % 2 == 1:
            self.calls += 1
            return "wait"
        return super().generate(observation)


def _rule_actions(task, seed, max_steps=200):
    return [r["action"] for r in Agent().run_task(task, seed, max_steps=max_steps)]


class TestModelBackendSeam(unittest.TestCase):
    def test_stub_replays_rule_trace_exactly(self):
        actions = _rule_actions("T3_navigate", 15)
        self.assertEqual(len(actions), 13)
        planner = RulePlanner(backend=StubBackend(actions))
        trace = Agent(planner=planner).run_task("T3_navigate", 15, max_steps=200)
        self.assertEqual([r["action"] for r in trace], actions)
        self.assertEqual(planner.fallbacks, 0)
        self.assertTrue(trace[-1]["done"])

    def test_invalid_tokens_fall_back_to_rule(self):
        rule = _rule_actions("T3_navigate", 15)
        planner = RulePlanner(backend=StubBackend(["north"]))
        trace = Agent(planner=planner).run_task("T3_navigate", 15, max_steps=200)
        self.assertEqual([r["action"] for r in trace], rule)
        self.assertEqual(planner.fallbacks, len(trace))
        self.assertTrue(trace[-1]["done"])

    def test_raising_backend_falls_back_to_rule(self):
        rule = _rule_actions("T3_navigate", 15)
        planner = RulePlanner(backend=RaisingBackend())
        trace = Agent(planner=planner).run_task("T3_navigate", 15, max_steps=200)
        self.assertEqual([r["action"] for r in trace], rule)
        self.assertEqual(planner.fallbacks, len(trace))
        self.assertTrue(trace[-1]["done"])

    def test_stalled_legal_backend_falls_back_after_window(self):
        backend = WaitingBackend()
        planner = RulePlanner(backend=backend, noop_guard=False)
        trace = Agent(planner=planner).run_task("T3_navigate", 15, max_steps=200)
        self.assertTrue(trace[-1]["done"])
        self.assertEqual(len(trace), 33)
        self.assertEqual(sum(r["reward"] for r in trace), 1.0)
        self.assertLess(backend.calls, len(trace))
        self.assertEqual(backend.calls, 21)
        self.assertEqual(planner.fallbacks, 1)
        decision = planner.last_probe["model_decision"]
        self.assertFalse(decision["accepted"])
        self.assertIsNone(decision["proposed"])
        self.assertIn(decision["rule"],
                      ("up", "down", "left", "right", "wait", "collect"))
        self.assertEqual(decision["reason"], "skipped")
        self.assertTrue(decision["skipped"])
        self.assertTrue(decision["distrusted"])
        self.assertGreaterEqual(decision["steps_since_reward"], 20)

    def test_trust_window_none_restores_the_stall(self):
        backend = WaitingBackend()
        planner = RulePlanner(backend=backend, trust_window=None,
                              noop_guard=False)
        trace = Agent(planner=planner).run_task("T3_navigate", 15, max_steps=200)
        self.assertEqual(len(trace), 200)
        self.assertEqual(sum(r["reward"] for r in trace), 0.0)
        self.assertEqual(planner.fallbacks, 0)
        self.assertEqual(backend.calls, 200)
        self.assertTrue(planner.last_probe["model_decision"]["accepted"])
        self.assertFalse(planner.last_probe["model_decision"]["distrusted"])

    def test_noop_proposal_rejected_immediately(self):
        backend = WaitingBackend()
        planner = RulePlanner(backend=backend)
        trace = Agent(planner=planner).run_task("T3_navigate", 15, max_steps=200)
        self.assertTrue(trace[-1]["done"])
        self.assertEqual(len(trace), 13)
        self.assertEqual(sum(r["reward"] for r in trace), 1.0)
        self.assertEqual(planner.fallbacks, 13)
        self.assertEqual(backend.calls, 13)
        decision = planner.last_probe["model_decision"]
        self.assertFalse(decision["accepted"])
        self.assertEqual(decision["reason"], "no-op")
        self.assertFalse(decision["distrusted"])
        self.assertTrue(decision["noop_guard"])

    def test_blocked_movement_rejected_immediately(self):
        backend = BlockedBackend()
        planner = RulePlanner(backend=backend)
        trace = Agent(planner=planner).run_task("T3_navigate", 15, max_steps=200)
        self.assertTrue(trace[-1]["done"])
        self.assertEqual(len(trace), 13)
        self.assertEqual(sum(r["reward"] for r in trace), 1.0)
        self.assertEqual(planner.fallbacks, 13)
        self.assertEqual(backend.calls, 13)
        decision = planner.last_probe["model_decision"]
        self.assertFalse(decision["accepted"])
        self.assertEqual(decision["reason"], "no-op")
        self.assertFalse(decision["distrusted"])

    def test_blocked_movement_without_guard_uses_stall_window(self):
        backend = BlockedBackend()
        planner = RulePlanner(backend=backend, noop_guard=False)
        trace = Agent(planner=planner).run_task("T3_navigate", 15, max_steps=200)
        self.assertEqual(len(trace), 33)
        self.assertEqual(sum(r["reward"] for r in trace), 1.0)
        self.assertEqual(planner.fallbacks, 1)
        self.assertEqual(backend.calls, 21)
        decision = planner.last_probe["model_decision"]
        self.assertFalse(decision["accepted"])
        self.assertTrue(decision["distrusted"])
        self.assertTrue(decision["skipped"])
        self.assertEqual(decision["reason"], "skipped")

    def test_distrust_skip_disabled_calls_after_window(self):
        backend = WaitingBackend()
        planner = RulePlanner(backend=backend, noop_guard=False,
                              skip_after_distrust=False)
        trace = Agent(planner=planner).run_task("T3_navigate", 15, max_steps=200)
        self.assertEqual(len(trace), 33)
        self.assertEqual(sum(r["reward"] for r in trace), 1.0)
        self.assertEqual(planner.fallbacks, 13)
        self.assertEqual(backend.calls, 33)
        decision = planner.last_probe["model_decision"]
        self.assertEqual(decision["proposed"], "wait")
        self.assertEqual(decision["reason"], "distrusted")
        self.assertFalse(decision["skipped"])
        self.assertTrue(decision["distrusted"])

    def test_noop_guard_independent_of_trust_window(self):
        backend = WaitingBackend()
        planner = RulePlanner(backend=backend, trust_window=None)
        trace = Agent(planner=planner).run_task("T3_navigate", 15, max_steps=200)
        self.assertEqual(len(trace), 13)
        self.assertEqual(sum(r["reward"] for r in trace), 1.0)
        self.assertEqual(planner.fallbacks, 13)
        self.assertEqual(planner.last_probe["model_decision"]["reason"], "no-op")
        self.assertFalse(planner.last_probe["model_decision"]["accepted"])

    def test_good_backend_keeps_zero_fallbacks(self):
        actions = _rule_actions("T3_navigate", 15)
        planner = RulePlanner(backend=StubBackend(actions))
        trace = Agent(planner=planner).run_task("T3_navigate", 15, max_steps=200)
        self.assertEqual([r["action"] for r in trace], actions)
        self.assertEqual(planner.fallbacks, 0)
        decision = planner.last_probe["model_decision"]
        self.assertTrue(decision["accepted"])
        self.assertEqual(decision["reason"], "accepted")

    def test_progress_guard_rejects_wrong_way_backend(self):
        for task, seed, steps, rejected in (
                ("T3_navigate", 15, 13, 12),
                ("T3_navigate", 65, 6, 5),
                ("T2_delayed_match", 3, 8, 8)):
            backend = WrongWayBackend()
            planner = RulePlanner(backend=backend, progress_skip_after=None)
            trace = Agent(planner=planner).run_task(task, seed, max_steps=200)
            self.assertEqual(len(trace), steps, "%s:%d" % (task, seed))
            self.assertEqual(sum(r["reward"] for r in trace), 1.0)
            self.assertTrue(trace[-1]["done"])
            self.assertEqual(backend.calls, steps)
            self.assertEqual(planner.progress_rejections, rejected)
            self.assertGreaterEqual(planner.fallbacks, steps - 1)
            self.assertLessEqual(planner.fallbacks, steps)
            decision = planner.last_probe["model_decision"]
            self.assertFalse(decision["accepted"])
            self.assertEqual(decision["reason"], "no-progress")
            self.assertFalse(decision["distrusted"])
            self.assertTrue(decision["progress_guard"])

    def test_progress_guard_off_restores_wrong_way_cost(self):
        for task, seed, steps, calls in (("T3_navigate", 15, 33, 21),
                                         ("T3_navigate", 65, 26, 21),
                                         ("T2_delayed_match", 3, 34, 21)):
            backend = WrongWayBackend()
            planner = RulePlanner(backend=backend, progress_guard=False)
            trace = Agent(planner=planner).run_task(task, seed, max_steps=200)
            self.assertEqual(len(trace), steps, "%s:%d" % (task, seed))
            self.assertEqual(sum(r["reward"] for r in trace), 1.0)
            self.assertEqual(backend.calls, calls)
            self.assertEqual(planner.fallbacks, 1)
            self.assertEqual(planner.progress_rejections, 0)
            self.assertTrue(planner.last_probe["model_decision"]["distrusted"])

    def test_progress_guard_leaves_item_tours_untouched(self):
        backend = WrongWayBackend()
        planner = RulePlanner(backend=backend)
        trace = Agent(planner=planner).run_task("T1_forage", 71,
                                                max_steps=200)
        self.assertEqual(len(trace), 36)
        self.assertEqual(sum(r["reward"] for r in trace), 3.0)
        self.assertEqual(backend.calls, 22)
        self.assertEqual(planner.fallbacks, 1)
        self.assertEqual(planner.progress_rejections, 0)
        self.assertTrue(planner.last_probe["model_decision"]["distrusted"])

    def test_progress_guard_independent_of_noop_guard(self):
        backend = WrongWayBackend()
        planner = RulePlanner(backend=backend, noop_guard=False,
                              progress_skip_after=None)
        trace = Agent(planner=planner).run_task("T3_navigate", 15,
                                                max_steps=200)
        self.assertEqual(len(trace), 13)
        self.assertEqual(backend.calls, 13)
        self.assertEqual(planner.fallbacks, 12)
        self.assertEqual(planner.progress_rejections, 12)
        self.assertEqual(planner.last_probe["model_decision"]["reason"],
                         "no-progress")

    def test_progress_skip_stops_calls_after_streak(self):
        for task, seed, steps, calls in (
                ("T3_navigate", 15, 13, 4),
                ("T3_navigate", 65, 6, 4),
                ("T2_delayed_match", 3, 8, 3)):
            backend = WrongWayBackend()
            planner = RulePlanner(backend=backend)
            trace = Agent(planner=planner).run_task(task, seed, max_steps=200)
            self.assertEqual(len(trace), steps, "%s:%d" % (task, seed))
            self.assertEqual(sum(r["reward"] for r in trace), 1.0)
            self.assertEqual(backend.calls, calls)
            self.assertEqual(planner.progress_rejections, 3)
            decision = planner.last_probe["model_decision"]
            self.assertEqual(decision["reason"], "skipped-progress")
            self.assertTrue(decision["skipped"])
            self.assertTrue(decision["progress_distrusted"])
            self.assertEqual(decision["progress_streak"], 3)
            self.assertEqual(decision["progress_skip_after"], 3)
            self.assertFalse(decision["distrusted"])

    def test_progress_skip_none_keeps_all_calls(self):
        for task, seed, steps, rejected in (
                ("T3_navigate", 15, 13, 12),
                ("T3_navigate", 65, 6, 5),
                ("T2_delayed_match", 3, 8, 8)):
            backend = WrongWayBackend()
            planner = RulePlanner(backend=backend, progress_skip_after=None)
            trace = Agent(planner=planner).run_task(task, seed, max_steps=200)
            self.assertEqual(len(trace), steps)
            self.assertEqual(backend.calls, steps)
            self.assertEqual(planner.progress_rejections, rejected)
            decision = planner.last_probe["model_decision"]
            self.assertEqual(decision["reason"], "no-progress")
            self.assertFalse(decision["progress_distrusted"])
            self.assertIsNone(decision["progress_skip_after"])

    def test_progress_skip_requires_consecutive_rejections(self):
        backend = AlternatingBackend()
        planner = RulePlanner(backend=backend)
        trace = Agent(planner=planner).run_task("T3_navigate", 15,
                                                max_steps=200)
        self.assertEqual(len(trace), 13)
        self.assertEqual(sum(r["reward"] for r in trace), 1.0)
        self.assertEqual(backend.calls, 13)
        self.assertEqual(planner.progress_rejections, 6)
        decision = planner.last_probe["model_decision"]
        self.assertFalse(decision["progress_distrusted"])

    def test_progress_skip_resets_between_episodes(self):
        backend = WrongWayBackend()
        planner = RulePlanner(backend=backend)
        first = Agent(planner=planner).run_task("T3_navigate", 15,
                                                max_steps=200)
        second = Agent(planner=planner).run_task("T3_navigate", 15,
                                                 max_steps=200)
        self.assertEqual(len(first), 13)
        self.assertEqual(len(second), 13)
        self.assertEqual(backend.calls, 8)
        self.assertEqual(planner.progress_rejections, 6)
        self.assertEqual(sum(r["reward"] for r in first), 1.0)
        self.assertEqual(sum(r["reward"] for r in second), 1.0)
        self.assertEqual(planner.last_probe["model_decision"]["reason"],
                         "skipped-progress")

    def test_invalid_progress_skip_after_rejected(self):
        for value in (0, -1, True, 1.5, "3"):
            with self.assertRaises(ValueError):
                RulePlanner(progress_skip_after=value)

    def test_policy_declares_backend_trust_and_noop_guard(self):
        self.assertEqual(PLANNER_POLICY.get("backend_trust"),
                         "stall>=20->match-only")
        self.assertEqual(PLANNER_POLICY.get("backend_noop_guard"), "on")
        self.assertEqual(PLANNER_POLICY.get("backend_distrust_skip"), "on")
        self.assertEqual(PLANNER_POLICY.get("backend_progress_guard"),
                         "single-target-bfs")
        self.assertEqual(PLANNER_POLICY.get("backend_progress_skip"),
                         "streak>=3->match-only")
        for key in ("backend_trust", "backend_noop_guard",
                    "backend_distrust_skip", "backend_progress_guard",
                    "backend_progress_skip"):
            legacy = dict(PLANNER_POLICY)
            legacy.pop(key, None)
            self.assertNotEqual(policy_digest(), policy_digest(legacy), key)

    def test_invalid_progress_guard_rejected(self):
        with self.assertRaises(ValueError):
            RulePlanner(progress_guard="yes")

    def test_invalid_trust_window_rejected(self):
        with self.assertRaises(ValueError):
            RulePlanner(trust_window=0)
        with self.assertRaises(ValueError):
            RulePlanner(trust_window=True)
        with self.assertRaises(ValueError):
            RulePlanner(trust_window=1.5)

    def test_invalid_noop_guard_rejected(self):
        with self.assertRaises(ValueError):
            RulePlanner(noop_guard="yes")

    def test_invalid_skip_after_distrust_rejected(self):
        with self.assertRaises(ValueError):
            RulePlanner(skip_after_distrust="yes")


if __name__ == "__main__":
    unittest.main()
