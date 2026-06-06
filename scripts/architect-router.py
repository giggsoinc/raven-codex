#!/usr/bin/env python3
"""
Raven — Architect Router (v4.1)

State-based router for greenfield repos.

Rule: Greenfield repos default to Andie (planning/architecture).

Greenfield = no .git or commits ≤ 1.

If greenfield and not a data question → print [ANDIE REQUIRED].
Codex injects as additionalContext and loads andie before response.

If brownfield or data question → silent passthrough. Triage-router owns brownfield.

Local-only. No telemetry. No regex. ~25 LOC.
"""

import os
import sys
from pathlib import Path

# Add scripts dir to path for router_common import
sys.path.insert(0, str(Path(__file__).parent))
from router_common import route_prompt, is_brownfield, log_overhead


def main():
    """Route to Andie for greenfield repos (unless pure data question)."""
    prompt = os.environ.get("PROMPT", "")
    if not prompt:
        try:
            prompt = sys.stdin.read()
        except Exception:
            return

    if not prompt or not prompt.strip():
        return

    # Use state-based routing (no regex)
    route = route_prompt(prompt, repo_path=".")

    # Architect-router only fires for greenfield repos
    if route == "andie" and not is_brownfield("."):
        emission = (
            "[ANDIE REQUIRED] Greenfield repo detected. MANDATORY: invoke "
            "`andie` skill BEFORE responding. Andie plans architecture, "
            "runs Functional/Technical/Data triad, HITL-gates proposals. "
            "Do not free-style the design.\n"
        )
        sys.stdout.write(emission)
        log_overhead("architect-router", emission)


if __name__ == "__main__":
    main()
