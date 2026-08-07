#!/usr/bin/env python3
"""Run Raven Stop-hook tasks with one shared Codex payload."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPTS = ("codex-token-meter-write.py", "obsidian-log.py")


def run_script(script_dir: Path, script: str, payload: dict) -> None:
    """Run one Stop task fail-soft."""
    path = script_dir / script
    if not path.exists():
        return
    try:
        subprocess.run(
            ["python3", str(path)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            timeout=8,
            check=False,
        )
    except Exception:
        pass


def main() -> int:
    """Read hook stdin once and fan out to Stop tasks."""
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}

    script_dir = Path(__file__).resolve().parent
    for script in SCRIPTS:
        run_script(script_dir, script, payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
