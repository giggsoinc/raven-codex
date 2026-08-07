#!/usr/bin/env python3
"""Routing honesty tests for chat-capable and premium model safeguards."""

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def load_script(name: str):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name.replace("-", "_")] = mod
    spec.loader.exec_module(mod)
    return mod


class RoutingHonestyCase(unittest.TestCase):
    def setUp(self):
        self.old = os.getcwd()
        self.tmp = tempfile.mkdtemp()
        os.chdir(self.tmp)

    def tearDown(self):
        os.chdir(self.old)

    def test_model_router_rejects_embedding_models(self):
        router = load_script("codex-model-router")

        ok, problems = router.validate_routing({
            "LOCAL_ONLY": "ollama/dolphin-mistral",
            "SIMPLE": "openai/text-embedding-3-small",
            "MEDIUM": "openai/gpt-4o",
            "COMPLEX": "openai/gpt-4o",
        })

        self.assertFalse(ok)
        self.assertTrue(any("not a chat-generation model" in p for p in problems))

    def test_model_router_sanitizes_premium_without_opt_in(self):
        router = load_script("codex-model-router")

        clean = router.sanitize_routing({
            "LOCAL_ONLY": "ollama/dolphin-mistral",
            "SIMPLE": "openai/gpt-4o-mini",
            "MEDIUM": "openai/gpt-4o",
            "COMPLEX": "openai/o1",
        }, allow_premium=False)

        self.assertEqual(clean["COMPLEX"], "openai/gpt-4o")

    def test_session_start_discloses_validation_and_active_model(self):
        session_start = load_script("codex-session-start")

        payload = json.dumps({"model": "gpt-5-codex"})
        with mock.patch.object(sys, "stdin", StringIO(payload)):
            with mock.patch.object(sys, "stdout", StringIO()) as stdout:
                session_start.main()

        output = json.loads(stdout.getvalue())
        context = output["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Validation → PASS", context)
        self.assertIn("Active     → gpt-5-codex", context)
        self.assertIn("cannot silently switch", context)


if __name__ == "__main__":
    unittest.main()
