#!/usr/bin/env python3
"""Validate Codex plugin hook/package boundaries.

Codex lifecycle entrypoints must call `scripts/codex-*.py` unless the script is
explicitly allow-listed as platform-neutral and safe for all hosts.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path


ALLOW_SHARED = {
    "cve-prompt-guard.py",
    "schema-guard.py",
    "token-guard.py",
    "obsidian-log.py",
}

COMMAND_SCRIPT_RE = re.compile(r"\$\{PLUGIN_ROOT\}/scripts/([^\"'\s]+\.py)")


def iter_hook_commands(node):
    """Yield command strings recursively from hooks JSON."""
    if isinstance(node, dict):
        if isinstance(node.get("command"), str):
            yield node["command"]
        for value in node.values():
            yield from iter_hook_commands(value)
    elif isinstance(node, list):
        for item in node:
            yield from iter_hook_commands(item)


def hook_script_names(hooks_path: Path) -> list[str]:
    """Extract script names referenced from hooks."""
    data = json.loads(hooks_path.read_text())
    names: list[str] = []
    for command in iter_hook_commands(data):
        match = COMMAND_SCRIPT_RE.search(command)
        if match:
            names.append(match.group(1))
    return names


def validate_hooks(root: Path) -> list[str]:
    """Validate hooks only reference allowed script targets."""
    problems: list[str] = []
    hooks_path = root / "hooks" / "hooks.json"
    if not hooks_path.exists():
        return ["hooks/hooks.json missing"]
    for script in hook_script_names(hooks_path):
        script_path = root / "scripts" / script
        if not script_path.exists():
            problems.append(f"hook target missing: scripts/{script}")
        if not script.startswith("codex-") and script not in ALLOW_SHARED:
            problems.append(f"hook target must be codex-* or allow-listed: scripts/{script}")
    return problems


def validate_bundle(root: Path, bundle: Path) -> list[str]:
    """Validate a built plugin bundle directory contains all hook targets."""
    problems: list[str] = []
    hooks_path = bundle / "hooks" / "hooks.json"
    if not hooks_path.exists():
        return ["bundle hooks/hooks.json missing"]
    for script in hook_script_names(hooks_path):
        if not (bundle / "scripts" / script).exists():
            problems.append(f"bundle missing hook target: scripts/{script}")
    return problems


def validate_generated_hooks(root: Path) -> list[str]:
    """Ensure hooks/hooks.json matches generator output."""
    generator = root / "scripts" / "generate-codex-hooks.py"
    hooks_path = root / "hooks" / "hooks.json"
    if not generator.exists():
        return ["scripts/generate-codex-hooks.py missing"]
    spec = importlib.util.spec_from_file_location("generate_codex_hooks", generator)
    module = importlib.util.module_from_spec(spec)
    sys.modules["generate_codex_hooks"] = module
    spec.loader.exec_module(module)
    try:
        rendered = json.dumps(module.generate(root), indent=2) + "\n"
    except Exception as exc:
        return [f"hook generation failed: {exc}"]
    current = hooks_path.read_text() if hooks_path.exists() else ""
    if current != rendered:
        return ["hooks/hooks.json is not generated from hooks/codex-hooks.manifest.json"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="repository root")
    parser.add_argument("--bundle", help="unpacked plugin bundle directory to validate")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    problems = validate_generated_hooks(root)
    problems.extend(validate_hooks(root))
    if args.bundle:
        problems.extend(validate_bundle(root, Path(args.bundle).resolve()))

    if problems:
        print("Codex boundary check failed:")
        for problem in problems:
            print(f"- {problem}")
        return 1
    print("Codex boundary check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
