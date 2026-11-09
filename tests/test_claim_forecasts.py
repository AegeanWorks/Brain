"""A claim's declared confidence must be scoreable, not just stored.

``ClaimLedger.add(..., confidence=...)`` validates a probability in [0, 1]
and the claim carries it forever, but nothing scores it. The repo scores the
self-model's confidence/outcome pairs with Brier and skill; a claim's
declared confidence is the same kind of forecast and had no readout, so a
ledger could declare 0.95 on every claim and never be told it was wrong.

``claims.claim_forecasts`` turns a ledger into the scorer's input: each
claim with a resolved status becomes one ``{probability, outcome}`` record.
These tests pin the mapping and the score, and that an unresolved claim is
excluded rather than guessed.
"""

import unittest

from calibration import summary
from claims import ClaimLedger, claim_forecasts


def _ledger():
    ledger = ClaimLedger()
    supported = ledger.add("a", "kill a", confidence=0.9)
    ledger.record(supported.id, "supports", "evidence a")
    refuted = ledger.add("b", "kill b", confidence=0.8)
    ledger.record(refuted.id, "refutes", "evidence b")
    inconclusive = ledger.add("c", "kill c", confidence=0.2)
    ledger.record(inconclusive.id, "inconclusive", "no evidence")
    ledger.add("d", "kill d", confidence=0.5)  # still proposed
    return ledger


class TestClaimForecasts(unittest.TestCase):
    def test_resolved_claims_become_forecasts(self):
        forecasts = claim_forecasts(_ledger())
        self.assertEqual(len(forecasts), 3)
        by_id = {f["id"]: f for f in forecasts}
        self.assertEqual(by_id["C1"]["probability"], 0.9)
        self.assertEqual(by_id["C1"]["outcome"], 1)
        self.assertEqual(by_id["C2"]["outcome"], 0)
        self.assertEqual(by_id["C3"]["outcome"], None)

    def test_a_proposed_claim_is_excluded(self):
        forecasts = claim_forecasts(_ledger())
        self.assertNotIn("C4", {f["id"] for f in forecasts})

    def test_inconclusive_is_kept_as_unresolved(self):
        # It is a verdict, so the claim is resolved to 'inconclusive'; the
        # outcome is None so the scorer ignores it and reports coverage.
        forecasts = claim_forecasts(_ledger())
        c3 = next(f for f in forecasts if f["id"] == "C3")
        self.assertIsNone(c3["outcome"])

    def test_the_score_is_computable(self):
        result = summary(claim_forecasts(_ledger()), min_resolved=1)
        self.assertEqual(result["counts"]["total"], 3)
        self.assertEqual(result["counts"]["resolved"], 2)
        self.assertEqual(result["counts"]["ignored"], 1)
        self.assertIsNotNone(result["brier"])
        # 0.9 on a 1 and 0.8 on a 0: (0.01 + 0.64) / 2
        self.assertAlmostEqual(result["brier"], 0.325, places=6)

    def test_an_all_confident_ledger_scores_badly(self):
        ledger = ClaimLedger()
        for index in range(4):
            claim = ledger.add("c%d" % index, "k%d" % index, confidence=0.95)
            ledger.record(claim.id, "refutes" if index % 2 else "supports",
                          "e%d" % index)
        result = summary(claim_forecasts(ledger), min_resolved=1)
        self.assertGreater(result["brier"], 0.4)

    def test_empty_ledger_yields_no_forecasts(self):
        self.assertEqual(claim_forecasts(ClaimLedger()), [])

    def test_the_mapping_does_not_change_the_ledger(self):
        ledger = _ledger()
        before = ledger.to_dict()
        claim_forecasts(ledger)
        self.assertEqual(ledger.to_dict(), before)


if __name__ == "__main__":
    unittest.main()
