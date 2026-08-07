#!/usr/bin/env python3
"""Generate Codex hooks using codex-first script resolution.

Resolution rule:
1. For logical script `name.py`, prefer `scripts/codex-name.py`.
2. If no Codex-specific file exists, fall back to `scripts/name.py` only when
   it is explicitly allow-listed as common-safe.
3. Otherwise fail generation.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


def load_allow_shared(root: Path) -> set[str]:
    """Load the common-safe allow-list from check-codex-boundary.py."""
    path = root / "scripts" / "check-codex-boundary.py"
    spec = importlib.util.spec_from_file_location("check_codex_boundary", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_codex_boundary"] = module
    spec.loader.exec_module(module)
    return set(module.ALLOW_SHARED)


def logical_to_codex_name(script: str) -> str:
    """Map a logical script name to its Codex-specific candidate."""
    return script if script.startswith("codex-") else f"codex-{script}"


def resolve_script(root: Path, script: str, allow_shared: set[str]) -> str:
    """Resolve logical script to Codex-specific or allow-listed shared file."""
    scripts_dir = root / "scripts"
    codex_name = logical_to_codex_name(script)
    if (scripts_dir / codex_name).exists():
        return codex_name
    if script in allow_shared and (scripts_dir / script).exists():
        return script
    raise FileNotFoundError(
        f"cannot resolve {script}: expected scripts/{codex_name} or allow-listed shared script"
    )


def command_from(root: Path, spec: dict, allow_shared: set[str]) -> dict:
    """Convert one manifest command spec into a Codex hook command."""
    script = resolve_script(root, spec["script"], allow_shared)
    item = {
        "type": "command",
        "command": f"python3 \"${{PLUGIN_ROOT}}/scripts/{script}\"",
    }
    for key in ("timeout", "statusMessage", "additionalContextLimit"):
        if key in spec:
            item[key] = spec[key]
    return item


def generate(root: Path) -> dict:
    """Generate hooks JSON object from manifest."""
    manifest_path = root / "hooks" / "codex-hooks.manifest.json"
    manifest = json.loads(manifest_path.read_text())
    allow_shared = load_allow_shared(root)
    generated = {"hooks": {}}
    for event, entries in manifest.get("hooks", {}).items():
        generated["hooks"][event] = []
        for entry in entries:
            out = {}
            if "matcher" in entry:
                out["matcher"] = entry["matcher"]
            out["hooks"] = [command_from(root, command, allow_shared) for command in entry.get("commands", [])]
            generated["hooks"][event].append(out)
    return generated


def write_hooks(root: Path, data: dict) -> None:
    """Write generated hooks JSON."""
    path = root / "hooks" / "hooks.json"
    path.write_text(json.dumps(data, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="repository root")
    parser.add_argument("--check", action="store_true", help="fail if hooks.json is not generated output")
    args = parser.parse_args()
    root = Path(args.root).resolve()

    try:
        generated = generate(root)
    except Exception as exc:
        print(f"Codex hook generation failed: {exc}", file=sys.stderr)
        return 1

    hooks_path = root / "hooks" / "hooks.json"
    rendered = json.dumps(generated, indent=2) + "\n"
    if args.check:
        current = hooks_path.read_text() if hooks_path.exists() else ""
        if current != rendered:
            print("hooks/hooks.json is not generated from hooks/codex-hooks.manifest.json", file=sys.stderr)
            return 1
        print("Codex hooks generated output is current")
        return 0

    hooks_path.write_text(rendered)
    print(f"Generated {hooks_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
