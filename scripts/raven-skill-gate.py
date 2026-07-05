#!/usr/bin/env python3
"""
Raven — Deterministic Skill-Routing Gate

Raven's specialist routing used to be advisory-only ("MANDATORY: invoke X")
— injected context the model could ignore. This gate enforces the workflow
invariant at boundaries the host actually honors:

  • git pre-commit        — `raven-skill-gate.py --event commit` (exit 2 blocks)
  • Cursor hook           — `raven-skill-gate.py --cursor-hook` reads the
                            beforeShellExecution JSON on stdin and denies
                            `git commit` when no fresh marker exists
  • Codex MCP             — the raven MCP server exposes raven_gate_check

It does NOT classify prompts (a hook can't semantically detect "this was a
bug report"). It checks one fact: did a gated specialist skill actually run
this session? Skills prove it via raven-mark-skill.py, which appends to
.raven/state/skill-invocations.jsonl with a script-stamped timestamp.

Honest scope: this guarantees the skill RAN, not that its output was used
well. That residual gap is inherent to LLM systems.

Policy: .raven/state/routing-policy.json
  mode            shadow (log only) | soft (warn) | hard (block)
  gated_skills    markers that satisfy the gate (default andie, andie-jr)
  scope           globs of files the gate cares about (default code files)
  freshness_hours fallback window when session start is unknown (default 4)
  soft_until      ISO date — auto-set 7 days after first run; once past,
                  soft escalates to hard (same grace pattern as
                  architecture-guard)
  override_uses   tool calls allowed per override touch (default 5)

Escape hatch (audited, never silent):
  touch .raven/state/gate-override   → allows the next N gated actions,
  each one logged to docs/observations/security_log.md.

Local-only. Stdlib only. Designed to complete in <100ms.
"""

import fnmatch
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CWD = Path.cwd()
STATE_DIR = CWD / ".raven" / "state"
POLICY_FILE = STATE_DIR / "routing-policy.json"
MARKER_FILE = STATE_DIR / "skill-invocations.jsonl"
OVERRIDE_FILE = STATE_DIR / "gate-override"
OVERRIDE_COUNT = STATE_DIR / "gate-override.count"
SESSION_FILE = CWD / ".raven" / ".model-session.json"
SECURITY_LOG = CWD / "docs" / "observations" / "security_log.md"

DEFAULT_POLICY = {
    "mode": "soft",
    "gated_skills": ["andie", "andie-jr"],
    "scope": ["*.py", "src/**", "scripts/**", "*.js", "*.ts", "*.go",
              "*.java", "*.rs", "*.sql", "*.tf"],
    "freshness_hours": 4,
    "override_uses": 5,
}

BLOCK_MSG = (
    "BLOCKED by raven-skill-gate: no specialist skill invoked this session. "
    "Invoke the matching specialist (e.g. andie-jr for bugs, andie for "
    "design) before editing — its first step runs raven-mark-skill.py. "
    "Override: touch .raven/state/gate-override (logged)."
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def load_policy() -> dict:
    """Load routing policy; create the default (soft, 7-day grace) if absent."""
    if POLICY_FILE.exists():
        try:
            policy = {**DEFAULT_POLICY, **json.loads(POLICY_FILE.read_text())}
        except Exception:
            policy = dict(DEFAULT_POLICY)
    else:
        policy = dict(DEFAULT_POLICY)
        policy["soft_until"] = (_now() + timedelta(days=7)).isoformat()
        try:
            STATE_DIR.mkdir(parents=True, exist_ok=True)
            POLICY_FILE.write_text(json.dumps(policy, indent=2))
        except Exception:
            pass
    # Grace-period escalation: soft → hard after soft_until
    if policy.get("mode") == "soft" and policy.get("soft_until"):
        try:
            if _now() > datetime.fromisoformat(policy["soft_until"]):
                policy["mode"] = "hard"
                policy["escalated"] = True
        except Exception:
            pass
    return policy


def session_start() -> datetime:
    """Start of the current session (from session-start.py's session file),
    else None — callers fall back to the freshness window."""
    try:
        data = json.loads(SESSION_FILE.read_text())
        ts = data.get("session_started_at", "").rstrip("Z")
        return datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)
    except Exception:
        return None


def has_fresh_marker(policy: dict) -> bool:
    """True if any gated skill marker is newer than session start (fallback:
    now − freshness_hours)."""
    if not MARKER_FILE.exists():
        return False
    threshold = session_start() or (
        _now() - timedelta(hours=policy.get("freshness_hours", 4)))
    gated = set(policy.get("gated_skills", []))
    try:
        for line in MARKER_FILE.read_text().splitlines():
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get("skill") not in gated:
                continue
            ts = datetime.fromisoformat(rec.get("ts", ""))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts >= threshold:
                return True
    except Exception:
        return False
    return False


def in_scope(files: list, policy: dict) -> bool:
    """True if any file matches the policy scope globs."""
    globs = policy.get("scope", [])
    for f in files:
        f = f.lstrip("./")
        for g in globs:
            if fnmatch.fnmatch(f, g) or fnmatch.fnmatch(Path(f).name, g):
                return True
    return False


def staged_files() -> list:
    try:
        out = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, timeout=3)
        return [l for l in out.stdout.splitlines() if l.strip()]
    except Exception:
        return []


def log_event(kind: str, detail: str) -> None:
    """Append to the observation log (same channel task-observer uses)."""
    try:
        SECURITY_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(SECURITY_LOG, "a") as f:
            f.write(f"- {_now().isoformat()} · raven-skill-gate · {kind} · {detail}\n")
    except Exception:
        pass


def consume_override(policy: dict) -> bool:
    """If the override touch-file exists, allow this action, decrement the
    remaining-uses counter, and log it. Never silent."""
    if not OVERRIDE_FILE.exists():
        return False
    try:
        remaining = int(OVERRIDE_COUNT.read_text()) if OVERRIDE_COUNT.exists() \
            else int(policy.get("override_uses", 5))
    except Exception:
        remaining = int(policy.get("override_uses", 5))
    remaining -= 1
    log_event("OVERRIDE", f"gate-override consumed, {max(remaining, 0)} uses left")
    if remaining <= 0:
        OVERRIDE_FILE.unlink(missing_ok=True)
        OVERRIDE_COUNT.unlink(missing_ok=True)
    else:
        OVERRIDE_COUNT.write_text(str(remaining))
    return True


def check(files: list, event: str) -> int:
    """Core gate. Returns exit code: 0 allow, 2 block (hard mode only)."""
    policy = load_policy()
    mode = policy.get("mode", "soft")

    if mode not in ("shadow", "soft", "hard"):
        mode = "soft"

    if files and not in_scope(files, policy):
        return 0  # out of scope — docs etc. pass freely

    if has_fresh_marker(policy):
        return 0

    if consume_override(policy):
        print(f"⚠️ raven-skill-gate: override in effect ({event}) — logged.",
              file=sys.stderr)
        return 0

    detail = f"event={event} files={','.join(files[:5]) or '-'} mode={mode}"
    if mode == "shadow":
        log_event("SHADOW", detail)
        return 0
    if mode == "soft":
        log_event("SOFT-WARN", detail)
        print(f"⚠️ raven-skill-gate (soft): {BLOCK_MSG}", file=sys.stderr)
        return 0
    log_event("BLOCKED", detail)
    print(BLOCK_MSG, file=sys.stderr)
    return 2


def cursor_hook() -> int:
    """Cursor beforeShellExecution hook adapter. Reads the hook JSON from
    stdin; denies `git commit` when the gate would block. Cursor has no
    blocking pre-edit event, so the commit boundary is where hard mode bites;
    edits are observed via the soft/shadow log."""
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}
    command = payload.get("command", "") or ""
    if "git commit" not in command:
        print(json.dumps({"permission": "allow"}))
        return 0
    code = check(staged_files(), event="cursor-shell")
    if code == 2:
        print(json.dumps({
            "permission": "deny",
            "userMessage": "🪶 Raven skill gate: commit blocked — no specialist "
                           "skill ran this session.",
            "agentMessage": BLOCK_MSG,
        }))
    else:
        print(json.dumps({"permission": "allow"}))
    return 0  # the JSON verdict, not the exit code, carries the decision


def main() -> int:
    args = sys.argv[1:]
    if "--cursor-hook" in args:
        return cursor_hook()

    event = "edit"
    files = []
    i = 0
    while i < len(args):
        if args[i] == "--event" and i + 1 < len(args):
            event = args[i + 1]
            i += 2
        elif args[i] == "--file":
            i += 1
            while i < len(args) and not args[i].startswith("--"):
                files.append(args[i])
                i += 1
        else:
            i += 1

    if event == "commit" and not files:
        files = staged_files()
    return check(files, event)


if __name__ == "__main__":
    sys.exit(main())
