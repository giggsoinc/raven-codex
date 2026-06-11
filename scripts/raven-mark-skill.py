#!/usr/bin/env python3
"""
Raven — Skill Invocation Marker

Appends one JSON line {ts, skill, session_id} to
.raven/state/skill-invocations.jsonl. Each gated skill's SKILL.md instructs
the model to run this as its FIRST step:

    python3 <scripts-dir>/raven-mark-skill.py andie-jr

The SCRIPT stamps the timestamp — the model cannot back-date a marker.
raven-skill-gate.py reads this file to decide whether a specialist actually
ran before code is committed.

Local-only. No telemetry. Stdlib only, <10ms.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

STATE_DIR = Path.cwd() / ".raven" / "state"
MARKER_FILE = STATE_DIR / "skill-invocations.jsonl"


def session_id() -> str:
    """Best-available session identity: Codex session env, else parent PID."""
    return (os.environ.get("CODEX_SESSION_ID")
            or os.environ.get("CURSOR_SESSION_ID")
            or f"ppid-{os.getppid()}")


def mark(skill: str) -> dict:
    """Append a marker line for `skill`; returns the record written."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "skill": skill,
        "session_id": session_id(),
    }
    with open(MARKER_FILE, "a") as f:
        f.write(json.dumps(record) + "\n")
    return record


def main() -> int:
    if len(sys.argv) != 2 or not sys.argv[1].strip():
        print("usage: raven-mark-skill.py <skill-name>", file=sys.stderr)
        return 1
    skill = sys.argv[1].strip()
    record = mark(skill)
    print(f"🪶 Raven marker · {skill} invoked at {record['ts']} "
          f"(session {record['session_id']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
