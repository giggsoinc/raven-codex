#!/usr/bin/env python3
"""
Raven — Triage Router (v4.2)

Deterministic routing: brownfield default = Andie-jr, greenfield default = Andie.

Precedence (mutually exclusive with architect-router — no double-fire):
  1. Force overrides: /andie, /andie-jr always win, exclusively
  2. Data-only question (explicit keywords, no code change) → direct answer —
     BUT symptom language overrides ("why is auth failing since yesterday?")
  3. Architecture-class prompt (decision intent, no symptom) → SILENT here;
     architect-router owns it and routes to Andie — even on a brownfield repo
  4. Trivial bounded edits (rename / fix typo / reformat…, ≤8 words) → nowhere
  5. Brownfield (git exists + commits > 1) → Andie-jr
  6. Greenfield (no .git OR ≤1 commit) → Andie

One source of truth: the DECISION/SYMPTOM classifier lives in
architect-router.py and is loaded here via importlib (fail-soft: any load
error → pre-v4.2 repo-state behavior, never a missed route).

Codex has no hook-JSON channel — emission is plain text on stdout, injected as
context. The FIRST line is the user-visible toaster: Raven never routes
silently.

Local-only. No telemetry.
"""

import os
import re
import sys
from pathlib import Path
from typing import Optional

# Add scripts dir to path for router_common import
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from router_common import (
        force_intent, is_brownfield, is_data_only_question, log_overhead)
except Exception:  # fail-soft: routing still works without the shared helper
    def force_intent(_p): return None
    def is_brownfield(_r="."): return False
    def is_data_only_question(_p): return False
    def log_overhead(_s, _t): return None

# Trivial bounded edits — no debug panel needed ("rename this variable →
# neither"). Symptom language still overrides.
_TRIVIAL = re.compile(
    r"^\s*(?:rename|fix\s+(?:a\s+)?typo|typo|reformat|re-?indent|sort\s+imports?|"
    r"bump\s+(?:the\s+)?version|add\s+a\s+comment)\b", re.IGNORECASE)

_ARCHITECT_MOD = None


def _architect_mod():
    """Load architect-router.py once so its decision/symptom regexes have ONE
    source of truth. Fail-soft: any load error → None (triage keeps its
    repo-state default; worst case is the pre-v4.2 double-fire, never a missed
    route)."""
    global _ARCHITECT_MOD
    if _ARCHITECT_MOD is None:
        try:
            import importlib.util
            path = Path(__file__).resolve().parent / "architect-router.py"
            spec = importlib.util.spec_from_file_location("_architect_router", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _ARCHITECT_MOD = mod
        except Exception:
            _ARCHITECT_MOD = False
    return _ARCHITECT_MOD or None


def is_symptom(prompt: str) -> bool:
    """True if the prompt carries symptom language (broken/failing/timeout…)."""
    mod = _architect_mod()
    return bool(mod and mod.SYMPTOM_NEGATE.search(prompt))


def is_architecture_class(prompt: str) -> bool:
    """True if architect-router would claim this prompt (decision intent, no
    symptom language)."""
    mod = _architect_mod()
    return bool(mod and mod.classify(prompt))


def classify(prompt: str) -> Optional[str]:
    """Return 'andie-jr' for brownfield, 'andie' for greenfield, None when
    triage should stay silent (data-only, trivial, or architect-router owns it)."""
    symptom = is_symptom(prompt)

    if not symptom and _TRIVIAL.match(prompt) and len(prompt.split()) <= 8:
        return None  # trivial bounded edit — no panel needed

    if is_data_only_question(prompt) and not symptom:
        return None  # direct answer — symptom language overrides the data check

    if is_architecture_class(prompt):
        return None  # decision/architecture intent → architect-router routes to Andie

    return "andie-jr" if is_brownfield(".") else "andie"


def main() -> None:
    """Route based on repo state (brownfield → Andie-jr, greenfield → Andie)."""
    prompt = os.environ.get("PROMPT", "")
    if not prompt:
        try:
            prompt = sys.stdin.read()
        except Exception:
            return
    if not prompt or not prompt.strip():
        return

    # 1. Explicit force always wins, exclusively
    forced = force_intent(prompt)
    if forced == "andie":
        return  # architect-router owns the andie force path
    if forced == "andie-jr":
        _emit_andie_jr(reason="forced via /andie-jr")
        return

    routed_to = classify(prompt)
    if routed_to == "andie-jr":
        _emit_andie_jr()
    elif routed_to == "andie":
        _emit_andie()
    # else: None → data-only / trivial, or architect-router owns it (no emission)


def _emit_andie_jr(reason: str = "brownfield repo detected") -> None:
    """Emit toaster (first line) + [ANDIE-JR REQUIRED] injection."""
    emission = (
        f"🪶 Raven → andie-jr · {reason} · debug flow: triage → root cause → fix\n"
        "[ANDIE-JR REQUIRED] Brownfield repo detected. Invoke `andie-jr` "
        "before diagnosing or editing; its first step records the invocation "
        "marker. This routing is ENFORCED at commit time by raven-skill-gate: "
        "without a fresh specialist marker, commits to code files are warned "
        "(soft mode) or blocked (hard mode). Surface the first toaster line "
        "to the user verbatim — Raven never routes silently.\n"
    )
    sys.stdout.write(emission)
    log_overhead("triage-router", emission)


def _emit_andie(reason: str = "greenfield project detected") -> None:
    """Emit toaster (first line) + [ANDIE REQUIRED] injection."""
    emission = (
        f"🪶 Raven → andie · {reason} · planning flow: problem → angles → plan\n"
        "[ANDIE REQUIRED] Greenfield project detected. Invoke `andie` before "
        "coding; its first step records the invocation marker. This routing "
        "is ENFORCED at commit time by raven-skill-gate: without a fresh "
        "specialist marker, commits to code files are warned (soft mode) or "
        "blocked (hard mode). Surface the first toaster line to the user "
        "verbatim — Raven never routes silently.\n"
    )
    sys.stdout.write(emission)
    log_overhead("triage-router", emission)


if __name__ == "__main__":
    main()
