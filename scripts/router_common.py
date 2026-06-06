#!/usr/bin/env python3
"""
Raven — Common Routing Logic (v4.1)

Replaces regex-based routing with simple state-based detection.

Rules:
  1. Force overrides: /andie or /andie-jr always work
  2. Pure data questions (read/query/explain, no code changes) → answer directly
  3. Brownfield (.git exists, commits > 1) → default Andie-jr
  4. Greenfield (no .git or commits ≤ 1) → default Andie
"""

import os
import subprocess
from pathlib import Path


def is_brownfield(repo_path: str = ".") -> bool:
    """Check if repo is brownfield (has git with >1 commits)."""
    git_dir = Path(repo_path) / ".git"
    if not git_dir.exists():
        return False
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "rev-list", "--count", "HEAD"],
            capture_output=True, text=True, timeout=2
        )
        commit_count = int(result.stdout.strip()) if result.returncode == 0 else 0
        return commit_count > 1
    except Exception:
        return False


def is_data_only_question(prompt: str) -> bool:
    """
    Pure data question: keywords present, no code changes mentioned, no decisions.
    Keywords: read, query, explain, show, list, count, help, what, how, search, find
    """
    data_keywords = {
        "read", "query", "explain", "show", "list", "count", "help",
        "what", "search", "find", "get", "display",
        "tell me", "can you tell me", "what is", "how many",
        "how does", "how much", "where is", "find me", "show me",
        "list the", "count the", "enumerate", "describe", "outline"
    }
    code_change_indicators = {
        "write", "create", "build", "implement", "change", "fix",
        "modify", "update", "delete", "remove", "add ", "edit",
        "refactor", "rewrite", "replace", "insert", "commit this",
        "commit the", " commit ", "git commit"
    }
    decision_indicators = {
        "should i", "should we", "should ", "which approach", "best way",
        "pros and cons", "compare", "decision", "tradeoff", "versus"
    }

    prompt_lower = prompt.lower().strip()

    # Check for force overrides first (handled elsewhere, but document here)
    if prompt_lower.startswith(("/andie", "/andie-jr")):
        return False

    has_data_keyword = any(kw in prompt_lower for kw in data_keywords)
    has_code_change = any(ind in prompt_lower for ind in code_change_indicators)
    has_decision = any(ind in prompt_lower for ind in decision_indicators)

    return has_data_keyword and not has_code_change and not has_decision


def route_prompt(prompt: str, repo_path: str = ".") -> str:
    """
    Route a prompt to the appropriate helper.

    Returns: "andie", "andie-jr", or "direct" (no routing needed)
    """
    if not prompt or not prompt.strip():
        return "direct"

    prompt_lower = prompt.strip().lower()

    # 1. Force overrides (explicit commands)
    if prompt_lower.startswith("/andie-jr"):
        return "andie-jr"
    if prompt_lower.startswith("/andie"):
        return "andie"

    # 2. Pure data questions → answer directly
    if is_data_only_question(prompt):
        return "direct"

    # 3. Brownfield/Greenfield detection
    brownfield = is_brownfield(repo_path)

    # Default: Brownfield → Andie-jr, Greenfield → Andie
    return "andie-jr" if brownfield else "andie"


def log_overhead(source: str, text: str, repo_path: str = ".") -> None:
    """Fail-soft logging of routing decision to log-overhead.py."""
    try:
        script_dir = Path(__file__).parent
        log_path = script_dir / "log-overhead.py"
        if not log_path.exists():
            return
        tokens = max(1, len(text) // 4)
        subprocess.Popen(
            ["python3", str(log_path), "--source", source, "--tokens", str(tokens)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            cwd=repo_path
        )
    except Exception:
        pass  # never block
