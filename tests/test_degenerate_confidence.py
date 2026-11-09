"""A calibration score must name circular confidence, not present it.

``Agent`` records a step's confidence *after* the reward is known (``1.0``
on a rewarded step, ``0.5`` otherwise), so ``SelfModel.calibration()``
scores a record where the probability is a function of the outcome. Brier
then restates the base rate and ``skill`` is structurally negative; the
score is a property of the record's construction, not a forecast measure.

``calibration.summary`` deliberately does not apply this diagnosis: a
genuinely perfect forecast also separates the classes, and flagging it
would be wrong. ``SelfModel.calibration`` knows the confidence is post-hoc
and appends the warning.
"""

import unittest

from calibration import confidence_is_outcome, summary
from self_model.model import SelfModel


def _pairs(rows):
    return [{"id": "i%d" % i, "probability": p, "outcome": o}
            for i, (p, o) in enumerate(rows)]


def _flagged(result):
    return any(w.startswith("confidence-is-outcome")
               for w in result["warnings"])


class TestConfidenceDiagnosis(unittest.TestCase):
    def test_perfect_separation_is_diagnosed(self):
        self.assertTrue(confidence_is_outcome(
            _pairs([(1.0, 1), (0.5, 0), (0.5, 0), (1.0, 1)])))

    def test_genuine_spread_is_not_diagnosed(self):
        self.assertFalse(confidence_is_outcome(
            _pairs([(0.9, 1), (0.6, 1), (0.4, 0), (0.2, 0)])))

    def test_single_confidence_across_both_classes_is_diagnosed(self):
        self.assertTrue(confidence_is_outcome(
            _pairs([(0.5, 1), (0.5, 0), (0.5, 1), (0.5, 0)])))

    def test_single_outcome_class_is_not_diagnosed(self):
        self.assertFalse(confidence_is_outcome(
            _pairs([(0.5, 0), (0.5, 0), (0.5, 0)])))

    def test_partial_separation_is_not_diagnosed(self):
        # Outcome 1 carries two confidences, so it is not a function.
        self.assertFalse(confidence_is_outcome(
            _pairs([(0.9, 1), (0.7, 1), (0.3, 0)])))

    def test_summary_does_not_flag_a_perfect_forecast(self):
        # A perfect forecast separates the classes but is a valid score.
        result = summary(_pairs([(1.0, 1), (0.0, 0)] * 5), min_resolved=10)
        self.assertFalse(_flagged(result))
        self.assertAlmostEqual(result["brier"], 0.0)

    def test_self_model_calibration_flags_its_own_record(self):
        model = SelfModel()
        # Reproduce what Agent records: confidence implies the outcome.
        for outcome in (0, 0, 1, 0, 1, 0):
            model.record(1.0, bool(outcome), 1.0 if outcome else 0.5)
        result = model.calibration(min_resolved=1)
        self.assertTrue(_flagged(result))
        self.assertIsNotNone(result["brier"])

    def test_self_model_with_spread_is_not_flagged(self):
        model = SelfModel()
        for outcome, conf in ((1, 0.9), (1, 0.7), (0, 0.3), (0, 0.2)):
            model.record(1.0, bool(outcome), conf)
        result = model.calibration(min_resolved=1)
        self.assertFalse(_flagged(result))

    def test_the_real_agent_run_is_no_longer_flagged(self):
        # Re-baselined in ADR-140. The run used to record `1.0 if reward > 0
        # else 0.5`, so it was flagged as circular. The confidence is now
        # formed before the action, so the diagnosis must not fire — even
        # though the predictor separates the classes, which is what a
        # correct forecast looks like.
        from agent import Agent
        from self_model.model import SelfModel as PersistentSelfModel

        model = PersistentSelfModel()
        Agent(self_model=model).run_task("T3_navigate", 15)
        result = model.calibration()
        self.assertFalse(_flagged(result))
        self.assertIsNotNone(result["brier"])
        self.assertEqual(result["counts"]["resolved"], 13)


if __name__ == "__main__":
    unittest.main()
