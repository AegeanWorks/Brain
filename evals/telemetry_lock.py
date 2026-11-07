"""Concurrent telemetry battery: serialized append vs lock-off ablation.

Two or more writers start together, each reads the head and then sleeps
briefly before appending. With the advisory lock the second writer reads
the first writer's digest and the chain verifies; with the lock removed
both link to the same stale head and verify_chain reports a broken link.
No logs are committed: each run uses a temporary directory.
"""

import argparse
import contextlib
import json
import os
import tempfile
import threading
import time
from unittest import mock

from telemetry.log import Telemetry, verify_chain


@contextlib.contextmanager
def _no_lock(_path, timeout_seconds=0.0):
    yield


def run_battery(writers=2, records=2, ablate=False):
    """Run concurrent writers and return the chain verdict."""
    errors = []
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "run.jsonl")
        barrier = threading.Barrier(writers)
        real_head = Telemetry._head_digest

        def slowed_head(tel):
            head = real_head(tel)
            time.sleep(0.1)
            return head

        def writer(index):
            tel = Telemetry(path)
            try:
                barrier.wait(timeout=10)
                for seq in range(records):
                    tel.append_action(seq, "concurrent", {"writer": index})
            except Exception as exc:  # hygiene: allow worker failure is reported in the JSON
                errors.append("%s: %s" % (type(exc).__name__, exc))

        with mock.patch.object(Telemetry, "_head_digest", slowed_head):
            if ablate:
                with mock.patch("telemetry.log._append_lock", _no_lock):
                    threads = [threading.Thread(target=writer, args=(i,))
                               for i in range(writers)]
                    for thread in threads:
                        thread.start()
                    for thread in threads:
                        thread.join(timeout=20)
            else:
                threads = [threading.Thread(target=writer, args=(i,))
                           for i in range(writers)]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join(timeout=20)
        result = verify_chain(path)
        return {
            "writers": writers,
            "records_per_writer": records,
            "expected_records": writers * records,
            "ablate": bool(ablate),
            "worker_errors": errors,
            "chain_ok": bool(result["ok"]),
            "chain_findings": result["findings"],
            "chain_records": result["records"],
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--writers", type=int, default=2)
    parser.add_argument("--records", type=int, default=2)
    parser.add_argument("--ablate", action="store_true",
                        help="remove the advisory lock (pre-fix behavior)")
    args = parser.parse_args()
    print(json.dumps(run_battery(args.writers, args.records, args.ablate),
                     indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
