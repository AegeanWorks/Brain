"""One exit-code contract for the eval batteries.

Most batteries already refuse malformed input by raising, but a battery
that merely *prints* a bad number exits 0, so a scripted gate cannot tell a
healthy run from a regressed one. Ten shipped batteries had no ``assert``,
``raise`` or non-zero exit at all; measured, ``python -m evals.telemetry_lock``
exits 0 both intact and with ``--ablate``, the deliberately broken case.

This module is the shared contract: a battery passes a list of findings and
exits with ``exit_code_for(findings)``. An empty list is 0; any finding is 1.
``audit_batteries`` reports which modules have adopted the contract, so the
gap is visible instead of being rediscovered by reading each file.

Pure functions plus one read-only directory scan; no battery is imported.
"""

import ast
from pathlib import Path

#: Exit code for a battery with no findings.
EXIT_OK = 0
#: Exit code for a battery reporting at least one failed claim.
EXIT_FINDING = 1

#: Names a module must reference to count as adopting the contract.
CONTRACT_MARKERS = ("battery_result", "exit_code_for")

#: Pure libraries/helpers that are not batteries by design.
LIBRARY_MODULES = frozenset({
    "estimators", "lesion_audit", "module_state", "pair_scan",
    "phi_diagnosis", "recompute", "replication", "synergy_null",
    "vector_audit",
})


def exit_code_for(findings):
    """Return the process exit code for one battery's findings."""
    return EXIT_FINDING if findings else EXIT_OK


def battery_result(name, findings, payload=None):
    """Build one battery's report: name, ok flag, findings and payload."""
    findings = list(findings or [])
    return {
        "battery": name,
        "ok": not findings,
        "findings": findings,
        "payload": payload if payload is not None else {},
    }


def format_findings(name, findings):
    """Render findings as one attributable line each, for stderr."""
    return "".join("%s: FAIL %s\n" % (name, finding) for finding in findings)


def _adopts_contract(source):
    """True when a module's source references the contract by name."""
    return any(marker in source for marker in CONTRACT_MARKERS)


def _refuses_by_raising(tree):
    """True when the module contains an explicit ``raise`` statement."""
    return any(isinstance(node, ast.Raise) for node in ast.walk(tree))


def audit_batteries(root):
    """Report which eval modules adopt the exit-code contract.

    A module counts as covered when its source references the contract or
    when it can at least refuse bad input by raising. The rest only print,
    so a regression there is invisible to a scripted gate.
    """
    directory = Path(root) / "evals"
    with_contract, without_contract, libraries = [], [], []
    if not directory.is_dir():
        return {"total": 0, "with_contract": [], "without_contract": [],
                "libraries": [], "contract": list(CONTRACT_MARKERS)}
    for path in sorted(directory.glob("*.py")):
        if path.stem == "__init__":
            continue
        if path.stem in LIBRARY_MODULES:
            libraries.append(path.stem)
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:
            without_contract.append(path.stem)
            continue
        covered = _adopts_contract(source)
        if not covered:
            try:
                covered = _refuses_by_raising(ast.parse(source))
            except SyntaxError:
                covered = False
        (with_contract if covered else without_contract).append(path.stem)
    return {
        "total": len(with_contract) + len(without_contract) + len(libraries),
        "with_contract": with_contract,
        "without_contract": without_contract,
        "libraries": libraries,
        "contract": list(CONTRACT_MARKERS),
    }


def main():
    """Print the audit; exit 1 when any battery lacks a self-check."""
    import sys

    root = Path(__file__).resolve().parent.parent
    report = audit_batteries(root)
    print("batteries: %d, libraries: %d, with a self-check: %d, none: %d"
          % (len(report["with_contract"]) + len(report["without_contract"]),
             len(report["libraries"]), len(report["with_contract"]),
             len(report["without_contract"])))
    for name in report["libraries"]:
        print("  LIBRARY: %s" % name)
    for name in report["without_contract"]:
        print("  NO SELF-CHECK: %s" % name)
    sys.exit(exit_code_for(report["without_contract"]))


if __name__ == "__main__":
    main()
