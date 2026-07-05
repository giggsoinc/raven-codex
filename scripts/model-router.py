#!/usr/bin/env python3
"""
Model Router v2 — Dynamic Model Routing for Raven-Codex

Classifies user queries and context into tiers (SIMPLE, MEDIUM, COMPLEX, LOCAL_ONLY)
based on signal detection, and outputs routing decision to .raven/.model-session.json.

LOCAL_ONLY is a HARD FLOOR: when secrets are detected, resolve_model() never
returns a cloud model — the only options are the configured local model
(ollama) or proceeding in-context without spawning anything.

Usage:
  - Library: from model_router import classify, resolve_model
    tier, score, reasons, model = classify(prompt, context)
    cloud_param, model = resolve_model(tier)   # cloud_param is None ⇒ local only

  - CLI: python3 model-router.py --prompt "..." [--context "{...}"] [--hook]
    --hook emits a plain-text user-visible toaster as the FIRST line plus
    RAVEN_MODEL_TIER guidance (Codex injects stdout as context — there is no
    hook-JSON channel).
"""

import argparse
import json
import hashlib
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List, Dict


# Signal definitions (keywords, weights)
SECURITY_KEYWORDS = {
    "vuln", "vulnerability", "cve", "exploit", "auth", "authentication",
    "token", "jwt", "oauth", "injection", "sql", "xss", "csrf", "credential",
    "secret", "password", "key", "cipher", "encrypt", "decrypt", "hash",
    "breach", "attack", "malicious", "threat", "vulnerability"
}

ARCHITECTURE_KEYWORDS = {
    "design", "schema", "database", "migrate", "migration", "refactor",
    "refactoring", "plan", "tradeoff", "architecture", "pattern",
    "structure", "class", "interface", "module", "component", "system",
    "api", "endpoint", "route", "handler", "service", "layer"
}

REASONING_KEYWORDS = {
    "compare", "which", "approach", "pros", "cons", "tradeoff", "should",
    "recommendation", "best", "optimal", "efficient", "trade-off",
    "advantage", "disadvantage", "alternative"
}


def _score_signal(prompt: str, context: str) -> Tuple[int, List[str]]:
    """
    Score the prompt and context on signal presence.

    Returns:
        (total_score, list_of_reasons)
    """
    score = 0
    reasons = []

    # Combine prompt and context for searching
    combined = f"{prompt} {context}".lower()

    # Security keywords (+3)
    for keyword in SECURITY_KEYWORDS:
        if keyword in combined:
            score += 3
            reasons.append(f"security_keyword:{keyword}")
            break  # Count once per category

    # Architecture keywords (+3)
    for keyword in ARCHITECTURE_KEYWORDS:
        if keyword in combined:
            score += 3
            reasons.append(f"architecture_keyword:{keyword}")
            break  # Count once per category

    # Reasoning keywords (+3)
    for keyword in REASONING_KEYWORDS:
        if keyword in combined:
            score += 3
            reasons.append(f"reasoning_keyword:{keyword}")
            break  # Count once per category

    # Multi-file scope (+2): references to multiple files
    file_count = len(re.findall(r'\b[a-z_]+\.(py|ts|js|go|java|rs|sql)\b', prompt))
    if file_count >= 3:
        score += 2
        reasons.append(f"multi_file_scope:{file_count}_files")
    elif "across the codebase" in prompt.lower() or "across" in prompt.lower():
        score += 2
        reasons.append("multi_file_scope:across_codebase")

    # Test/doc generation (+1)
    if any(x in prompt.lower() for x in ["write test", "write tests", "write unit test", "write unittest", "document", "docstring", "generate test"]):
        score += 1
        reasons.append("test_or_doc_generation")

    # Debugging with stack trace (+1)
    if "traceback" in combined or "error:" in combined or "failed" in combined:
        score += 1
        reasons.append("debugging_with_error")

    # Single-file bounded edit (-1): "fix typo", "rename variable", etc.
    if any(x in prompt.lower() for x in ["fix typo", "rename", "what does", "what is", "return"]):
        if not any(x in prompt.lower() for x in ["across", "multiple", "several"]):
            score = max(0, score - 1)
            reasons.append("single_file_bounded_edit")

    return score, reasons


def _detect_secrets(context: str) -> bool:
    """
    Detect if secrets or sensitive credentials are present in context.

    FORCE → LOCAL_ONLY if true.
    """
    # Check for common secret patterns
    secret_patterns = [
        r'manifest\.secrets',
        r'\.env',
        r'SECRET_KEY\s*=',
        r'API_KEY\s*=',
        r'password\s*=',
        r'token\s*=',
        r'private\s+key',
        r'-----BEGIN',
        r'-----END',
    ]

    context_lower = context.lower()
    for pattern in secret_patterns:
        if re.search(pattern, context_lower, re.IGNORECASE):
            return True

    # Check for credential markers in context
    if any(x in context for x in ['PRIVATE', 'SECRET', '-----BEGIN']):
        return True

    return False


def _load_model_env() -> Dict[str, str]:
    """
    Load .model.env and extract tier → model mapping.

    Actual format (written by session-start.py):
        [routing]
        LOCAL_ONLY = ollama/dolphin-mistral:latest
        SIMPLE     = ollama/dolphin-mistral:latest
        MEDIUM     = openai/gpt-4o
        COMPLEX    = openai/o1

    Returns {tier: "provider/model"} dict
    """
    # Check project-local first, then home
    model_env_path = Path.cwd() / ".model.env"
    if not model_env_path.exists():
        model_env_path = Path.home() / ".model.env"

    defaults = {
        "SIMPLE": "openai/gpt-4o-mini",
        "MEDIUM": "openai/gpt-4o",
        "COMPLEX": "openai/o1",
        "LOCAL_ONLY": "ollama/dolphin-mistral",
    }

    if not model_env_path.exists():
        return defaults

    models = {}
    in_routing = False

    try:
        with open(model_env_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith(";"):
                    continue

                # Detect [routing] section
                if line == "[routing]":
                    in_routing = True
                    continue
                elif line.startswith("["):
                    in_routing = False
                    continue

                # Parse TIER = provider/model within [routing]
                if in_routing and "=" in line:
                    key, val = line.split("=", 1)
                    tier = key.strip()
                    model_str = val.strip()
                    if tier in ("LOCAL_ONLY", "SIMPLE", "MEDIUM", "COMPLEX"):
                        models[tier] = model_str
    except Exception as e:
        print(f"Warning: Failed to parse .model.env: {e}", file=sys.stderr)

    # Fill missing tiers with defaults
    for tier, default_model in defaults.items():
        if tier not in models:
            models[tier] = default_model

    return models


_LOCAL_PROVIDERS = {"ollama", "local", "lmstudio", "llamacpp", "vllm"}
_DEFAULT_LOCAL = "ollama/dolphin-mistral"


def _is_local_model(model: str) -> bool:
    """True if the provider prefix is a local runtime (never leaves the box)."""
    return model.split("/", 1)[0].lower() in _LOCAL_PROVIDERS


def resolve_model(tier: str) -> Tuple[Optional[str], str]:
    """Resolve a tier to (cloud_param, model).

    LOCAL_ONLY is a hard floor: ALWAYS returns (None, <local model>) — never a
    cloud param, even if .model.env misconfigures the tier to a cloud model.
    (The old behavior of silently remapping a privacy tier to a small cloud
    model would exfiltrate secret-laden context.)

    Non-privacy tiers return (model, model) for cloud models. A non-privacy
    tier pointed at a local model returns (None, <local model>) — callers may
    fall back to a cloud default but must flag it `cloud_fallback`.
    """
    models = _load_model_env()
    configured = models.get(tier, _DEFAULT_LOCAL)
    if tier == "LOCAL_ONLY":
        local = configured if _is_local_model(configured) else _DEFAULT_LOCAL
        return None, local
    if _is_local_model(configured):
        return None, configured
    return configured, configured


def classify(
    prompt: str,
    context: str = ""
) -> Tuple[str, int, List[str], str]:
    """
    Classify a query into tier: SIMPLE, MEDIUM, COMPLEX, LOCAL_ONLY.

    Args:
        prompt: User query text
        context: Additional context (e.g., previous messages, file content)

    Returns:
        (tier, score, reasons, model_string)
    """
    # Force LOCAL_ONLY if secrets detected — hard floor, never a cloud model
    if _detect_secrets(context):
        _, local_model = resolve_model("LOCAL_ONLY")
        return "LOCAL_ONLY", 999, ["secrets_in_context"], local_model

    # Score the query
    score, reasons = _score_signal(prompt, context)

    # Assign tier based on score
    if score >= 6:
        tier = "COMPLEX"
    elif score >= 3:
        tier = "MEDIUM"
    else:
        tier = "SIMPLE"

    # Load model config and get model for this tier
    models = _load_model_env()
    model_string = models.get(tier, "openai/gpt-4o")

    return tier, score, reasons, model_string


def write_session_json(tier: str, score: int, reasons: List[str], model: str, prompt: str, source: str = "user_work") -> Path:
    """
    Write classification result to .raven/.model-session.json.

    Two-bucket schema:
      - raven_overhead: tokens from Raven internals (hooks, skill loads, banners)
      - user_work: tokens from the user's actual prompt + Codex's response

    Default source = user_work (this is the typical case — Codex is responding
    to a user prompt). When called from a hook context that's purely overhead,
    pass --source raven_overhead.

    Returns:
        Path to written file
    """
    raven_dir = Path.cwd() / ".raven"
    raven_dir.mkdir(exist_ok=True)

    session_file = raven_dir / ".model-session.json"

    # Load existing or init two-bucket schema
    if session_file.exists():
        try:
            data = json.loads(session_file.read_text())
        except Exception:
            data = {}
    else:
        data = {}

    # Init schema if missing or legacy
    if "raven_overhead" not in data or "user_work" not in data:
        data = {
            "session_started_at": data.get("session_started_at") or (datetime.utcnow().isoformat() + "Z"),
            "raven_overhead": {"tokens": 0, "cost_usd": 0.0, "calls": 0, "by_source": {}},
            "user_work": {
                "tokens": 0,
                "cost_usd": 0.0,
                "calls": 0,
                "tier_counts": {"SIMPLE": 0, "MEDIUM": 0, "COMPLEX": 0, "LOCAL_ONLY": 0},
                "last_classification": None,
            },
            "providers": {},
        }

    # Update the appropriate bucket
    bucket = data[source] if source in ("user_work", "raven_overhead") else data["user_work"]
    bucket["calls"] += 1
    if source == "user_work":
        bucket["tier_counts"][tier] = bucket["tier_counts"].get(tier, 0) + 1
        bucket["last_classification"] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "user_query_hash": hashlib.sha256(prompt.encode()).hexdigest()[:16],
            "tier": tier,
            "score": score,
            "reasons": reasons,
            "model_for_tier": model,
        }

    # Write atomically
    try:
        session_file.write_text(json.dumps(data, indent=2))
        return session_file
    except Exception as e:
        print(f"Error writing {session_file}: {e}", file=sys.stderr)
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Classify query into model tier (SIMPLE/MEDIUM/COMPLEX/LOCAL_ONLY)"
    )
    parser.add_argument("--prompt", required=True, help="User query text")
    parser.add_argument("--context", default="", help="Additional context (JSON or text)")
    parser.add_argument("--write-json", action="store_true", help="Write result to .raven/.model-session.json")
    parser.add_argument("--source", default="user_work",
                        choices=["user_work", "raven_overhead"],
                        help="Attribution bucket: user_work (default) or raven_overhead")
    parser.add_argument("--hook", action="store_true",
                        help="Emit plain-text toaster (first line) + RAVEN_MODEL_TIER "
                             "context instead of JSON — for Codex prompt injection")

    args = parser.parse_args()

    # Method B inference — if called from a hook context, override to overhead
    # CODEX_HOOK_EVENT is set by Codex when a hook fires
    if os.environ.get("CODEX_HOOK_EVENT") and args.source == "user_work":
        # Still default to user_work because the user prompt IS user work,
        # even though model-router runs from a hook. The hook FIRES it but
        # the work being classified IS the user's. Leave as user_work.
        pass

    # Classify
    tier, score, reasons, model = classify(args.prompt, args.context)
    cloud_param, resolved = resolve_model(tier)

    result = {
        "tier": tier,
        "score": score,
        "reasons": reasons,
        "model": resolved,
        "source": args.source,
    }
    if tier == "LOCAL_ONLY":
        result["local_only"] = True
        result["guidance"] = (
            "Secrets in context — cloud calls are blocked. Run the local model "
            f"({resolved} via ollama) or proceed in-context without spawning.")
    elif cloud_param is None:
        # Non-privacy tier configured to a local model; cloud fallback allowed
        # but must be visible.
        result["cloud_fallback"] = True

    if args.hook:
        # Plain-text emission: toaster first line (user-visible), then model
        # guidance for the session. Raven never routes silently.
        if tier == "LOCAL_ONLY":
            toast = ("🔒 Raven router · secrets detected → LOCAL_ONLY · "
                     "cloud calls blocked, local model only")
        else:
            cats = sorted({r.split(":", 1)[0] for r in reasons})[:2]
            toast = f"🔀 Raven router · {tier} → {resolved} · {', '.join(cats) or 'baseline'}"
        print(toast)
        print(f"RAVEN_MODEL_TIER={tier}")
        if tier == "LOCAL_ONLY":
            print(result["guidance"])
        else:
            print(f"Route subagent/specialist work to {resolved} for this prompt.")
    else:
        print(json.dumps(result, indent=2))

    # Optionally write to session file
    if args.write_json:
        session_file = write_session_json(tier, score, reasons, model, args.prompt, source=args.source)
        print(f"# Written to {session_file} (bucket: {args.source})", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
