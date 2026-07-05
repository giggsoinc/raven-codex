#!/usr/bin/env python3
"""Raven — MCP Server (platform-agnostic).

The ONLY enforcement channel Codex respects (no hooks/skills/agents there).
Codex CLI: merge config.toml.example into ~/.codex/config.toml.
Codex plugin: declared via .codex-plugin/plugin.json -> ./.mcp.json.
Tools: raven_status, raven_cve_check, raven_sync_libs, raven_debug, raven_violation.
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def send(obj: dict) -> None:
    """Write one JSON-RPC message to stdout and flush."""
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def read():
    """Read one JSON-RPC message from stdin; return None at EOF."""
    line = sys.stdin.readline()
    return json.loads(line.strip()) if line else None


def find_scripts_dir():
    """Locate the Raven scripts dir (project-local, bundled, or installed)."""
    cwd = Path(os.getcwd())
    here = Path(os.path.dirname(__file__))
    for candidate in [cwd / ".raven" / "scripts", cwd / ".codex" / "scripts",
                      here.parent / "scripts", here,
                      Path.home() / ".raven-codex" / "scripts", Path.home() / ".raven" / "scripts"]:
        if candidate.exists() and (candidate / "cve-check.py").exists():
            return candidate
    return None


def run_script(script: str, args=None) -> dict:
    """Run a Raven script via python3 and capture its output."""
    scripts = find_scripts_dir()
    if not scripts:
        return {"error": "Raven not installed in this project. Run raven-setup.sh first."}
    path = scripts / script
    if not path.exists():
        return {"error": f"{script} not found in {scripts}"}
    r = subprocess.run(["python3", str(path)] + (args or []),
                       capture_output=True, text=True, cwd=os.getcwd())
    return {"stdout": r.stdout, "stderr": r.stderr, "returncode": r.returncode}


def _obj(props=None, required=None) -> dict:
    """Build a JSON-schema object for a tool's inputSchema."""
    return {"type": "object", "properties": props or {}, "required": required or []}


def _text(s: str) -> dict:
    """Wrap a string as an MCP text-content result."""
    return {"content": [{"type": "text", "text": s}]}

TOOLS = [
    {"name": "raven_status", "description": "Check Raven manifest, version, mode, and health",
     "inputSchema": _obj()},
    {"name": "raven_cve_check", "description": "Run CVE security check on a Python library",
     "inputSchema": _obj({"library": {"type": "string", "description": "Library name e.g. fastapi"}}, ["library"])},
    {"name": "raven_sync_libs", "description": "Sync requirements/pyproject libraries into manifest",
     "inputSchema": _obj({"dry_run": {"type": "boolean", "description": "Preview only, don't write"}})},
    {"name": "raven_debug", "description": "Full Raven health check — manifest, scripts, hooks",
     "inputSchema": _obj()},
    {"name": "raven_violation", "description": "Emit a violation event to the Raven audit log",
     "inputSchema": _obj({"type": {"type": "string"},
                          "severity": {"type": "string", "enum": ["P1", "P2", "P3"]},
                          "detail": {"type": "string"}}, ["type", "severity", "detail"])},
    {"name": "raven_mark_skill", "description": "Record that a gated specialist skill "
     "(e.g. andie, andie-jr) has been invoked this session. Gated skills MUST call this "
     "as their first step — the script stamps the timestamp.",
     "inputSchema": _obj({"skill": {"type": "string", "description": "Skill name, e.g. andie-jr"}}, ["skill"])},
    {"name": "raven_gate_check", "description": "Check the skill-routing gate: returns ALLOW "
     "or the BLOCKED message if no fresh specialist marker exists. Commits also enforce this "
     "via the git pre-commit hook.",
     "inputSchema": _obj({"files": {"type": "array", "items": {"type": "string"},
                                    "description": "Files about to be modified (optional)"}})},
]


def _status() -> dict:
    """raven_status — summarize the project manifest."""
    mp = Path(os.getcwd()) / ".raven" / "manifest.json"
    if not mp.exists():
        return _text("❌ manifest.json not found — run raven-setup.sh")
    m = json.loads(mp.read_text())
    stack = m.get("stack", {})
    return _text(f"✅ Raven {m.get('standards', '')}\n"
                 f"Project: {m.get('project')} | Mode: {m.get('mode')} | "
                 f"GitHub: {m.get('github_id', '')} | Tag: {m.get('audit_tag', '')}\n"
                 f"Stack: {stack.get('language')} | Cloud: {stack.get('cloud')}")


def _debug() -> dict:
    """raven_debug — check key files and scripts exist."""
    cwd = Path(os.getcwd())
    checks = [f"{'✅' if (cwd / f).exists() else '❌'} {label}" for f, label in [
        (".raven/manifest.json", "manifest.json"), (".gitignore", ".gitignore"),
        (".git/hooks/pre-commit", "pre-commit hook")]]
    scripts = find_scripts_dir()
    checks.append(f"{'✅' if scripts else '❌'} raven scripts ({scripts or 'not found'})")
    checks.append(f"{'✅' if (cwd / 'AGENTS.md').exists() else '⚠️ '} AGENTS.md (Codex instructions)")
    return _text("\n".join(checks))


def _call(name: str, args: dict) -> dict:
    """Dispatch a tools/call by tool name."""
    if name == "raven_status":
        return _status()
    if name == "raven_cve_check":
        r = run_script("cve-check.py", ["--library", args.get("library", "")])
        return _text(r.get("stdout", "") + r.get("stderr", ""))
    if name == "raven_sync_libs":
        r = run_script("sync-libraries.py", ["--dry-run"] if args.get("dry_run") else [])
        return _text(r.get("stdout", ""))
    if name == "raven_debug":
        return _debug()
    if name == "raven_violation":
        r = run_script("emit-violation.py", ["--type", args.get("type", "unknown"),
                                             "--severity", args.get("severity", "P3"),
                                             "--detail", args.get("detail", "")])
        return _text("Violation emitted" if r.get("returncode") == 0 else r.get("stderr", ""))
    if name == "raven_mark_skill":
        r = run_script("raven-mark-skill.py", [args.get("skill", "")])
        return _text(r.get("stdout", "") or r.get("stderr", ""))
    if name == "raven_gate_check":
        gate_args = ["--event", "edit"]
        files = args.get("files") or []
        if files:
            gate_args += ["--file"] + [str(f) for f in files]
        r = run_script("raven-skill-gate.py", gate_args)
        if r.get("returncode") == 2:
            return _text(r.get("stderr", "BLOCKED by raven-skill-gate"))
        return _text("ALLOW" + (("\n" + r["stderr"]) if r.get("stderr") else ""))
    return _text(f"Unknown tool: {name}")


def handle(method: str, params: dict) -> dict:
    """Route an MCP method to its handler."""
    if method == "initialize":
        return {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}},
                "serverInfo": {"name": "raven", "version": "4.1.0"}}
    if method == "tools/list":
        return {"tools": TOOLS}
    if method == "tools/call":
        return _call(params.get("name"), params.get("arguments", {}))
    return {}


def main() -> None:
    """Read/handle/respond loop over JSON-RPC stdio."""
    while True:
        req = read()
        if req is None:
            break
        mid = req.get("id")
        try:
            send({"jsonrpc": "2.0", "id": mid, "result": handle(req.get("method", ""), req.get("params", {}))})
        except Exception as e:  # noqa: BLE001 — never crash the server loop
            send({"jsonrpc": "2.0", "id": mid, "error": {"code": -32603, "message": str(e)}})


if __name__ == "__main__":
    main()
