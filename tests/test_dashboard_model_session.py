#!/usr/bin/env python3
"""Dashboard compatibility for token meter session schemas."""

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def load_dashboard():
    spec = importlib.util.spec_from_file_location("codex_dashboard", SCRIPTS / "codex-dashboard.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["codex_dashboard"] = mod
    spec.loader.exec_module(mod)
    return mod


class DashboardSessionCase(unittest.TestCase):
    def setUp(self):
        self.old = os.getcwd()
        self.tmp = tempfile.mkdtemp()
        os.chdir(self.tmp)

    def tearDown(self):
        os.chdir(self.old)

    def test_raven_code_schema_reads_as_raven_overhead(self):
        Path(".raven").mkdir()
        Path(".raven/.model-session.json").write_text(json.dumps({
            "session_started_at": "2026-08-07T00:00:00+00:00",
            "raven_code": {"tokens": 10, "cost_usd": 0.01, "calls": 1},
            "user_work": {"tokens": 20, "cost_usd": 0.02, "calls": 2},
        }))

        dashboard = load_dashboard()
        metrics = dashboard.aggregate(days=1)

        self.assertEqual(metrics["last_session"]["raven_overhead"]["tokens"], 10)
        self.assertEqual(metrics["last_session"]["user_work"]["tokens"], 20)
        self.assertEqual(metrics["last_session"]["tokens"], 30)


if __name__ == "__main__":
    unittest.main()
