"""Claim/verdict records with kill tests and an immutable ledger.

Failing-first: Brain has no structured claim, kill test or verdict
history. A claim must keep its text/kill test/confidence; a verdict must
append evidence and update status without mutating the previous record.
"""

import json
import unittest

from claims import (CLAIM_STATUSES, VERDICT_STATUSES, Claim, ClaimLedger,
                    Verdict)

STAMP = "2026-11-07T00:00:00Z"


class TestClaims(unittest.TestCase):
    def test_add_claim_defaults_and_ids(self):
        ledger = ClaimLedger()
        first = ledger.add("T3:15 takes 13 steps", "steps != 13",
                           confidence=0.8)
        second = ledger.add("T3:65 takes 6 steps", "steps != 6")
        self.assertEqual(first.id, "C1")
        self.assertEqual(second.id, "C2")
        self.assertEqual(first.status, "proposed")
        self.assertEqual(first.confidence, 0.8)
        self.assertEqual(first.kill_test, "steps != 13")
        self.assertEqual(first.verdicts, ())
        self.assertEqual(len(ledger.claims()), 2)

    def test_record_verdict_history_and_immutability(self):
        ledger = ClaimLedger()
        original = ledger.add("T3:15 takes 13 steps", "steps != 13")
        supported = ledger.record("C1", "supports", "actual=13", at=STAMP)
        self.assertEqual(original.status, "proposed")
        self.assertEqual(supported.status, "supported")
        self.assertEqual(len(supported.verdicts), 1)
        self.assertEqual(supported.verdicts[0].status, "supports")
        self.assertEqual(supported.verdicts[0].evidence, "actual=13")
        self.assertEqual(supported.verdicts[0].at, STAMP)
        refuted = ledger.record("C1", "refutes", "actual=12", at=STAMP)
        self.assertEqual(refuted.status, "refuted")
        self.assertEqual([v.status for v in refuted.verdicts],
                         ["supports", "refutes"])
        self.assertEqual(ledger.get("C1"), refuted)

    def test_verdict_ref_roundtrip(self):
        ledger = ClaimLedger()
        ledger.add("T3:15 takes 13 steps", "steps != 13")
        ledger.record("C1", "supports", "actual=13", at=STAMP,
                      ref="episode-abc123")
        payload = ledger.to_dict()
        restored = ClaimLedger.from_dict(payload)
        verdict = restored.get("C1").verdicts[0]
        self.assertEqual(verdict.ref, "episode-abc123")
        self.assertEqual(json.loads(json.dumps(payload)),
                         payload)

    def test_legacy_verdict_without_ref_loads_none(self):
        payload = {
            "claims": [{
                "id": "C1", "text": "text", "kill_test": "kill",
                "status": "supported", "confidence": 0.5,
                "verdicts": [{"status": "supports", "evidence": "ok",
                              "at": STAMP}],
            }]
        }
        restored = ClaimLedger.from_dict(payload)
        self.assertIsNone(restored.get("C1").verdicts[0].ref)
        self.assertEqual(restored.get("C1").status, "supported")

    def test_invalid_ref_rejected(self):
        ledger = ClaimLedger()
        ledger.add("text", "kill")
        for value in ("", "   ", 3, True):
            with self.assertRaises(ValueError):
                ledger.record("C1", "supports", "ok", at=STAMP,
                              ref=value)

    def test_ref_history_preserved(self):
        ledger = ClaimLedger()
        ledger.add("text", "kill")
        ledger.record("C1", "supports", "first", at=STAMP, ref="episode-a")
        result = ledger.record("C1", "refutes", "second", at=STAMP,
                               ref="episode-b")
        self.assertEqual([v.ref for v in result.verdicts],
                         ["episode-a", "episode-b"])
        restored = ClaimLedger.from_dict(ledger.to_dict())
        self.assertEqual([v.ref for v in restored.get("C1").verdicts],
                         ["episode-a", "episode-b"])

    def test_frozen_verdict_with_ref(self):
        verdict = Verdict("supports", "evidence", STAMP, ref="episode-a")
        with self.assertRaises(Exception):
            verdict.ref = "episode-b"
        self.assertEqual(verdict.ref, "episode-a")

    def test_inconclusive_verdict(self):
        ledger = ClaimLedger()
        ledger.add("unresolved", "no evidence")
        result = ledger.record("C1", "inconclusive", "ambiguous", at=STAMP)
        self.assertEqual(result.status, "inconclusive")

    def test_summary_counts(self):
        ledger = ClaimLedger()
        ledger.add("a", "ka")
        ledger.add("b", "kb")
        ledger.add("c", "kc")
        ledger.record("C1", "supports", "ok", at=STAMP)
        ledger.record("C2", "refutes", "bad", at=STAMP)
        summary = ledger.summary()
        self.assertEqual(summary["claims"], 3)
        self.assertEqual(summary["statuses"]["supported"], 1)
        self.assertEqual(summary["statuses"]["refuted"], 1)
        self.assertEqual(summary["statuses"]["proposed"], 1)
        self.assertEqual(summary["statuses"]["inconclusive"], 0)
        self.assertEqual(summary["verdicts"], 2)

    def test_invalid_inputs_rejected(self):
        ledger = ClaimLedger()
        with self.assertRaises(ValueError):
            ledger.add("", "kill")
        with self.assertRaises(ValueError):
            ledger.add("text", "")
        with self.assertRaises(ValueError):
            ledger.add("text", "kill", confidence=1.1)
        with self.assertRaises(ValueError):
            ledger.add("text", "kill", confidence=True)
        ledger.add("text", "kill", claim_id="C1")
        with self.assertRaises(ValueError):
            ledger.add("other", "kill", claim_id="C1")
        with self.assertRaises(ValueError):
            ledger.record("C1", "unknown", "evidence")
        with self.assertRaises(ValueError):
            ledger.record("C1", "supports", "")
        with self.assertRaises(ValueError):
            ledger.record("missing", "supports", "evidence")

    def test_to_dict_from_dict_roundtrip(self):
        ledger = ClaimLedger()
        ledger.add("T3:15 takes 13 steps", "steps != 13", confidence=0.8)
        ledger.record("C1", "supports", "actual=13", at=STAMP)
        payload = ledger.to_dict()
        restored = ClaimLedger.from_dict(payload)
        self.assertEqual(restored.claims(), ledger.claims())
        json.dumps(payload)

    def test_status_must_match_verdict_history(self):
        with self.assertRaises(ValueError):
            Claim("C1", "text", "kill", status="supported")
        with self.assertRaises(ValueError):
            Claim("C1", "text", "kill", status="supported",
                  verdicts=(Verdict("refutes", "e", STAMP),))
        with self.assertRaises(ValueError):
            Claim("C1", "text", "kill", status="proposed",
                  verdicts=(Verdict("supports", "e", STAMP),))
        Claim("C1", "text", "kill", status="refuted",
              verdicts=(Verdict("supports", "e", STAMP),
                        Verdict("refutes", "e2", STAMP)))
        Claim("C1", "text", "kill")

    def test_from_dict_rejects_inconsistent_status(self):
        payload = {"claims": [{
            "id": "C1", "text": "text", "kill_test": "kill",
            "status": "supported", "confidence": 0.5, "verdicts": [],
        }]}
        with self.assertRaises(ValueError):
            ClaimLedger.from_dict(payload)
        payload["claims"][0]["verdicts"] = [
            {"status": "refutes", "evidence": "e", "at": STAMP}]
        with self.assertRaises(ValueError):
            ClaimLedger.from_dict(payload)

    def test_verdict_texts_validated_on_load(self):
        base = {"id": "C1", "text": "text", "kill_test": "kill",
                "status": "supported", "confidence": 0.5}
        for verdict in ({"status": "supports", "evidence": "", "at": STAMP},
                        {"status": "supports", "evidence": "e", "at": ""}):
            payload = {"claims": [dict(base, verdicts=[verdict])]}
            with self.assertRaises(ValueError):
                ClaimLedger.from_dict(payload)

    def test_consistent_legacy_payload_loads(self):
        payload = {"claims": [{
            "id": "C1", "text": "text", "kill_test": "kill",
            "status": "supported", "confidence": 0.5,
            "verdicts": [{"status": "supports", "evidence": "e",
                          "at": STAMP}],
        }]}
        restored = ClaimLedger.from_dict(payload)
        self.assertEqual(restored.get("C1").status, "supported")

    def test_dataclasses_frozen(self):
        claim = Claim("C1", "text", "kill")
        with self.assertRaises(Exception):
            claim.text = "changed"
        verdict = Verdict("supports", "evidence", STAMP)
        with self.assertRaises(Exception):
            verdict.status = "refutes"
        self.assertIn(claim.status, CLAIM_STATUSES)
        self.assertIn(verdict.status, VERDICT_STATUSES)


if __name__ == "__main__":
    unittest.main()
