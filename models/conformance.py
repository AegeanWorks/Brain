"""Check a provider against the backend contract, without reading its code.

A pluggable seam is only worth having if a new provider can be *validated*.
This module exercises a provider class and reports what it observed, in the
same report-with-findings shape the evidence batteries use.

The checks, and why each one is here:

  ``identity-from-class-name``  the provider never declared an identity, so
                                a class rename would invalidate every
                                historical header pin.
  ``non-string``               ``generate`` returned something that is not a
                                token, so the planner cannot compare it.
  ``no-proposal``              ``generate`` returned ``None``; legal only
                                when the provider means "no proposal", which
                                the caller cannot distinguish from a fault.
  ``raises``                   ``generate`` raised. Raising is the contract
                                for faults, so this is reported rather than
                                treated as a failure of the backend — a
                                provider that raises is conforming *if* the
                                caller counts the fallback. It is recorded
                                so a caller knows what to expect.
  ``illegal-token``            the token is not in the observation's legal
                                set; the planner would reject it anyway, and
                                a provider that only proposes illegal tokens
                                is not usable.
  ``non-deterministic``        two calls with the same observation differ.
                                Determinism is the protocol requirement that
                                makes replay verification possible at all.

A provider is *conformant* when it declares its identity, returns a legal
string token (or raises), and repeats itself. Note what is deliberately not
asserted: that a real language model reproduces byte-identical output across
processes. Temperature and batching make that false in practice, so a
provider backed by a live model should be checked through a replay transport.
"""

from models.backend import ModelBackend

_FALLBACK_MODULES = ("backend",)


def check_backend(provider, observation, calls=2):
    """Exercise ``provider`` and return ``ok`` plus named findings.

    ``provider`` is a ready backend instance, or a class — a class is
    instantiated with no arguments, which is how ``StubBackend`` is checked.
    """
    if isinstance(provider, type):
        class_name = provider.__name__
        try:
            instance = provider(_check_script()) if _needs_script(provider) \
                else provider()
        except TypeError:
            return {
                "ok": False, "identity": None, "deterministic": None,
                "findings": ["cannot-construct:%s" % class_name],
            }
    else:
        instance = provider
        class_name = type(provider).__name__

    findings = []

    identity = instance.identity()
    if not isinstance(identity, str) or not identity:
        findings.append("identity-missing")
    else:
        # A provider that embeds its class name in its declared identity is
        # rename-fragile no matter which prefix it uses, not just when the
        # prefix happens to be the instance's module basename. This mirrors
        # ``agent.model_label``, which rejects any label ending in the class
        # name so a class rename cannot silently invalidate a historical pin.
        if identity.endswith(type(instance).__name__):
            findings.append("identity-from-class-name")

    proposals = []
    deterministic = None
    for _ in range(calls):
        try:
            proposals.append(instance.generate(dict(observation)))
        except Exception as exc:
            findings.append("raises:%s" % type(exc).__name__)
            deterministic = True
            break

    if len(proposals) == calls:
        deterministic = len({repr(p) for p in proposals}) == 1
        if not deterministic:
            findings.append("non-deterministic")

    for proposal in proposals:
        if proposal is None:
            findings.append("no-proposal")
        elif not isinstance(proposal, str):
            findings.append("non-string:%s" % type(proposal).__name__)
        elif (observation.get("legal")
              and proposal not in observation["legal"]):
            findings.append("illegal-token:%s" % proposal)

    # ``raises`` describes expected behaviour, not a contract violation, so
    # it is reported in findings but does not by itself make ok false.
    # Repeated findings collapse: two identical calls should read once.
    findings = list(dict.fromkeys(findings))
    blocking = [f for f in findings if not f.startswith("raises:")]
    return {
        "ok": not blocking,
        "identity": identity,
        "deterministic": deterministic,
        "findings": findings,
    }


def _needs_script(provider):
    """True when the provider is StubBackend-like and needs a script list."""
    return provider.__name__ == "StubBackend"


def _check_script():
    return ["wait", "wait", "wait"]


def format_findings(report):
    """Render a conformance report as one line, for battery output."""
    status = "ok" if report["ok"] else "FAIL"
    detail = ", ".join(report["findings"]) or "conforming"
    return "%s %s (%s)" % (status, report["identity"], detail)
