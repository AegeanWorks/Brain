"""Golden trace hashes: exact action sequences for the pin seeds.

Transferred idea: Keystone --simulate --expect-hash (pinned simulation
hash). Step counts and rewards pin outcomes; this pins the exact paths.
Any routing change — even a behavior-neutral path swap at identical
step counts — fails loudly instead of drifting silently.

Regeneration rule (deliberately manual, no auto-update flag): after a
reviewed planner change, recompute the nine hashes on the intact tree
and replace the GOLDEN map in one reviewed edit. Never update goldens
to make a red tree green.
"""

import hashlib
import unittest

from agent import Agent
from models.manifest import canonical

GOLDEN = {
    ("T1_forage", 71): "bafe50ffa65a5a6fc8033b2a5aaf714ffca8541f9c853469922540dd5884909f",
    ("T2_delayed_match", 3): "8d077e83551ba256f7e64b04269eae823e512e1df83317b0779789c854676b5d",
    ("T3_navigate", 15): "63c67660a330b473b8930a6b506db5ca460163b704c0ffd5b57f78598bcb8e73",
    ("T3_navigate", 65): "8484f2abc9c258d49875cd51710e0a58cda3bd8c55dadda01ec751134dfe178b",
    ("T3_navigate", 74): "82f601358c5d3b3addb4fe6d93cec891a838a85891b437c9f8d642534c5b89d4",
    ("T3_navigate", 202): "3cbaeb8d6f33cfa0d065e009d44d106f159ca285c92d9d01694c2f17025175af",
    ("T3_navigate", 272): "1b5ddcb1fde878a6c83d0e30a70c054dadd7e9bfd952438fdfa882e05171c562",
    ("T3_navigate", 307): "f558faf02feae58b3ed492812bdf8f543037a47056c5d96b66ae8968e75eeb62",
    ("T3_navigate", 479): "36be15074e82eca78f2175ec51852a1dced6dc3de7bcfb6acb6181ab7428b25c",
}


def _fingerprint(trace):
    return hashlib.sha256(canonical([r["action"] for r in trace]).encode()).hexdigest()


class TestGoldenTraces(unittest.TestCase):
    def test_pin_seeds_match_golden_hashes(self):
        self.assertEqual(len(GOLDEN), 9)
        for (task, seed), want in sorted(GOLDEN.items()):
            trace = Agent().run_task(task, seed)
            self.assertTrue(trace[-1]["done"], "%s:%d" % (task, seed))
            self.assertEqual(_fingerprint(trace), want, "%s:%d" % (task, seed))


if __name__ == "__main__":
    unittest.main()
