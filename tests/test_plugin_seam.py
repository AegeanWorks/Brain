"""Two mock LLM providers to prove the seam, without a network or a model.

The point of these tests is that *nothing here touches a real model*. A
provider is a class with `generate(observation)` and `identity()`; the
registry selects it by name; the conformance check validates it. That is the
whole contract, and it can be exercised completely offline.

`EchoProvider` is conforming. `AlternatingProvider` is deliberately not
deterministic — it is the control that proves the conformance check
discriminates rather than rubber-stamping.
"""

import unittest

from agent import Planner, model_label
from models.backend import ModelBackend, StubBackend
from models.conformance import check_backend, format_findings
from models.registry import BACKENDS, build, names, register

OBS = {"task": "T3_navigate", "x": 0, "y": 0, "steps": 0,
       "legal": ["up", "down", "left", "right", "wait"]}


class EchoProvider(ModelBackend):
    """Conforming mock: deterministic, identity declared, legal token."""

    def identity(self):
        return "mock:echo"

    def generate(self, observation):
        legal = observation.get("legal") or ["wait"]
        return legal[-1]


class AlternatingProvider(ModelBackend):
    """Non-deterministic control: same input, different output."""

    def __init__(self):
        self._n = 0

    def identity(self):
        return "mock:alternating"

    def generate(self, observation):
        self._n += 1
        legal = observation.get("legal") or ["wait"]
        return legal[self._n % len(legal)]


class TestPlugInSeam(unittest.TestCase):
    def test_a_new_provider_is_pluggable_without_touching_the_agent(self):
        register("mock-echo", EchoProvider)
        backend = build("mock-echo")
        self.assertIsInstance(backend, ModelBackend)
        self.assertEqual(backend.generate(OBS), "wait")

    def test_a_registered_provider_drives_the_planner(self):
        register("mock-echo-planner", EchoProvider)
        planner = Planner(backend=build("mock-echo-planner"))
        self.assertIs(planner.backend.__class__, EchoProvider)

    def test_the_header_pin_comes_from_the_provider(self):
        backend = EchoProvider()
        self.assertEqual(model_label(backend), "mock:echo")

    def test_the_pin_survives_a_class_rename(self):
        renamed = type("RenamedProvider", (EchoProvider,), {})
        self.assertEqual(model_label(renamed()), "mock:echo")

    def test_the_no_backend_label_is_unchanged(self):
        self.assertEqual(model_label(None), "rule")

    def test_the_stub_keeps_its_class_name_label(self):
        # StubBackend's identity is class-name derived, so `model_label`
        # deliberately rejects it and falls back — which keeps every
        # historical header written with "StubBackend" matching.
        self.assertEqual(model_label(StubBackend(["wait"])), "StubBackend")

    def test_the_conforming_mock_passes(self):
        report = check_backend(EchoProvider, OBS)
        self.assertTrue(report["ok"], report["findings"])
        self.assertEqual(report["identity"], "mock:echo")

    def test_the_non_deterministic_control_fails(self):
        report = check_backend(AlternatingProvider, OBS)
        self.assertFalse(report["ok"])
        self.assertIn("non-deterministic", report["findings"])

    def test_every_registered_provider_is_named(self):
        for name in names():
            self.assertIsInstance(name, str)
            self.assertTrue(name)

    def test_an_unknown_name_does_not_silently_default(self):
        with self.assertRaises(KeyError):
            build("definitely-not-registered")

    def test_the_report_renders_as_one_line(self):
        line = format_findings(check_backend(EchoProvider, OBS))
        self.assertIn("ok", line)
        self.assertIn("mock:echo", line)
        self.assertNotIn("\n", line)


if __name__ == "__main__":
    unittest.main()
