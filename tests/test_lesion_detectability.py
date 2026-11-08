"""Lesion detectability: a differential must be able to fail for its reason.

``test_planner_and_selfmodel_lesions_change_nothing`` asserts that zeroing
P or S leaves ``syn`` unchanged, and reads that as "planner and self-model
are not part of the measured integration". The assertion cannot fail for
that reason: ``synergy`` never reads columns 2..5, so replacing P/S with
random noise leaves ``syn`` byte-identical too. A control that cannot
distinguish its lesion from arbitrary noise is vacuous (EVID-009).

These tests pin the detectable surface per module, so the lesion suite
can assert "this change is invisible to this readout" as a measured fact
rather than an untested assumption, and so an invisible module cannot be
mistaken for an absent one.
"""

import unittest

from evals.estimators import SYNERGY_COLUMNS, synergy, synergy_scope
from evals.lesion_audit import (
    LESION_MODULES,
    MODULE_SPANS,
    detectability,
    module_columns,
    substitute_module,
)


def _rows(width=9, n=12):
    """Deterministic rows whose module block occupies columns 0..width-1."""
    rows = []
    for i in range(n):
        rows.append([float(i % 4), float((i * 3) % 5),
                     float(i % 3), float((i * 2) % 7),
                     float((i * 5) % 6), float(i % 2),
                     float(i % 8), float((i * 3) % 8), float(i % 2)])
    return rows


class TestLesionDetectability(unittest.TestCase):
    def test_module_spans_cover_the_m_ps_hub_layout(self):
        # M=[0,1], P=[2,3], S=[4,5], hub=[6..8]: the agent's block layout.
        self.assertEqual(MODULE_SPANS["M"], (0, 2))
        self.assertEqual(MODULE_SPANS["P"], (2, 4))
        self.assertEqual(MODULE_SPANS["S"], (4, 6))
        self.assertEqual(LESION_MODULES, ("M", "P", "S", "hub"))

    def test_module_columns_lists_the_span(self):
        self.assertEqual(module_columns("P"), [2, 3])
        self.assertEqual(module_columns("hub", width=9), [6, 7, 8])

    def test_synergy_sees_m_and_hub_only(self):
        rows = _rows()
        target = [float(r[-1]) for r in rows]
        trace = [r[:-1] for r in rows]
        base = synergy(trace, target)
        for module in LESION_MODULES:
            swapped = substitute_module(rows, module, seed=4)
            got = synergy([r[:-1] for r in swapped],
                          [float(r[-1]) for r in swapped])
            detectable = got != base
            expected = module in ("M", "hub")
            self.assertEqual(
                detectable, expected,
                "module %s detectable=%s, expected %s" % (module, detectable, expected))

    def test_detectability_reports_which_modules_are_visible(self):
        report = detectability(_rows())
        self.assertEqual(report["synergy"]["detectable"], ["M", "hub"])
        self.assertEqual(report["synergy"]["invisible"], ["P", "S"])
        self.assertEqual(report["synergy"]["columns"], list(SYNERGY_COLUMNS))
        self.assertIn("phi", report)

    def test_a_vacuous_lesion_is_named_not_counted_as_evidence(self):
        report = detectability(_rows())
        self.assertFalse(
            report["synergy"]["all_detectable"],
            "P/S are not read by synergy; a lesion of them cannot be evidence")
        self.assertTrue(report["synergy"]["invisible"])

    def test_substitution_preserves_shape_and_other_modules(self):
        rows = _rows()
        swapped = substitute_module(rows, "P", seed=9)
        self.assertEqual(len(swapped), len(rows))
        for src, dst in zip(rows, swapped):
            self.assertEqual(len(src), len(dst))
            # M untouched
            self.assertEqual(dst[0:2], src[0:2])
            # S and hub untouched
            self.assertEqual(dst[4:], src[4:])

    def test_scope_still_reports_insufficiency_after_substitution(self):
        flat = [[5.0, float(i % 3)] + [0.0] * 6 for i in range(8)]
        scope = synergy_scope(flat, [float(i % 2) for i in range(8)])
        self.assertFalse(scope["sufficient"])
        self.assertEqual(scope["reason"], "constant-scope-column")


if __name__ == "__main__":
    unittest.main()
