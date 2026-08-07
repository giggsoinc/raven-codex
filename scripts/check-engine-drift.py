#!/usr/bin/env python3
"""Check that generated or mirrored Raven engine files do not drift.

The Codex plugin keeps `scripts/` as the canonical engine tree. Optional mirror
trees may exist for compatibility, but their files must byte-match canonical
scripts when present.
"""

from __future__ import annotations

import argparse
import filecmp
import sys
from pathlib import Path


DEFAULT_MIRRORS = (".claude/scripts", ".codex/scripts")


def iter_canonical_files(root: Path) -> list[Path]:
    """Return canonical Python engine files under scripts/."""
    scripts = root / "scripts"
    if not scripts.exists():
        raise FileNotFoundError("canonical scripts/ directory is missing")
    return sorted(p for p in scripts.glob("*.py") if p.is_file())


def check_mirror(root: Path, mirror: Path) -> list[str]:
    """Compare one mirror tree to scripts/ and return drift messages."""
    problems: list[str] = []
    if not mirror.exists():
        return problems
    for source in iter_canonical_files(root):
        target = mirror / source.name
        if not target.exists():
            problems.append(f"missing mirror file: {target}")
            continue
        if not filecmp.cmp(source, target, shallow=False):
            problems.append(f"drift: {target} differs from {source}")
    return problems


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="repository root")
    parser.add_argument(
        "--mirror",
        action="append",
        default=[],
        help="mirror directory to check; defaults to known compatibility trees",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    mirrors = [root / m for m in (args.mirror or DEFAULT_MIRRORS)]
    problems: list[str] = []
    try:
        for mirror in mirrors:
            problems.extend(check_mirror(root, mirror))
    except FileNotFoundError as exc:
        problems.append(str(exc))

    if problems:
        print("Raven engine drift found:")
        for problem in problems:
            print(f"- {problem}")
        return 1

    print("Raven engine drift check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
