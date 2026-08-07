#!/usr/bin/env python3
"""Codex hook boundary tests."""

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "check-codex-boundary.py"
GENERATOR = ROOT / "scripts" / "generate-codex-hooks.py"


def load_checker():
    spec = importlib.util.spec_from_file_location("check_codex_boundary", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["check_codex_boundary"] = mod
    spec.loader.exec_module(mod)
    return mod


def load_generator():
    spec = importlib.util.spec_from_file_location("generate_codex_hooks", GENERATOR)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["generate_codex_hooks"] = mod
    spec.loader.exec_module(mod)
    return mod


class CodexBoundaryCase(unittest.TestCase):
    def test_repo_hooks_pass_boundary(self):
        checker = load_checker()
        self.assertEqual(checker.validate_hooks(ROOT), [])
        self.assertEqual(checker.validate_generated_hooks(ROOT), [])

    def test_non_codex_hook_target_fails_unless_allowlisted(self):
        checker = load_checker()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "hooks").mkdir()
            (root / "scripts").mkdir()
            (root / "scripts" / "session-start.py").write_text("")
            (root / "hooks" / "hooks.json").write_text(json.dumps({
                "hooks": {
                    "SessionStart": [{
                        "hooks": [{
                            "type": "command",
                            "command": "python3 \"${PLUGIN_ROOT}/scripts/session-start.py\"",
                        }]
                    }]
                }
            }))

            problems = checker.validate_hooks(root)

        self.assertTrue(any("must be codex-*" in p for p in problems))

    def test_generator_prefers_codex_file(self):
        generator = load_generator()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "scripts" / "check-codex-boundary.py").write_text(f"ALLOW_SHARED = {set()!r}\n")
            (root / "scripts" / "codex-example.py").write_text("")
            resolved = generator.resolve_script(root, "example.py", set())
        self.assertEqual(resolved, "codex-example.py")

    def test_generator_allows_common_only_when_allowlisted(self):
        generator = load_generator()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "scripts" / "common.py").write_text("")
            resolved = generator.resolve_script(root, "common.py", {"common.py"})
            with self.assertRaises(FileNotFoundError):
                generator.resolve_script(root, "common.py", set())
        self.assertEqual(resolved, "common.py")


if __name__ == "__main__":
    unittest.main()
