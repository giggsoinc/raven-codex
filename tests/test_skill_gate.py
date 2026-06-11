#!/usr/bin/env python3
"""raven-skill-gate regression suite — the 6 contract cases:

(a) edit blocked when no marker (hard mode)
(b) edit allowed after raven-mark-skill.py runs
(c) stale marker (older than session start) blocks
(d) shadow mode never blocks but logs
(e) override touch-file allows and logs (with countdown)
(f) gate completes in <100ms

Each test runs in a fresh temp project dir; the gate module is re-loaded per
test because its paths bind to CWD at import.
"""

import importlib.util
import json
import os
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def load(name: str):
    spec = importlib.util.spec_from_file_location(
        name.replace("-", "_"), SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write_policy(mode: str):
    state = Path(".raven/state")
    state.mkdir(parents=True, exist_ok=True)
    (state / "routing-policy.json").write_text(json.dumps({
        "mode": mode,
        "gated_skills": ["andie", "andie-jr"],
        "scope": ["*.py", "src/**"],
        "freshness_hours": 4,
        "override_uses": 2,
    }))


class GateCase(unittest.TestCase):
    def setUp(self):
        self._old = os.getcwd()
        self.tmp = tempfile.mkdtemp()
        os.chdir(self.tmp)

    def tearDown(self):
        os.chdir(self._old)

    def test_a_blocked_without_marker(self):
        write_policy("hard")
        gate = load("raven-skill-gate")
        self.assertEqual(gate.check(["src/app.py"], "edit"), 2)

    def test_b_allowed_after_marker(self):
        write_policy("hard")
        marker = load("raven-mark-skill")
        marker.mark("andie-jr")
        gate = load("raven-skill-gate")
        self.assertEqual(gate.check(["src/app.py"], "edit"), 0)

    def test_c_stale_marker_blocks(self):
        write_policy("hard")
        # Session started now; marker is from before the session.
        Path(".raven").mkdir(exist_ok=True)
        Path(".raven/.model-session.json").write_text(json.dumps({
            "session_started_at": datetime.now(timezone.utc).isoformat()}))
        state = Path(".raven/state")
        state.mkdir(parents=True, exist_ok=True)
        stale_ts = (datetime.now(timezone.utc) - timedelta(hours=9)).isoformat()
        (state / "skill-invocations.jsonl").write_text(
            json.dumps({"ts": stale_ts, "skill": "andie-jr", "session_id": "x"}) + "\n")
        gate = load("raven-skill-gate")
        self.assertEqual(gate.check(["src/app.py"], "edit"), 2)

    def test_d_shadow_never_blocks_but_logs(self):
        write_policy("shadow")
        gate = load("raven-skill-gate")
        self.assertEqual(gate.check(["src/app.py"], "edit"), 0)
        log = Path("docs/observations/security_log.md")
        self.assertTrue(log.exists())
        self.assertIn("SHADOW", log.read_text())

    def test_e_override_allows_and_logs(self):
        write_policy("hard")
        Path(".raven/state/gate-override").touch()
        gate = load("raven-skill-gate")
        self.assertEqual(gate.check(["src/app.py"], "edit"), 0)  # use 1 of 2
        log = Path("docs/observations/security_log.md")
        self.assertIn("OVERRIDE", log.read_text())
        self.assertEqual(gate.check(["src/app.py"], "edit"), 0)  # use 2 of 2
        # allowance exhausted → override file consumed → next call blocks
        self.assertFalse(Path(".raven/state/gate-override").exists())
        self.assertEqual(gate.check(["src/app.py"], "edit"), 2)

    def test_f_gate_under_100ms(self):
        write_policy("hard")
        gate = load("raven-skill-gate")
        start = time.perf_counter()
        gate.check(["src/app.py"], "edit")
        elapsed = time.perf_counter() - start
        self.assertLess(elapsed, 0.1, f"gate took {elapsed * 1000:.1f}ms")

    def test_out_of_scope_passes(self):
        write_policy("hard")
        gate = load("raven-skill-gate")
        self.assertEqual(gate.check(["docs/readme.md"], "edit"), 0)


if __name__ == "__main__":
    unittest.main()
