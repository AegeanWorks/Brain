"""Unit tests for planner.plan.Planner."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from planner.plan import Planner


class TestPlanner(unittest.TestCase):
    def test_add_and_next(self):
        p = Planner()
        p.add_step("load", "load_op")
        p.add_step("run", "run_op")
        cur = p.next()
        self.assertEqual(cur["name"], "load")
        self.assertEqual(cur["status"], "pending")

    def test_mark_ok_advances(self):
        p = Planner([("a", "op_a"), ("b", "op_b")])
        self.assertTrue(p.mark_ok())
        cur = p.next()
        self.assertEqual(cur["name"], "b")
        st = p.state()
        self.assertEqual(st["idx"], 1)
        self.assertEqual(st["status"], ["ok", "pending"])

    def test_mark_fail_and_recover_skips(self):
        p = Planner([("a", "op_a"), ("b", "op_b"), ("c", "op_c")])
        p.mark_ok()
        self.assertTrue(p.mark_fail())
        nxt = p.recover()
        self.assertEqual(nxt["name"], "c")
        st = p.state()
        self.assertEqual(st["status"], ["ok", "failed", "pending"])

    def test_recover_none_when_drained(self):
        p = Planner([("a", "op_a")])
        p.mark_fail()
        self.assertIsNone(p.recover())
        self.assertIsNone(p.next())
        self.assertTrue(p.state()["done"])

    def test_state_shape(self):
        p = Planner()
        st = p.state()
        self.assertIn("idx", st)
        self.assertIn("status", st)
        self.assertEqual(st["idx"], 0)
        self.assertTrue(st["done"])


if __name__ == "__main__":
    unittest.main()
