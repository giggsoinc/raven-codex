# Raven Tokenomics — what the discipline layer actually costs

Raven's promise is discipline without a token tax. This note states the
measured cost of every component, where it lands (per-prompt vs per-session),
and how to watch it. Figures measured on this repo, ~4 chars/token.

## The headline

**Enforcement is free. Routing is cheap. Skills are the spend — and they are
paid once, only when invoked.**

The skill-routing gate (`raven-skill-gate.py`) costs **0 tokens per message**:
it enforces via git pre-commit exit codes, Cursor shell-deny, and MCP calls —
out-of-band channels, never injected context.

## Per-prompt (recurring) costs

| Component | Payload | Tokens | Fires |
|---|---|---|---|
| triage-router emission | 487 chars | ~120 | only when routing to andie-jr |
| architect-router emission | 577 chars | ~145 | only when routing to andie |
| model-router `--hook` toaster | 212 chars | ~55 | every prompt (if wired) |
| raven-skill-gate | 0 | **0** | out-of-band |

Three design rules keep this flat:

1. **Mutual exclusion (routers v4.2)** — at most ONE router fires per prompt.
   The pre-v4.2 double-fire (both banners at once) is gone.
2. **Silent paths inject nothing** — data-only questions, trivial bounded
   edits, and decision-prompts-on-triage emit zero bytes.
3. Toasters ride inside the same emission; visibility costs no extra line.

Worst case per prompt: ~175 tokens. Typical: ~55. Many prompts: 0.

## Per-session (one-time) costs

| Component | Tokens | Notes |
|---|---|---|
| session-start banner | ~455 | once, includes gate mode + domain signal |
| skill marker confirmation | ~24 | once per gated skill |
| andie SKILL.md load | ~3,600 | only when invoked; ONE mode file extra, never all four |
| andie-jr SKILL.md load | ~1,500 | only when invoked |

The gate protects exactly this spend: if a session pays ~3.6k tokens to load
a specialist, the ~120-token router nudge plus the zero-token commit gate
ensure that investment isn't wasted by skipping the skill.

## In money (gpt-4o input, ~$2.50/M tokens)

- Worst-case per-prompt routing overhead: **~$0.0004**
- Full Andie session including skill load: **~$0.01**
- Skill-gate enforcement: **$0.00**

## How to monitor

Every router emission calls `log_overhead()`, which attributes tokens to the
`raven_overhead` bucket — separate from `user_work` — in
`.raven/.model-session.json`:

```json
{
  "raven_overhead": {"tokens": 0, "cost_usd": 0.0, "calls": 0, "by_source": {}},
  "user_work":      {"tokens": 0, "tier_counts": {...}, "last_classification": {...}}
}
```

- **Live dashboard** — `python3 scripts/dashboard-server.py` →
  http://127.0.0.1:9787 (raw numbers at `/metrics.json`).
- **Per-session summary** — written to `~/RavenVault/sessions/` on Stop
  (Obsidian-compatible).
- **Gate activity** — overrides and soft/shadow violations append to
  `docs/observations/security_log.md`; skill invocations to
  `.raven/state/skill-invocations.jsonl`.
- **Visual reference** — `docs/Agent_token_architecture_business.html`
  (owner view) and `docs/Agent_token_architecture_tech.html` (engineer view,
  reads `/metrics.json` live when the dashboard server is running).

If `raven_overhead` ever grows faster than ~175 tokens/prompt, something is
double-firing — that is the regression signal to watch.
