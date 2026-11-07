"""Unit tests for self_model.model.SelfModel."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from self_model.model import SelfModel


class TestSelfModel(unittest.TestCase):
    def test_initial_snapshot(self):
        m = SelfModel()
        snap = m.snapshot()
        self.assertEqual(snap, {"steps": 0, "errors": 0, "budget": 0.0,
                                "mean_conf": 0.0, "error_rate": 0.0})

    def test_record_ok_and_fail(self):
        m = SelfModel()
        m.record(1.5, True, 0.8)
        m.record(2.5, False, 0.4)
        snap = m.snapshot()
        self.assertEqual(snap["steps"], 2)
        self.assertEqual(snap["errors"], 1)
        self.assertAlmostEqual(snap["budget"], 4.0)
        self.assertAlmostEqual(snap["mean_conf"], 0.6)
        self.assertAlmostEqual(snap["error_rate"], 0.5)

    def test_reset(self):
        m = SelfModel()
        m.record(1.0, False, 0.3)
        m.reset()
        snap = m.snapshot()
        self.assertEqual(snap["steps"], 0)
        self.assertEqual(snap["errors"], 0)
        self.assertEqual(snap["budget"], 0.0)
        self.assertEqual(snap["mean_conf"], 0.0)
        self.assertEqual(snap["error_rate"], 0.0)


if __name__ == "__main__":
    unittest.main()
