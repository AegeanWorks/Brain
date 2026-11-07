"""Calibration scoring: Brier, log loss, skill and reliability bins.

Failing-first: there is no scorer for forecast probabilities and no
SelfModel calibration readout. Perfect predictions should score Brier 0
and skill 1; inverted predictions Brier 1 and negative skill; unresolved
outcomes are ignored; small samples warn.
"""

import math
import unittest

from calibration import summary
from self_model.model import SelfModel


def _forecast(identifier, probability, outcome):
    return {"id": str(identifier), "probability": probability,
            "outcome": outcome}


def _perfect():
    return [_forecast(index, 1.0 if index < 5 else 0.0,
                      1 if index < 5 else 0) for index in range(10)]


def _inverted():
    return [_forecast(index, 1.0 if index >= 5 else 0.0,
                      1 if index < 5 else 0) for index in range(10)]


class TestCalibration(unittest.TestCase):
    def test_perfect_forecast(self):
        result = summary(_perfect(), min_resolved=10)
        self.assertEqual(result["counts"]["resolved"], 10)
        self.assertEqual(result["counts"]["supported"], 5)
        self.assertEqual(result["counts"]["refuted"], 5)
        self.assertAlmostEqual(result["brier"], 0.0)
        self.assertLess(result["log_loss"], 1e-9)
        self.assertAlmostEqual(result["skill"], 1.0)
        self.assertEqual(result["coverage"], 1.0)
        self.assertEqual(result["warnings"], [])

    def test_inverted_forecast(self):
        result = summary(_inverted(), min_resolved=10)
        self.assertAlmostEqual(result["brier"], 1.0)
        self.assertGreater(result["log_loss"], 20.0)
        self.assertLess(result["skill"], 0.0)
        self.assertTrue(any("overconfident" in warning
                            for warning in result["warnings"]))

    def test_calibrated_fixture_discriminates(self):
        forecasts = [
            _forecast(0, 0.9, 1), _forecast(1, 0.8, 1),
            _forecast(2, 0.7, 0), _forecast(3, 0.6, 1),
            _forecast(4, 0.5, 0), _forecast(5, 0.4, 0),
            _forecast(6, 0.3, 1), _forecast(7, 0.2, 0),
            _forecast(8, 0.1, 0), _forecast(9, 0.1, 0),
        ]
        result = summary(forecasts, min_resolved=10)
        self.assertGreater(result["brier"], 0.0)
        self.assertLess(result["brier"], 0.3)
        self.assertGreater(result["log_loss"], 0.0)
        self.assertEqual(len(result["bins"]), 5)

    def test_unresolved_outcomes_ignored(self):
        forecasts = [_forecast(0, 0.8, 1), _forecast(1, 0.2, 0),
                     _forecast(2, 0.5, None)]
        result = summary(forecasts, min_resolved=2)
        self.assertEqual(result["counts"]["total"], 3)
        self.assertEqual(result["counts"]["resolved"], 2)
        self.assertEqual(result["counts"]["ignored"], 1)
        self.assertEqual(result["coverage"], 0.6667)
        self.assertTrue(result["warnings"])

    def test_empty_and_small_samples_warn(self):
        empty = summary([], min_resolved=10)
        self.assertIsNone(empty["brier"])
        self.assertIsNone(empty["skill"])
        self.assertTrue(any("no resolved" in warning
                            for warning in empty["warnings"]))
        small = summary(_perfect()[:3], min_resolved=10)
        self.assertTrue(any("descriptive below 10" in warning
                            for warning in small["warnings"]))

    def test_invalid_inputs_rejected(self):
        for forecast in (
            _forecast(0, 1.1, 1),
            _forecast(1, -0.1, 0),
            _forecast(2, 0.5, 2),
            {"id": "3", "probability": 0.5},
            {"probability": 0.5, "outcome": 1},
        ):
            with self.assertRaises(ValueError):
                summary([forecast], min_resolved=1)
        with self.assertRaises(ValueError):
            summary(_perfect(), min_resolved=0)

    def test_selfmodel_records_confidence_and_outcomes(self):
        model = SelfModel()
        model.record(1.0, True, 1.0)
        model.record(1.0, True, 1.0)
        model.record(1.0, False, 0.5)
        model.record(1.0, False, 0.5)
        result = model.calibration(min_resolved=2)
        self.assertEqual(result["counts"]["total"], 4)
        self.assertEqual(result["counts"]["resolved"], 4)
        self.assertAlmostEqual(result["brier"], 0.125)
        self.assertTrue(any("overconfident" in warning
                            for warning in result["warnings"]))
        model.reset()
        self.assertEqual(model.calibration(min_resolved=2)["counts"]["total"], 0)


if __name__ == "__main__":
    unittest.main()
