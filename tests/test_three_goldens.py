"""Three-blocker golden paths: exact action sequences for the family.

Companion to test_three_blocker (five counts with rewards): step counts
pin outcomes (15/12/10/13/19) but a behavior-neutral path swap at
identical counts would drift silently. This pins the exact paths,
including the recovered (6,5) escape path.

Regeneration rule (deliberately manual, no auto-update flag): after a
reviewed planner change, recompute the five hashes on the intact tree
and replace the THREE_GOLDEN map in one reviewed edit. Never update
goldens to make a red tree green.
"""

import hashlib
import unittest

from models.manifest import canonical
from tests.test_three_blocker import THREE_CONFIGS, _three_steps

THREE_GOLDEN = {
    ((6, 7), ((2, 7), (5, 4), (6, 3))): "7949f4d396bc9dbef85853de9a3b8356a4fd974dd224e58ac726c466bbd1214a",
    ((7, 3), ((5, 2), (7, 0), (6, 1))): "41cfa636ca65469e9809e6d6d1edab9809304243be8fc195404414487dd44dba",
    ((6, 0), ((5, 0), (2, 1), (7, 1))): "91e21d46ea59362931cafd2c69869a7da9f110aa71f8c8d0fc02b2f8b7963f50",
    ((4, 7), ((4, 4), (7, 7), (3, 1))): "0ecb47ebdc6e248e35c10877c4f112cee51a9d56ab5479a836aecb3447446b6f",
    ((6, 5), ((6, 4), (5, 5), (3, 5))): "9ed8486fc3a9aebe3e66206cbd9f844b5f97f40a92db841abb4ea015bd7d62e9",
}


def _fingerprint(trace):
    return hashlib.sha256(canonical([r["action"] for r in trace]).encode()).hexdigest()


class TestThreeGoldens(unittest.TestCase):
    def test_three_paths_match_golden_hashes(self):
        self.assertEqual(len(THREE_GOLDEN), 5)
        self.assertEqual(len(THREE_CONFIGS), 5)
        for target, obstacles, want_steps, want_reward in THREE_CONFIGS:
            key = (tuple(target), tuple(tuple(o) for o in obstacles))
            want = THREE_GOLDEN[key]
            trace = _three_steps(target, obstacles)
            self.assertTrue(trace[-1]["done"], "%r %r" % (target, obstacles))
            self.assertEqual(sum(r["reward"] for r in trace), want_reward)
            self.assertEqual(len(trace), want_steps)
            self.assertEqual(_fingerprint(trace), want, "%r %r" % (target, obstacles))


if __name__ == "__main__":
    unittest.main()
