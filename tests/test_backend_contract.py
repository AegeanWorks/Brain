"""A backend seam is only pluggable if a provider can be checked, not read.

`ModelBackend` is already an ABC with one method, and `LlamaCppBackend`
implements it. What is missing is everything that makes a seam *usable*:

  * no registry, so nothing can select a provider by name and an unknown
    name has no defined behaviour;
  * no stable identity, so `model_label()` guesses from `model_path` and
    falls back to `type(backend).__name__` — renaming the class silently
    changes every historical pin;
  * no conformance contract, so a new provider can only be validated by
    reading its code.

These tests pin the contract a provider must meet:

  * `identity()` is a stable, non-empty string that does not change when the
    class is renamed;
  * the registry builds by name and **raises** on an unknown name rather
    than falling back;
  * a provider is deterministic when its transport is;
  * a raising transport propagates, so the caller can count the fallback;
  * a provider that returns a non-string or an illegal token is detectable
    by the conformance check rather than silently accepted.
"""

import unittest

from models.backend import ModelBackend, StubBackend
from models.conformance import check_backend
from models.registry import BACKENDS, build, register


class _Echo(ModelBackend):
    """Minimal conforming provider: returns the first legal token."""

    def identity(self):
        return "echo:test"

    def generate(self, observation):
        legal = observation.get("legal") or ["wait"]
        return legal[0]


class _NoIdentity(ModelBackend):
    def generate(self, observation):
        return "wait"


class _Raising(ModelBackend):
    def identity(self):
        return "raising:test"

    def generate(self, observation):
        raise RuntimeError("transport down")


class _ReturnsNone(ModelBackend):
    def identity(self):
        return "none:test"

    def generate(self, observation):
        return None


class _ReturnsInt(ModelBackend):
    def identity(self):
        return "int:test"

    def generate(self, observation):
        return 3


OBS = {"task": "T3_navigate", "x": 0, "y": 0, "steps": 0,
       "legal": ["up", "down", "left", "right", "wait"]}


class TestBackendContract(unittest.TestCase):
    def test_the_abc_requires_generate(self):
        with self.assertRaises(TypeError):
            ModelBackend()

    def test_identity_is_part_of_the_protocol(self):
        # A provider that does not override identity still gets a usable
        # one, but the base must declare it so implementations override it.
        self.assertTrue(hasattr(ModelBackend, "identity"))
        self.assertEqual(StubBackend(["wait"]).identity(),
                         "stub:%s" % StubBackend.__name__)

    def test_identity_survives_a_class_rename(self):
        # The pin must come from the provider, not from the class name.
        renamed = type("SomethingElseEntirely", (_Echo,),
                       {"identity": lambda self: "echo:test"})
        self.assertEqual(renamed().identity(), "echo:test")

    def test_a_conforming_provider_passes(self):
        report = check_backend(_Echo, OBS)
        self.assertTrue(report["ok"], report["findings"])
        self.assertEqual(report["identity"], "echo:test")

    def test_a_missing_identity_is_named(self):
        report = check_backend(_NoIdentity, OBS)
        self.assertFalse(report["ok"])
        self.assertIn("identity-from-class-name", report["findings"])

    def test_a_raising_provider_is_reported_not_swallowed(self):
        # Raising is the *contract* for a fault, so it does not make the
        # provider non-conforming; it must be reported so the caller knows
        # to count a fallback rather than silently trusting a proposal.
        report = check_backend(_Raising, OBS)
        self.assertTrue(report["ok"], report["findings"])
        self.assertTrue(any("raises" in f for f in report["findings"]))

    def test_a_none_proposal_is_named(self):
        report = check_backend(_ReturnsNone, OBS)
        self.assertFalse(report["ok"])
        self.assertTrue(any("no-proposal" in f for f in report["findings"]))

    def test_a_non_string_proposal_is_named(self):
        report = check_backend(_ReturnsInt, OBS)
        self.assertFalse(report["ok"])
        self.assertTrue(any("non-string" in f for f in report["findings"]))

    def test_determinism_is_checked(self):
        report = check_backend(_Echo, OBS)
        self.assertTrue(report["deterministic"])

    def test_the_registry_builds_a_known_provider(self):
        backend = build("stub", script=["wait"])
        self.assertIsInstance(backend, StubBackend)

    def test_an_unknown_name_raises_and_names_the_choices(self):
        with self.assertRaises(KeyError) as ctx:
            build("no-such-backend")
        self.assertIn("no-such-backend", str(ctx.exception))
        self.assertIn("stub", str(ctx.exception))

    def test_registering_a_duplicate_raises(self):
        with self.assertRaises(ValueError):
            register("stub", StubBackend)

    def test_the_registry_names_what_it_has(self):
        self.assertIn("stub", BACKENDS)
        self.assertIn("llamacpp", BACKENDS)


if __name__ == "__main__":
    unittest.main()
