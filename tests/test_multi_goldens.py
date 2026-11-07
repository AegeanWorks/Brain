"""Multi-obstacle golden paths: exact action sequences for two-blocker traps.

Companion to test_golden_traces (nine pin seeds): step counts pin
outcomes (9/18/11/13) but a behavior-neutral path swap at identical
counts would drift silently. This pins the exact paths.

Regeneration rule (deliberately manual, no auto-update flag): after a
reviewed planner change, recompute the four hashes on the intact tree
and replace the MULTI_GOLDEN map in one reviewed edit. Never update
goldens to make a red tree green.
"""

import hashlib
import unittest

from models.manifest import canonical
from tests.test_multi_obstacle import MULTI_CONFIGS, _multi_steps

MULTI_GOLDEN = {
    ((5, 0), ((2, 0), (1, 1))): "28567d9826460bf352d5714b8be35ea3b429f499f64ce359c05ca240f8a8a1e0",
    ((7, 5), ((6, 1), (7, 2))): "de1154e153cdf7c7944fabdcddf3dc40a805f97996a83ff6b20265fa9ff38e92",
    ((3, 6), ((2, 2), (3, 2))): "399f17fed3793f3961a116f7aa9ba66d650ca997d5c49de9f5eb59bac8c129fe",
    ((5, 6), ((4, 4), (5, 5))): "db4f17e35c8d1edabd904d772ff1ddebbeb3b9cc8265332dbff256537e61f20a",
}


def _fingerprint(trace):
    return hashlib.sha256(canonical([r["action"] for r in trace]).encode()).hexdigest()


class TestMultiGoldens(unittest.TestCase):
    def test_multi_paths_match_golden_hashes(self):
        self.assertEqual(len(MULTI_GOLDEN), 4)
        self.assertEqual(len(MULTI_CONFIGS), 4)
        for target, obstacles, want_steps in MULTI_CONFIGS:
            key = (tuple(target), tuple(tuple(o) for o in obstacles))
            want = MULTI_GOLDEN[key]
            trace = _multi_steps(target, obstacles)
            self.assertTrue(trace[-1]["done"], "%r %r" % (target, obstacles))
            self.assertEqual(len(trace), want_steps)
            self.assertEqual(_fingerprint(trace), want, "%r %r" % (target, obstacles))


if __name__ == "__main__":
    unittest.main()
