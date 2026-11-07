"""Policy binding: run headers cite the producing configuration.

Transferred idea: Assay per-record policy citation + research-engine
3b evidence binding (a run is bound to what produced it). The header
names the planner policy, its digest, and the model label, all covered
by the hash chain, so a header edited after the fact fails verify.
"""

import json
import os
import tempfile
import unittest

from agent import Agent, PLANNER_POLICY, model_label, policy_digest
from models.backend import StubBackend
from telemetry.log import Telemetry, verify_chain


def _logged_header(task="T3_navigate", seed=15, backend=None):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "run.jsonl")
        planner_kwargs = {} if backend is None else {"backend": backend}
        from agent import Planner
        agent = Agent(planner=Planner(**planner_kwargs))
        agent.run_task_logged(task, seed, log_path=path)
        rows = Telemetry(path).read_all()
        return rows[0], verify_chain(path)


class TestPolicyBinding(unittest.TestCase):
    def test_header_cites_policy_and_model(self):
        header, result = _logged_header()
        self.assertEqual(header["policy"], PLANNER_POLICY["name"])
        self.assertEqual(header["policy_sha256"], policy_digest())
        self.assertEqual(header["model"], "rule")
        self.assertTrue(result["ok"])

    def test_digest_stable_and_config_sensitive(self):
        self.assertEqual(policy_digest(), policy_digest())
        self.assertEqual(len(policy_digest()), 64)
        altered = dict(PLANNER_POLICY)
        altered["lookahead_depth"] = 3
        self.assertNotEqual(policy_digest(altered), policy_digest())

    def test_stub_backend_label(self):
        header, _ = _logged_header(backend=StubBackend(["wait"] * 200))
        self.assertEqual(header["model"], "StubBackend")
        self.assertEqual(model_label(None), "rule")

    def test_edited_policy_fails_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run.jsonl")
            agent = Agent()
            agent.run_task_logged("T3_navigate", 15, log_path=path)
            with open(path, "r", encoding="utf-8") as f:
                lines = [ln for ln in f if ln.strip()]
            obj = json.loads(lines[0])
            obj["policy"] = "grid-rule/planner-tampered"
            lines[0] = json.dumps(obj, sort_keys=True) + "\n"
            with open(path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            result = verify_chain(path)
            self.assertFalse(result["ok"])
            self.assertIn("edited-record:0", result["findings"])


if __name__ == "__main__":
    unittest.main()
