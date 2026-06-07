#!/usr/bin/env python3
"""Raven — PR Gate v1.1.

Orchestrates manifest validation + secret detection + CVE scan for CI.
Called by the Raven GitHub Action on every PR.

Exit codes:
  0 = all checks passed
  1 = hard block (secret or critical CVE)
  2 = manifest missing or invalid (did not run — treated as neutral by the action)
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

MANIFEST_PATH = os.environ.get("RAVEN_MANIFEST_PATH", ".raven/manifest.json")
SCRIPTS_DIR = Path(__file__).parent
BASE_REF = os.environ.get("GITHUB_BASE_REF", "main")
results = {"manifest": "skipped", "secrets": "skipped", "cve": "skipped", "audit": "skipped"}


def run(script: str, extra_args=None):
    """Run a sibling Raven script and return (returncode, combined_output)."""
    path = SCRIPTS_DIR / script
    if not path.exists():
        return 2, f"{script} not found"
    r = subprocess.run(["python3", str(path)] + (extra_args or []),
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def banner(icon: str, label: str, detail: str = "") -> None:
    """Print a GitHub-status-style banner line."""
    print(f"{icon} raven/{label}{(' — ' + detail) if detail else ''}")


def changed_files():
    """Return PR-changed files (added/copied/modified) vs the base ref."""
    r = subprocess.run(["git", "diff", "--name-only", "--diff-filter=ACM",
                        f"origin/{BASE_REF}...HEAD"], capture_output=True, text=True)
    return [f for f in r.stdout.split() if f]


def changed_libraries():
    """Parse newly-added `name==version` lines from changed requirements files."""
    libs = []
    for rf in (f for f in changed_files() if Path(f).name in ("requirements.txt", "requirements.in")):
        d = subprocess.run(["git", "diff", f"origin/{BASE_REF}...HEAD", "--", rf],
                           capture_output=True, text=True)
        for line in d.stdout.splitlines():
            if not line.startswith("+") or line.startswith("+++"):
                continue
            spec = line[1:].split("#")[0].strip()
            m = re.match(r"^([A-Za-z0-9._-]+)\s*(?:==\s*([0-9][\w.\-]*))?", spec)
            if m and m.group(1):
                libs.append((m.group(1).lower(), m.group(2) or ""))
    return libs


def check_manifest():
    """Validate manifest presence and required fields; exit 2 if it cannot run."""
    if not Path(MANIFEST_PATH).exists():
        banner("⚠️ ", "discipline-check", "did not run — manifest missing")
        print(f"   Run raven-setup in your project to create {MANIFEST_PATH}")
        sys.exit(2)
    try:
        manifest = json.loads(Path(MANIFEST_PATH).read_text())
    except (json.JSONDecodeError, OSError) as e:
        banner("⚠️ ", "discipline-check", f"did not run — manifest invalid: {e}")
        sys.exit(2)
    missing = [k for k in ("project", "stack", "owner") if k not in manifest]
    if missing:
        banner("⚠️ ", "discipline-check", f"did not run — manifest missing fields: {missing}")
        sys.exit(2)
    results["manifest"] = "passed"
    print(f"✅ manifest.json valid — project: {manifest.get('project')} stack: {manifest.get('stack')}")


def check_secrets():
    """Run the secret scanner in PR mode; hard-block on detection."""
    code, out = run("secret-scan.py", ["--pr"])
    print(out.strip())
    if code != 0:
        results["secrets"] = "blocked"
        banner("🔴", "discipline-check", "blocked — secret detected in changed files")
        sys.exit(1)
    results["secrets"] = "passed"


def check_cve():
    """Scan each newly-added dependency; hard-block on a critical CVE (exit 1)."""
    libs = changed_libraries()
    if not libs:
        results["cve"] = "passed"
        print("✅ no new dependencies to scan")
        return
    blocked = []
    for lib, ver in libs:
        code, out = run("cve-check.py", ["--library", lib] + (["--version", ver] if ver else []))
        print(out.strip())
        if code == 1:  # hard block (critical CVE) — see cve-check.py exit codes
            blocked.append(f"{lib}=={ver}" if ver else lib)
    if blocked:
        results["cve"] = "blocked"
        banner("🔴", "discipline-check", f"blocked — critical CVE in: {', '.join(blocked)}")
        sys.exit(1)
    results["cve"] = "passed"


def write_audit():
    """Record a passed PR-gate event to the audit log (best-effort)."""
    run("audit-log.py", ["--event", "pr-gate",
                         "--pr", os.environ.get("GITHUB_PR_NUMBER", "unknown"),
                         "--actor", os.environ.get("GITHUB_ACTOR", "unknown"),
                         "--result", "passed"])
    results["audit"] = "written"


def main():
    """Run the full PR gate in order, exiting non-zero on the first hard block."""
    check_manifest()
    check_secrets()
    check_cve()
    write_audit()
    banner("✅", "discipline-check", "passed — CVE clean · no secrets · manifest valid")
    sys.exit(0)


if __name__ == "__main__":
    main()
