"""A pre-outcome prediction must not be flagged as circular.

`SelfModel.calibration` warned `confidence-is-outcome` whenever the record
separated the outcome classes, because that was the signature of a
confidence computed *from* the outcome (`_conf = 1.0 if reward > 0`).

Once the confidence is formed before the action, that signature is what a
*correct* forecast looks like — the case `calibration.confidence_is_outcome`
says must not be flagged. These tests pin both directions so the warning
stays truthful:
  * `record` (post-hoc confidence) still warns;
  * `record_prediction` (pre-action) does not, and reports positive skill;
  * the agent's own run reaches real skill.
"""

import unittest

from agent import Agent
from self_model.model import SelfModel


class TestPreOutcomeCalibration(unittest.TestCase):
    def test_a_post_hoc_confidence_still_warns(self):
        model = SelfModel()
        for outcome in (1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0):
            model.record(1.0, bool(outcome),
                         1.0 if outcome else 0.5)
        result = model.calibration(min_resolved=1)
        self.assertTrue(any("confidence-is-outcome" in w
                            for w in result["warnings"]))

    def test_a_pre_outcome_prediction_does_not_warn(self):
        model = SelfModel()
        for outcome in (1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0):
            model.record_prediction(1.0, bool(outcome),
                                    0.8 if outcome else 0.05)
        result = model.calibration(min_resolved=1)
        self.assertFalse(any("confidence-is-outcome" in w
                             for w in result["warnings"]))

    def test_a_pre_outcome_prediction_reports_positive_skill(self):
        model = SelfModel()
        for outcome in (1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0):
            model.record_prediction(1.0, bool(outcome),
                                    0.8 if outcome else 0.05)
        result = model.calibration(min_resolved=1)
        self.assertGreater(result["skill"], 0.5)

    def test_reset_clears_the_pre_outcome_flag(self):
        model = SelfModel()
        model.record_prediction(1.0, True, 0.8)
        model.record_prediction(1.0, False, 0.05)
        model.reset()
        model.record(1.0, True, 1.0)
        model.record(1.0, False, 0.5)
        result = model.calibration(min_resolved=1)
        self.assertTrue(any("confidence-is-outcome" in w
                            for w in result["warnings"]))

    def test_the_agent_run_reaches_real_skill(self):
        model = SelfModel()
        for task, seed in (("T3_navigate", 15), ("T1_forage", 71),
                           ("T2_delayed_match", 3)):
            Agent(self_model=model).run_task(task, seed)
        result = model.calibration(min_resolved=1)
        self.assertGreater(result["skill"], 0.5)
        self.assertFalse(any("confidence-is-outcome" in w
                             for w in result["warnings"]))

    def test_the_recorded_values_are_the_predictor_outputs(self):
        model = SelfModel()
        Agent(self_model=model).run_task("T3_navigate", 15)
        self.assertTrue(set(model._confs) <= {0.05, 0.8, 0.5})


if __name__ == "__main__":
    unittest.main()
