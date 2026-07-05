#!/usr/bin/env python3
"""Raven routing matrix — 9 cases proving triage-router and architect-router
are mutually exclusive (no double-fire, no missed route).

Loads both routers via importlib (hyphenated filenames) and asserts which
router claims each prompt class. Brownfield/greenfield is forced by patching
is_brownfield, so the test is repo-state independent.
"""

import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))


def _load(name: str):
    spec = importlib.util.spec_from_file_location(
        name.replace("-", "_"), SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


triage = _load("triage-router")
architect = _load("architect-router")
import router_common  # noqa: E402


def routes(prompt: str, brownfield: bool):
    """Return (triage_target, architect_fires) for a prompt."""
    orig = triage.is_brownfield
    triage.is_brownfield = lambda _r=".": brownfield
    try:
        forced = router_common.force_intent(prompt)
        if forced == "andie-jr":
            t = "andie-jr"
        elif forced == "andie":
            t = None
        else:
            t = triage.classify(prompt)
        a = (forced == "andie") or (
            forced != "andie-jr" and architect.classify(prompt))
        return t, bool(a)
    finally:
        triage.is_brownfield = orig


class TestRoutingMatrix(unittest.TestCase):
    def test_1_symptom_brownfield_jr_only(self):
        t, a = routes("the login endpoint is failing with a 500 error", True)
        self.assertEqual(t, "andie-jr")
        self.assertFalse(a)

    def test_2_decision_andie_only(self):
        t, a = routes("should we use Postgres or MongoDB for the new service?", True)
        self.assertIsNone(t)
        self.assertTrue(a)

    def test_3_brownfield_default_jr(self):
        t, a = routes("update the retry logic in the payment worker", True)
        self.assertEqual(t, "andie-jr")
        self.assertFalse(a)

    def test_4_data_only_none(self):
        t, a = routes("show me the list of endpoints in this service", True)
        self.assertIsNone(t)
        self.assertFalse(a)

    def test_5_trivial_none(self):
        t, a = routes("rename this variable to user_id", True)
        self.assertIsNone(t)
        self.assertFalse(a)

    def test_6_symptom_overrides_data(self):
        t, a = routes("why is the auth service failing since yesterday?", True)
        self.assertEqual(t, "andie-jr")
        self.assertFalse(a)

    def test_7_decision_plus_brownfield_andie_only(self):
        t, a = routes("design the architecture for our multi-tenant billing system", True)
        self.assertIsNone(t)
        self.assertTrue(a)

    def test_8_force_jr_exclusive(self):
        t, a = routes("/andie-jr the cache layer", True)
        self.assertEqual(t, "andie-jr")
        self.assertFalse(a)

    def test_9_force_andie_exclusive(self):
        t, a = routes("/andie plan the data model", True)
        self.assertIsNone(t)
        self.assertTrue(a)


if __name__ == "__main__":
    unittest.main()
