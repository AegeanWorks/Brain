"""Vector independence: the M/P/S/hub blocks are not independent readouts.

``Agent._step_vectors`` emits M=[count, hits], P=[idx, pending],
S=[errors, budget], hub=[x, y, reward] per step, and the telemetry
claim is that these measure the memory, planner and self-model modules.
In practice several components are mechanically the step index: the loop
saves one memory row, records one self-model transition and marks one
planner step per iteration, so those counters are identical by
construction rather than by measurement.

A "distinct" column count below 3 means the block is not three
independent measurements, and any integration readout computed from it
must not be read as cross-module coupling. These tests pin the audit that
makes that visible; they change no vector value.
"""

import unittest

from evals.vector_audit import (
    BLOCK_LABELS,
    audit_rows,
    column_report,
    degenerate_columns,
    duplicate_pairs,
    distinct_columns,
)


def _rows(vectors):
    """Expand (M, P, S, hub) tuples into flat 9-column rows."""
    out = []
    for m, p, s, h in vectors:
        out.append(list(m) + list(p) + list(s) + list(h))
    return out


class TestVectorAudit(unittest.TestCase):
    def test_block_labels_match_the_agent_layout(self):
        self.assertEqual(BLOCK_LABELS,
                         ["M0", "M1", "P0", "P1", "S0", "S1",
                          "hub0", "hub1", "hub2"])

    def test_column_report_names_constants(self):
        rows = _rows([
            ((1, 1), (0, 0), (0, 1.0), (0, 1, 3.0)),
            ((2, 2), (0, 0), (0, 2.0), (1, 2, 5.0)),
            ((3, 3), (0, 0), (0, 3.0), (2, 3, 4.0)),
        ])
        report = column_report(rows)
        self.assertEqual(report["constant"], ["P0", "P1", "S0"])
        self.assertEqual(report["n_rows"], 3)
        self.assertEqual(report["n_columns"], 9)

    def test_duplicate_pairs_are_named(self):
        rows = _rows([
            ((1, 1), (0, 0), (0, 1.0), (0, 1, 3.0)),
            ((2, 2), (0, 0), (0, 2.0), (1, 2, 5.0)),
            ((3, 3), (0, 0), (0, 3.0), (2, 3, 4.0)),
        ])
        pairs = duplicate_pairs(rows)
        self.assertIn(("M0", "M1"), pairs)
        self.assertIn(("M0", "S1"), pairs)
        # A constant column duplicates every other constant column.
        self.assertIn(("P0", "S0"), pairs)

    def test_distinct_nonconstant_columns_collapse_to_zero(self):
        rows = _rows([
            ((1, 1), (0, 0), (0, 1.0), (0, 0, 0.0)),
            ((2, 2), (0, 0), (0, 2.0), (0, 0, 0.0)),
            ((3, 3), (0, 0), (0, 3.0), (0, 0, 0.0)),
        ])
        # Everything that varies is the same step counter; nothing else moves.
        self.assertEqual(distinct_columns(rows), 1)
        self.assertEqual(degenerate_columns(rows), ["M1", "S1"])

    def test_independent_blocks_report_no_degeneracy(self):
        rows = _rows([
            ((1, 2), (0, 4), (0, 1.0), (5, 7, 3.0)),
            ((2, 0), (1, 3), (0, 1.0), (6, 6, 5.0)),
            ((3, 5), (2, 2), (1, 2.0), (7, 5, 4.0)),
        ])
        report = audit_rows(rows)
        self.assertEqual(report["constant"], [])
        self.assertEqual(report["duplicates"], [])
        self.assertGreaterEqual(report["distinct"], 6)

    def test_identical_column_content_is_detected_not_assumed(self):
        rows = _rows([
            ((1, 1), (0, 0), (0, 1.0), (0, 1, 0.0)),
            ((2, 2), (0, 0), (0, 2.0), (0, 2, 0.0)),
        ])
        # M0 and M1 agree here by construction of the fixture.
        self.assertIn(("M0", "M1"), duplicate_pairs(rows))

    def test_empty_rows_degrade_without_raising(self):
        report = audit_rows([])
        self.assertEqual(report["n_rows"], 0)
        self.assertEqual(report["distinct"], 0)
        self.assertEqual(report["constant"], [])
        self.assertEqual(report["duplicates"], [])


class TestLiveVectorDegeneracy(unittest.TestCase):
    """Pin the real substrate's vector structure, measured not assumed.

    One memory save, one self-model record and one planner mark happen per
    loop step, so those counters agree with the step index by construction.
    This test records the measured degeneracy so a future change that makes
    the blocks genuinely independent (or accidentally collapses more of
    them) fails here instead of silently changing what an integration
    readout means.
    """

    def _rows(self, agent, task="T1_forage", seed=71):
        import os
        import tempfile

        from evals.recompute import _vec_row
        from telemetry.log import Telemetry

        with tempfile.TemporaryDirectory() as tmp:
            log = os.path.join(tmp, "r.jsonl")
            agent.run_task_logged(task, seed, max_steps=40, log_path=log)
            steps = [r for r in Telemetry(log).read_all()
                     if r.get("type") == "action" and r.get("kind") == "step"]
        return [r for r in (_vec_row(x) for x in steps) if r]

    def test_default_agent_store_path_has_three_constant_columns(self):
        import os
        import tempfile

        from agent import Agent
        from memory.store import MemoryStore

        with tempfile.TemporaryDirectory() as d:
            store = MemoryStore(os.path.join(d, "m.db"))
            try:
                report = audit_rows(self._rows(Agent(memory_store=store)))
            finally:
                store.close()
        self.assertEqual(report["constant"], ["P0", "P1", "S0"])
        self.assertIn(("M0", "M1"), report["duplicates"])
        self.assertIn(("M0", "S1"), report["duplicates"])

    def test_full_wiring_collapses_four_counters_onto_one(self):
        import os
        import tempfile

        from agent import Agent
        from memory.store import MemoryStore
        from planner.plan import Planner as TrackerPlanner
        from self_model.model import SelfModel as PersistentSelfModel

        with tempfile.TemporaryDirectory() as d:
            store = MemoryStore(os.path.join(d, "m.db"))
            try:
                agent = Agent(
                    memory_store=store,
                    planner_tracker=TrackerPlanner(
                        [("s%d" % i, "op%d" % i) for i in range(40)]),
                    self_model=PersistentSelfModel())
                report = audit_rows(self._rows(agent))
            finally:
                store.close()
        self.assertEqual(report["constant"], [])
        # Every M/P/S counter that advances once per step is the same column.
        for pair in (("M0", "M1"), ("M0", "P0"), ("M0", "S1"),
                     ("M1", "P0"), ("P0", "S1")):
            self.assertIn(pair, report["duplicates"])
        self.assertLess(report["distinct"], report["n_columns"],
                        "every column is distinct; the degeneracy is gone")


if __name__ == "__main__":
    unittest.main()
