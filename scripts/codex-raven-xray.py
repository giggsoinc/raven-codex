#!/usr/bin/env python3
"""Raven Xray: static Python code-symbol map.

Limits are intentional: Python only, stdlib `ast`, static imports/calls only,
plain JSON at `.raven/xray.json`. It is a code map, not a runtime graph.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

XRAY_PATH = Path(".raven/xray.json")
LIMIT_NOTE = "Python-only static AST map; dynamic dispatch/imports are not resolved."


def python_files(root: Path) -> list[Path]:
    """Return source Python files under root."""
    ignored = {".git", ".raven", "__pycache__", "node_modules", ".venv", "venv"}
    files: list[Path] = []
    for path in root.rglob("*.py"):
        if any(part in ignored for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


def rel(path: Path, root: Path) -> str:
    """Relative path string."""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def call_name(node: ast.AST) -> str | None:
    """Best-effort static call target name."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = call_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return None


class FileVisitor(ast.NodeVisitor):
    """Collect symbols, imports, and static calls for one file."""

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self.scope: list[str] = []
        self.symbols: dict[str, dict[str, Any]] = {}
        self.imports: list[str] = []
        self.calls: list[dict[str, str]] = []

    def current_symbol(self) -> str | None:
        return ".".join(self.scope) if self.scope else None

    def add_symbol(self, name: str, kind: str, lineno: int) -> None:
        qname = ".".join([*self.scope, name]) if self.scope else name
        self.symbols[qname] = {
            "name": qname,
            "kind": kind,
            "file": self.file_path,
            "line": lineno,
        }

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append(alias.name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = "." * node.level + (node.module or "")
        for alias in node.names:
            self.imports.append(f"{module}.{alias.name}".strip("."))

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.add_symbol(node.name, "class", node.lineno)
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.add_symbol(node.name, "function", node.lineno)
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)

    def visit_Call(self, node: ast.Call) -> None:
        target = call_name(node.func)
        source = self.current_symbol()
        if target and source:
            self.calls.append({"from": source, "to": target, "file": self.file_path})
        self.generic_visit(node)


def build(root: Path) -> dict[str, Any]:
    """Build xray graph."""
    files = python_files(root)
    symbols: dict[str, dict[str, Any]] = {}
    imports_by_file: dict[str, list[str]] = {}
    calls: list[dict[str, str]] = []
    errors: list[str] = []

    for path in files:
        name = rel(path, root)
        try:
            tree = ast.parse(path.read_text(errors="ignore"), filename=name)
        except SyntaxError as exc:
            errors.append(f"{name}:{exc.lineno}: {exc.msg}")
            continue
        visitor = FileVisitor(name)
        visitor.visit(tree)
        for sym, data in visitor.symbols.items():
            symbols[f"{name}:{sym}"] = data
        imports_by_file[name] = sorted(set(visitor.imports))
        calls.extend(visitor.calls)

    callers: dict[str, list[str]] = defaultdict(list)
    callees: dict[str, list[str]] = defaultdict(list)
    known_short = {data["name"].split(".")[-1]: key for key, data in symbols.items()}
    for call in calls:
        target = call["to"].split(".")[-1]
        target_key = known_short.get(target, call["to"])
        source_key = f"{call['file']}:{call['from']}"
        callers[target_key].append(source_key)
        callees[source_key].append(target_key)

    hotspot_counts = Counter(call["file"] for call in calls)
    hotspots = [
        {"file": file, "static_call_count": count, "symbol_count": sum(1 for s in symbols.values() if s["file"] == file)}
        for file, count in hotspot_counts.most_common(20)
    ]

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "root": str(root),
        "limits": LIMIT_NOTE,
        "files_count": len(files),
        "symbols_count": len(symbols),
        "calls_count": len(calls),
        "symbols": symbols,
        "imports_by_file": imports_by_file,
        "calls": calls,
        "callers": {k: sorted(set(v)) for k, v in callers.items()},
        "callees": {k: sorted(set(v)) for k, v in callees.items()},
        "hotspots": hotspots,
        "errors": errors,
    }


def is_stale(path: Path, seconds: int) -> bool:
    """Return true when path is missing or older than seconds."""
    if not path.exists():
        return True
    return (time.time() - path.stat().st_mtime) > seconds


def load_xray() -> dict[str, Any]:
    """Load xray JSON fail-soft."""
    try:
        return json.loads(XRAY_PATH.read_text())
    except Exception:
        return {}


def print_list(title: str, items: list[str]) -> None:
    print(f"{title} ({LIMIT_NOTE})")
    for item in items:
        print(f"- {item}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true", help="Build .raven/xray.json")
    parser.add_argument("--if-stale", type=int, help="Build only if xray is older than N seconds")
    parser.add_argument("--callers", help="Show static callers for a symbol")
    parser.add_argument("--callees", help="Show static callees for a symbol")
    parser.add_argument("--impact", help="Show callers and callees for a symbol")
    parser.add_argument("--root", default=".", help="Repository root")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if args.build or (args.if_stale is not None and is_stale(XRAY_PATH, args.if_stale)):
        data = build(root)
        XRAY_PATH.parent.mkdir(parents=True, exist_ok=True)
        XRAY_PATH.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
        print(f"xray built: {XRAY_PATH} ({data['symbols_count']} symbols, {data['calls_count']} calls)")
        if not (args.callers or args.callees or args.impact):
            return 0

    data = load_xray()
    if not data:
        print("xray missing; run: python3 scripts/raven-xray.py --build", file=sys.stderr)
        return 1

    if args.callers or args.impact:
        symbol = args.callers or args.impact
        print_list(f"Callers of {symbol}", data.get("callers", {}).get(symbol, []))
    if args.callees or args.impact:
        symbol = args.callees or args.impact
        print_list(f"Callees of {symbol}", data.get("callees", {}).get(symbol, []))
    return 0


if __name__ == "__main__":
    sys.exit(main())
