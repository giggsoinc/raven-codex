#!/usr/bin/env python3
"""
Raven — Triage Router (v4.1)

State-based router that runs on every UserPromptSubmit BEFORE any skill loads.

Rule: Brownfield repos default to Andie-jr (unless pure data question).

If brownfield detected → print [ANDIE-JR REQUIRED] to stdout.
Codex injects it as additionalContext and loads andie-jr first.

If greenfield or data question → silent passthrough. Other routing applies.

Local-only. No telemetry. No regex. ~30 LOC.
"""

import os
import sys
from pathlib import Path

# Add scripts dir to path for router_common import
sys.path.insert(0, str(Path(__file__).parent))
from router_common import route_prompt, log_overhead


def main():
    """Route based on repo state (brownfield/greenfield) and prompt type."""
    # Codex passes the prompt via $PROMPT env or stdin
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

    if route == "andie-jr":
        # additionalContext injection — Codex reads stdout on UserPromptSubmit
        emission = (
            "[ANDIE-JR REQUIRED] Brownfield repo detected. MANDATORY: invoke "
            "`andie-jr` skill BEFORE any file read, bash command, or response. "
            "Andie-jr structures debug flow: problem → root cause → fix → audit.\n"
        )
        sys.stdout.write(emission)
        log_overhead("triage-router", emission)


if __name__ == "__main__":
    main()
