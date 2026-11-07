# Brain

[![Built with AIKit](https://img.shields.io/badge/built%20with-AIKit-6f42c1)](https://github.com/AegeanWorks/AIKit)

Deterministic agent substrate with memory planner self-model and integration telemetry plus ablation harness.

## ⚡ 30-Second Cold-Start Quick Reference

- **Runtime Prerequisites**: Python 3.10+ stdlib only, no third-party packages.
- **Canonical Regression Shield Gate**:
  ```bash
  python -m unittest discover -s tests -t .
  ```

### 🛠️ AIKit Commands (run from the AIKit folder)
| Role | Command |
|---|---|
| Status, task and gates | `python aikit.py status brain` |
| Phase 4: every gate | `python aikit.py check brain` |
| Repair memory and map, then check | `python aikit.py fix brain` |
| Resume an interrupted task | `python aikit.py resume brain` |

## 📦 What's Inside

```text
brain/
├── agent.py                  <- rule-based perceive-plan-act-observe loop + hub
├── memory/store.py           <- SQLite FTS5 persistent store (WAL, fsync)
├── planner/plan.py           <- explicit steps + recover
├── self_model/model.py       <- budget/error/confidence counters
├── worlds/grid.py            <- deterministic 8x8 fixed-step tasks T1-T3
├── telemetry/log.py          <- JSONL append-only, fsync before exec
├── telemetry/ablate.py       <- hub_zero / lesion / shuffle (pure)
├── evals/estimators.py       <- MI, Phi_AR, SYN, GBI, k, gain, recovery, null
├── evals/recompute.py        <- independent recompute from logs (--log)
├── evals/tasks.yaml          <- pinned tasks, Vc, windows, seeds
├── evals/verdict.json        <- UNKNOWN, no claim drafted
├── tests/                    <- unittest gate, tempdir only
```

## 📜 License

Free for personal use under the Aegean License 1.1 (AL-1.1); see [LICENSE](LICENSE). Any commercial use needs the Aegean Commercial License 1.0 (ACL-1.0); see [COMMERCIAL.md](COMMERCIAL.md).
