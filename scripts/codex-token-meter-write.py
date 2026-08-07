#!/usr/bin/env python3
"""Raven Stop hook: delta token/cost meter.

Reads a Codex/assistant transcript JSONL, records only newly observed assistant
usage events, and keeps full-transcript verification separate from accumulated
deltas. This avoids the old bug where every Stop trigger re-added the whole
transcript to monthly totals.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PRICING_FILE = Path(__file__).parent / "model-pricing.json"
RAVEN_DIR = Path.cwd() / ".raven"
AUDIT_DIR = RAVEN_DIR / "audit"
CHECKPOINT_FILE = RAVEN_DIR / ".token-meter-checkpoint.json"
LOCK_FILE = RAVEN_DIR / ".token-meter.lock"
SESSION_FILE = RAVEN_DIR / ".model-session.json"
COST_LOG = RAVEN_DIR / "cost-log.jsonl"
COST_VERIFY = RAVEN_DIR / ".cost-verify.json"
VAULT_METRICS = Path.home() / "RavenVault" / ".metrics"


@dataclass
class UsageEvent:
    """One observed assistant model usage row."""

    event_id: str
    session_id: str
    timestamp: str
    model: str
    actor: str
    bucket: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_creation_tokens: int
    computed_cost_usd: float
    estimated_cost_usd: float
    pricing_source: str

    @property
    def tokens(self) -> int:
        return self.input_tokens + self.output_tokens


def utc_now() -> str:
    """Current UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any) -> Any:
    """Load JSON fail-soft."""
    try:
        return json.loads(path.read_text()) if path.exists() else default
    except Exception:
        return default


def write_json(path: Path, data: Any) -> None:
    """Atomically write JSON with parent directory creation."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    os.replace(tmp, path)


@contextlib.contextmanager
def meter_lock():
    """Best-effort interprocess lock for Stop-hook state writes."""
    RAVEN_DIR.mkdir(parents=True, exist_ok=True)
    handle = LOCK_FILE.open("w")
    try:
        try:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        except Exception:
            pass
        yield
    finally:
        try:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass
        handle.close()


def load_pricing() -> dict[str, dict[str, float]]:
    """Load model pricing from local config."""
    data = load_json(PRICING_FILE, {})
    models = data.get("models", {}) if isinstance(data, dict) else {}
    default = data.get("default", {"input_per_1m": 1, "output_per_1m": 5})
    return {"models": models, "default": default}


def price_for(model: str, pricing: dict[str, Any]) -> tuple[dict[str, float], str]:
    """Return model price and whether it was exact/default."""
    models = pricing.get("models", {})
    if model in models:
        return models[model], "model"
    return pricing.get("default", {"input_per_1m": 1, "output_per_1m": 5}), "default"


def cost_usd(model: str, usage: dict[str, int], pricing: dict[str, Any]) -> tuple[float, str]:
    """Compute cost with cache token multipliers."""
    price, source = price_for(model, pricing)
    input_rate = float(price.get("input_per_1m", 1))
    output_rate = float(price.get("output_per_1m", 5))
    cost = (
        usage["input_tokens"] / 1_000_000 * input_rate
        + usage["output_tokens"] / 1_000_000 * output_rate
        + usage["cache_read_tokens"] / 1_000_000 * input_rate * 0.1
        + usage["cache_creation_tokens"] / 1_000_000 * input_rate * 1.25
    )
    return round(cost, 8), source


def message_from(entry: dict[str, Any]) -> dict[str, Any]:
    """Return the assistant message payload for common transcript shapes."""
    msg = entry.get("message")
    if isinstance(msg, dict):
        return msg
    return entry


def role_from(entry: dict[str, Any], msg: dict[str, Any]) -> str:
    """Extract role across transcript variants."""
    return str(msg.get("role") or entry.get("role") or entry.get("type") or "")


def usage_from(entry: dict[str, Any], msg: dict[str, Any]) -> dict[str, int] | None:
    """Extract usage from known Codex/OpenAI-style shapes."""
    raw = msg.get("usage") or entry.get("usage") or entry.get("response", {}).get("usage")
    if not isinstance(raw, dict):
        return None
    usage = {
        "input_tokens": int(raw.get("input_tokens") or raw.get("prompt_tokens") or 0),
        "output_tokens": int(raw.get("output_tokens") or raw.get("completion_tokens") or 0),
        "cache_read_tokens": int(raw.get("cache_read_input_tokens") or raw.get("cached_input_tokens") or 0),
        "cache_creation_tokens": int(raw.get("cache_creation_input_tokens") or 0),
    }
    if not any(usage.values()):
        return None
    return usage


def tool_blocks(msg: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract tool-use-like blocks from a message."""
    blocks: list[dict[str, Any]] = []
    for key in ("tool_uses", "tool_calls"):
        val = msg.get(key)
        if isinstance(val, list):
            blocks.extend(x for x in val if isinstance(x, dict))
    content = msg.get("content")
    if isinstance(content, list):
        blocks.extend(x for x in content if isinstance(x, dict) and x.get("type") in {"tool_use", "function_call"})
    return blocks


def is_raven_event(entry: dict[str, Any], msg: dict[str, Any]) -> bool:
    """Detect Raven infrastructure usage without claiming perfect attribution."""
    text = json.dumps({"entry": entry, "message": msg}, sort_keys=True).lower()
    return any(
        marker in text
        for marker in (
            ".raven/",
            "/raven-codex/",
            "raven-",
            "raven_",
            "skills/andie",
            "codex-pre-tool-discipline",
        )
    )


def actor_from(entry: dict[str, Any], msg: dict[str, Any]) -> str:
    """Infer primary vs subagent from transcript metadata."""
    text = json.dumps({"entry": entry, "message": msg}, sort_keys=True).lower()
    if "subagent" in text or "sub_agent" in text or "multi-agent" in text:
        return "subagent"
    return "primary"


def stable_event_id(entry: dict[str, Any], msg: dict[str, Any], line_no: int) -> str:
    """Build a stable event id for dedupe."""
    for candidate in (
        entry.get("id"),
        entry.get("request_id"),
        entry.get("turn_id"),
        entry.get("uuid"),
        msg.get("id"),
        msg.get("request_id"),
    ):
        if candidate:
            return str(candidate)
    payload = json.dumps({"line": line_no, "entry": entry}, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()[:24]


def parse_transcript(transcript_path: str, fallback_session_id: str = "") -> list[UsageEvent]:
    """Parse transcript JSONL into usage events."""
    pricing = load_pricing()
    events: list[UsageEvent] = []
    path = Path(transcript_path)
    try:
        lines = path.read_text().splitlines()
    except Exception as exc:
        sys.stderr.write(f"Warning: failed to read transcript {transcript_path}: {exc}\n")
        return events

    for line_no, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(entry, dict):
            continue
        msg = message_from(entry)
        if role_from(entry, msg) != "assistant":
            continue
        usage = usage_from(entry, msg)
        if not usage:
            continue

        model = str(msg.get("model") or entry.get("model") or "unknown")
        computed, pricing_source = cost_usd(model, usage, pricing)
        session_id = str(
            entry.get("session_id")
            or entry.get("sessionId")
            or msg.get("session_id")
            or msg.get("sessionId")
            or fallback_session_id
            or path.stem
        )
        events.append(UsageEvent(
            event_id=stable_event_id(entry, msg, line_no),
            session_id=session_id,
            timestamp=str(entry.get("timestamp") or msg.get("timestamp") or utc_now()),
            model=model,
            actor=actor_from(entry, msg),
            bucket="raven_code" if is_raven_event(entry, msg) else "user_work",
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
            cache_read_tokens=usage["cache_read_tokens"],
            cache_creation_tokens=usage["cache_creation_tokens"],
            computed_cost_usd=computed,
            estimated_cost_usd=computed,
            pricing_source=pricing_source,
        ))
    return events


def empty_bucket() -> dict[str, Any]:
    """Metrics bucket shape used by the dashboard."""
    return {
        "tokens": 0,
        "input": 0,
        "output": 0,
        "cache_read": 0,
        "cache_creation": 0,
        "cost_usd": 0.0,
        "calls": 0,
    }


def add_event(bucket: dict[str, Any], event: UsageEvent) -> None:
    """Accumulate one event into a bucket."""
    bucket["calls"] += 1
    bucket["input"] += event.input_tokens
    bucket["output"] += event.output_tokens
    bucket["cache_read"] += event.cache_read_tokens
    bucket["cache_creation"] += event.cache_creation_tokens
    bucket["tokens"] += event.tokens
    bucket["cost_usd"] = round(bucket["cost_usd"] + event.computed_cost_usd, 8)


def summarize(events: list[UsageEvent], session_id: str = "") -> dict[str, Any]:
    """Summarize events into .model-session-compatible metrics."""
    metrics = {
        "session_id": session_id or (events[-1].session_id if events else ""),
        "session_started_at": events[0].timestamp if events else utc_now(),
        "timestamp": utc_now(),
        "model": events[-1].model if events else "unknown",
        "raven_code": empty_bucket(),
        "user_work": empty_bucket(),
    }
    by_model: dict[str, dict[str, Any]] = {}
    for event in events:
        add_event(metrics[event.bucket], event)
        by_model.setdefault(event.model, empty_bucket())
        add_event(by_model[event.model], event)

    total = empty_bucket()
    for bucket in (metrics["raven_code"], metrics["user_work"]):
        for key in ("tokens", "input", "output", "cache_read", "cache_creation", "calls"):
            total[key] += bucket[key]
        total["cost_usd"] = round(total["cost_usd"] + bucket["cost_usd"], 8)
    metrics["tokens"] = total["tokens"]
    metrics["total"] = total
    metrics["by_model"] = by_model
    return metrics


def load_checkpoint() -> dict[str, Any]:
    """Load token checkpoint."""
    checkpoint = load_json(CHECKPOINT_FILE, {"version": 1, "sessions": {}})
    if not isinstance(checkpoint, dict):
        return {"version": 1, "sessions": {}}
    checkpoint.setdefault("version", 1)
    checkpoint.setdefault("sessions", {})
    return checkpoint


def checkpoint_session(checkpoint: dict[str, Any], session_id: str) -> dict[str, Any]:
    """Get or create a checkpoint session."""
    sessions = checkpoint.setdefault("sessions", {})
    session = sessions.setdefault(session_id, {
        "seen_event_ids": [],
        "events": [],
        "cost_totals": {
            "session_cost_usd": 0.0,
            "month_cost_usd": {},
        },
        "updated_at": utc_now(),
    })
    session.setdefault("seen_event_ids", [])
    session.setdefault("events", [])
    session.setdefault("cost_totals", {"session_cost_usd": 0.0, "month_cost_usd": {}})
    session["cost_totals"].setdefault("session_cost_usd", 0.0)
    session["cost_totals"].setdefault("month_cost_usd", {})
    return session


def apply_delta(events: list[UsageEvent], session_id: str) -> tuple[list[UsageEvent], dict[str, Any]]:
    """Return new events and update checkpoint in memory."""
    checkpoint = load_checkpoint()
    session = checkpoint_session(checkpoint, session_id)
    seen = set(session.get("seen_event_ids", []))
    delta = [event for event in events if event.event_id not in seen]

    for event in delta:
        session["seen_event_ids"].append(event.event_id)
        session["events"].append(event.__dict__)
    session["updated_at"] = utc_now()
    return delta, checkpoint


def checkpoint_events(checkpoint: dict[str, Any], session_id: str) -> list[UsageEvent]:
    """Rehydrate checkpoint events for a session."""
    raw = checkpoint_session(checkpoint, session_id).get("events", [])
    events: list[UsageEvent] = []
    for item in raw:
        try:
            events.append(UsageEvent(**item))
        except TypeError:
            continue
    return events


def append_cost_log(events: list[UsageEvent], session: dict[str, Any]) -> None:
    """Append one cost-log row per newly observed model event."""
    if not events:
        return
    RAVEN_DIR.mkdir(parents=True, exist_ok=True)
    totals = session.setdefault("cost_totals", {"session_cost_usd": 0.0, "month_cost_usd": {}})
    totals.setdefault("session_cost_usd", 0.0)
    totals.setdefault("month_cost_usd", {})
    with open(COST_LOG, "a") as f:
        for event in events:
            month = event.timestamp[:7]
            totals["session_cost_usd"] = round(float(totals.get("session_cost_usd", 0.0)) + event.computed_cost_usd, 8)
            month_totals = totals["month_cost_usd"]
            month_totals[month] = round(float(month_totals.get(month, 0.0)) + event.computed_cost_usd, 8)
            row = {
                "logged_at": utc_now(),
                "session_id": event.session_id,
                "event_id": event.event_id,
                "turn_timestamp": event.timestamp,
                "model": event.model,
                "actor": event.actor,
                "bucket": event.bucket,
                "input_tokens": event.input_tokens,
                "output_tokens": event.output_tokens,
                "cache_read_tokens": event.cache_read_tokens,
                "cache_creation_tokens": event.cache_creation_tokens,
                "estimated_cost_usd": event.estimated_cost_usd,
                "computed_cost_usd": event.computed_cost_usd,
                "cumulative_session_cost_usd": totals["session_cost_usd"],
                "cumulative_month_cost_usd": month_totals[month],
                "pricing_source": event.pricing_source,
            }
            f.write(json.dumps(row, sort_keys=True) + "\n")


def update_monthly(delta_events: list[UsageEvent]) -> None:
    """Update monthly rollup using only delta events."""
    if not delta_events:
        return
    VAULT_METRICS.mkdir(parents=True, exist_ok=True)
    by_month: dict[str, list[UsageEvent]] = defaultdict(list)
    for event in delta_events:
        try:
            ts = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
        except Exception:
            ts = datetime.now(timezone.utc)
        by_month[ts.strftime("%Y-%m")].append(event)

    for month, events in by_month.items():
        path = VAULT_METRICS / f"{month}.json"
        data = load_json(path, {"sessions": 0, "total": {}, "by_day": {}})
        data.setdefault("sessions", 0)
        data.setdefault("total", {})
        data.setdefault("by_day", {})
        data.setdefault("session_ids", [])
        known_sessions = set(data.get("session_ids", []))
        seen_sessions = {event.session_id for event in events}
        new_sessions = sorted(seen_sessions - known_sessions)
        data["session_ids"].extend(new_sessions)
        data["sessions"] = len(set(data["session_ids"]))
        for event in events:
            try:
                day = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00")).strftime("%Y-%m-%d")
            except Exception:
                day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            data["by_day"].setdefault(day, {"sessions": 0, "tokens": 0, "cost_usd": 0.0})
            data["by_day"][day].setdefault("session_ids", [])
            day_sessions = set(data["by_day"][day].get("session_ids", []))
            if event.session_id not in day_sessions:
                data["by_day"][day]["session_ids"].append(event.session_id)
            data["by_day"][day]["sessions"] = len(set(data["by_day"][day]["session_ids"]))
            data["by_day"][day]["tokens"] += event.tokens
            data["by_day"][day]["cost_usd"] = round(data["by_day"][day]["cost_usd"] + event.computed_cost_usd, 8)
            data["total"]["tokens"] = data["total"].get("tokens", 0) + event.tokens
            data["total"]["cost_usd"] = round(data["total"].get("cost_usd", 0.0) + event.computed_cost_usd, 8)
        write_json(path, data)


def write_audit(delta_events: list[UsageEvent], metrics: dict[str, Any], verified: bool) -> None:
    """Append a compact audit event only when new usage was observed or verification failed."""
    if not delta_events and verified:
        return
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    entry = {
        "timestamp": utc_now(),
        "event": "token-meter",
        "session_id": metrics.get("session_id", ""),
        "delta_events": len(delta_events),
        "delta_tokens": sum(event.tokens for event in delta_events),
        "delta_cost_usd": round(sum(event.computed_cost_usd for event in delta_events), 8),
        "session_tokens": metrics["total"]["tokens"],
        "session_cost_usd": metrics["total"]["cost_usd"],
        "verified": verified,
    }
    with open(AUDIT_DIR / f"{date}.log", "a") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")


def verify_cost(path_a: dict[str, Any], full_events: list[UsageEvent]) -> dict[str, Any]:
    """Compare accumulated deltas against independent full-transcript recompute."""
    path_a_cost = float(path_a.get("total", {}).get("cost_usd", 0.0))
    path_b = summarize(full_events, path_a.get("session_id", ""))
    path_b_cost = float(path_b.get("total", {}).get("cost_usd", 0.0))
    diff = abs(path_a_cost - path_b_cost)
    baseline = max(path_b_cost, 0.00000001)
    divergence = diff / baseline
    result = {
        "verified": divergence <= 0.05,
        "checked_at": utc_now(),
        "path_a_accumulated_delta_cost_usd": round(path_a_cost, 8),
        "path_b_full_recompute_cost_usd": round(path_b_cost, 8),
        "divergence_ratio": round(divergence, 8),
        "threshold_ratio": 0.05,
    }
    write_json(COST_VERIFY, result)
    return result


def main() -> None:
    """Read Stop hook stdin, parse transcript, write delta metrics."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transcript", help="transcript JSONL path")
    args = parser.parse_args()

    try:
        hook_input = json.load(sys.stdin) if not sys.stdin.isatty() else {}
    except Exception:
        hook_input = {}

    transcript_path = args.transcript or hook_input.get("transcript_path", "")
    if not transcript_path:
        sys.stderr.write("No transcript_path in hook input; skipping metrics\n")
        return

    fallback_session_id = str(
        hook_input.get("session_id")
        or hook_input.get("sessionId")
        or Path(transcript_path).stem
    )
    full_events = parse_transcript(transcript_path, fallback_session_id)
    session_id = full_events[-1].session_id if full_events else fallback_session_id

    with meter_lock():
        delta_events, checkpoint = apply_delta(full_events, session_id)
        session = checkpoint_session(checkpoint, session_id)
        append_cost_log(delta_events, session)
        write_json(CHECKPOINT_FILE, checkpoint)
        accumulated_events = checkpoint_events(checkpoint, session_id)
        metrics = summarize(accumulated_events, session_id)

        write_json(SESSION_FILE, metrics)
        update_monthly(delta_events)
        verify = verify_cost(metrics, full_events)
        write_audit(delta_events, metrics, bool(verify.get("verified")))


if __name__ == "__main__":
    main()
