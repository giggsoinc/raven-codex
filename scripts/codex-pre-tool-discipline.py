#!/usr/bin/env python3
"""Codex PreToolUse discipline gate for Bash commands.

This hook blocks high-risk command patterns before they run. It is deliberately
small and deterministic; deeper checks still live in dedicated Raven scripts,
pre-commit, and CI.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


INSTALL_RE = re.compile(
    r"\b(pip\s+install|npm\s+install|yarn\s+add|pnpm\s+add|poetry\s+add|uv\s+add|cargo\s+add|go\s+get)\b",
    re.IGNORECASE,
)

RULES: list[tuple[re.Pattern[str], str, str]] = [
    (
        re.compile(r"\brm\s+(-[^\s]*r[^\s]*f|-[^\s]*f[^\s]*r)\b|\brm\s+-rf\b", re.IGNORECASE),
        "destructive-delete",
        "Raven blocks recursive force deletes from agent shell hooks. Use an explicit reviewed command with approval.",
    ),
    (
        re.compile(r"\bgit\s+reset\s+--hard\b|\bgit\s+clean\s+-[^\n]*f", re.IGNORECASE),
        "destructive-git",
        "Raven blocks destructive git cleanup from agent shell hooks. Preserve user work unless explicitly approved.",
    ),
    (
        re.compile(r"\bgit\s+push\s+--force(?:-with-lease)?\b", re.IGNORECASE),
        "force-push",
        "Raven blocks force push from agent shell hooks. Use a reviewed approval path for history rewrites.",
    ),
    (
        re.compile(r"\b0\.0\.0\.0\b"),
        "public-bind",
        "Raven blocks opening services on 0.0.0.0 from agent shell hooks. Bind localhost unless explicitly reviewed.",
    ),
]


def audit(rule: str, command: str) -> None:
    """Write a local audit entry; never raise from a hook."""
    try:
        audit_dir = Path(".raven/audit")
        audit_dir.mkdir(parents=True, exist_ok=True)
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": "guard_block",
            "guard": "codex-pre-tool-discipline",
            "rule": rule,
            "command": command[:300],
        }
        with open(audit_dir / f"{date}.log", "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def block(rule: str, reason: str, command: str) -> None:
    """Emit a Codex hook block response."""
    audit(rule, command)
    print(json.dumps({
        "continue": False,
        "stopReason": (
            f"RAVEN DISCIPLINE BLOCK — {rule}\n\n"
            f"{reason}\n\n"
            f"Command:\n  {command[:300]}"
        ),
    }))


def main() -> int:
    """Read Codex hook payload and block unsafe Bash commands."""
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    command = payload.get("tool_input", {}).get("command", "")
    if not command:
        return 0

    for pattern, rule, reason in RULES:
        if pattern.search(command):
            block(rule, reason, command)
            return 0

    if INSTALL_RE.search(command) and "[RAVEN:CVE-CHECKED]" not in command:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": (
                    "Raven dependency discipline: install command detected. "
                    "Run raven_cve_check for each new package before relying on it. "
                    "To mark a reviewed install command, include [RAVEN:CVE-CHECKED]."
                ),
            }
        }))

    return 0


if __name__ == "__main__":
    sys.exit(main())
