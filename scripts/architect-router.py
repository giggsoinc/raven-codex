#!/usr/bin/env python3
"""
Raven — Architect Router (v4.2)

State + intent router that owns the Andie path. Symmetric counterpart to
triage-router; the two are mutually exclusive (no double-fire).

Rule: DECISION intent (design/plan/should-I/which/tradeoff/architecture) AND
not a symptom (symptoms belong to triage-router → andie-jr); bare build/create
verbs also need multi-component scope. Greenfield repos with no decision intent
still default to Andie via triage-router's classify.

Codex has no hook-JSON channel — emission is plain text on stdout, injected as
context. The FIRST line is the user-visible toaster: Raven never routes
silently.

Local-only. No telemetry.
"""

import os
import re
import sys
from pathlib import Path

# Add scripts dir to path for router_common import
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from router_common import force_intent, log_overhead
except Exception:  # fail-soft: routing still works without the shared helper
    def force_intent(_p): return None
    def log_overhead(_s, _t): return None

# ── DECISION intent — any one match triggers ─────────────────────────────────
DECISION = re.compile(
    r"(?:"
    r"\bdesign\b"
    r"|\bplan(?:ning)?\b"
    r"|\barchitecture\b|\barchitect(?:ural)?\b"
    r"|\bshould\s+i\b|\bshould\s+we\b"
    r"|\bwhich\s+(?:approach|option|way|stack|tool|library|framework|design|pattern)"
    r"|\bcompare\b|\bcomparison\b"
    r"|\btrade.?off\b|\bpros\s+and\s+cons\b"
    r"|\brefactor\b"
    r"|\bscaffold\b|\bbootstrap\b"
    r"|\bhow\s+do\s+i\s+(?:approach|design|architect|structure|organize|model)"
    r"|\bhow\s+should\s+i\b"
    r"|\bbest\s+way\s+to\b"
    r"|\bevaluate\b|\bassess\b"
    r"|\bbuild\s+(?:me\s+)?(?:a|an|the|new)\s+\w"
    r"|\bcreate\s+(?:a|an|the|new)\s+\w"
    r"|\bimplement\s+(?:a|an|the|new)\s+\w"
    r"|\badd\s+(?:a|an|the|new)\s+\w"
    r"|\bdecide\b|\bdecision\b"
    r"|\bstrategy\b|\bstrategic\b"
    r"|\broadmap\b"
    r"|\breview\s+(?:options|approaches|approach|design|architecture)"
    r"|\bgreenfield\b"
    r"|\bsystem\s+design\b"
    r")",
    re.IGNORECASE,
)

# ── MULTI-COMPONENT scope signals — imply ≥2 moving parts ────────────────────
MULTI_COMPONENT = re.compile(
    r"(?:"
    r"\bauth(?:entication|orization)?\s+(?:and|\+|with|plus)\s+\w+"
    r"|\b(?:api|frontend|backend|database|cache|queue|worker|service)\s+(?:and|\+|with|plus)\s+\w+"
    r"|\bmulti.\w+"
    r"|\bdistributed\b"
    r"|\bpipeline\b|\bworkflow\b|\borchestrat(?:e|ion)\b"
    r"|\bmicroservice"
    r"|\bevent.driven\b|\bevent\s+sourc(?:e|ing)\b"
    r"|\bdata\s+model\b|\bschema\b|\bentity\s+(?:relationship|model)"
    r"|\bintegration\s+(?:between|of|with)"
    r"|\bcross.\w+"
    r"|\bend.to.end\b|\be2e\b"
    r"|\bstack\b|\barchitecture\b|\bplatform\b"
    r"|\bsystem\b.{0,30}\bsystem\b"
    r"|\b(?:two|three|four|five|multiple|several|many)\s+(?:services|systems|components|modules|tiers|layers)"
    r"|\bmonorepo\b|\bmono.repo\b"
    r"|\brbac\b|\bsso\b|\boauth\b"
    r"|\bobservability\b|\btelemetry\b|\bmetrics?\s+and\s+log"
    r"|\bci/cd\b|\bcicd\b|\bdeployment\s+pipeline\b"
    r")",
    re.IGNORECASE,
)

# ── SYMPTOM negation — triage-router (andie-jr) handles these ────────────────
SYMPTOM_NEGATE = re.compile(
    r"(?:"
    r"\btiming?\s*out\b|\btimed?\s*out\b|\btimeout\b"
    r"|\bfail(?:ing|ed|s|ure)?\b|\bcrash(?:ing|ed|es)?\b|\bhang(?:ing|s)?\b"
    r"|\bstuck\b|\bfrozen\b|\bunresponsive\b|\bbroken\b"
    r"|\berror\b|\bexception\b|\btraceback\b|\bstack\s*trace\b"
    r"|\bregression\b|\bused\s+to\s+\w+"
    r"|\bdoesn'?t\s+(?:work|run|fire|return|load|start)\b"
    r"|\bnot\s+(?:working|responding|loading|firing|starting)\b"
    r"|\bcan'?t\s+(?:connect|reach|access)\b"
    r"|\bwhy\s+(?:is|isn'?t|did|does|won'?t)\s+(?:my|the|this)"
    r")",
    re.IGNORECASE,
)


def classify(prompt: str) -> bool:
    """Return True if prompt is architecture-class (andie required)."""
    if not prompt or not prompt.strip():
        return False
    if SYMPTOM_NEGATE.search(prompt):
        return False  # triage-router owns this
    has_decision = bool(DECISION.search(prompt))
    has_multi = bool(MULTI_COMPONENT.search(prompt))
    # Bare build/create/add verbs need multi-component scope to qualify
    build_only = re.compile(
        r"^\s*(?:build|create|add|implement|scaffold|bootstrap)\s+", re.IGNORECASE)
    if build_only.match(prompt) and not has_multi:
        return False  # "build a function" — too small, let normal routing handle
    return has_decision


def main() -> None:
    """Emit [ANDIE REQUIRED] for architecture-class prompts.

    Order: explicit force (exclusive) → regex classify. Silent otherwise.
    """
    prompt = os.environ.get("PROMPT", "")
    if not prompt:
        try:
            prompt = sys.stdin.read()
        except Exception:
            return
    if not prompt or not prompt.strip():
        return

    forced = force_intent(prompt)
    if forced == "andie-jr":
        return  # explicit andie-jr force is exclusive — triage-router owns it
    trigger = (forced == "andie") or classify(prompt)
    if not trigger:
        return

    why = "forced via /andie" if forced == "andie" else "architecture-class prompt detected"
    emission = (
        f"🪶 Raven → andie · {why} · triad plan before code\n"
        "[ANDIE REQUIRED] This prompt is architecture-class — it involves "
        "design decisions, multi-component scope, or strategic tradeoffs. "
        "MANDATORY: invoke `andie` skill BEFORE responding. Andie runs the "
        "Functional/Technical/Data triad, HITL-gates proposals, and hands off "
        "a crisp plan. Surface the first toaster line to the user verbatim — "
        "Raven never routes silently. Do not free-style the design.\n"
    )
    sys.stdout.write(emission)
    log_overhead("architect-router", emission)


if __name__ == "__main__":
    main()
