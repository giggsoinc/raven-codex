# Raven Skill-Routing Gate

Raven's specialist routing used to be advisory-only: routers injected
"invoke `andie-jr` before any file read" as context, and the model decided
whether to comply. Sometimes it routed; sometimes it diagnosed and edited
directly. The gate applies the same two-tier model Raven already uses for
commits — advise while coding, hard-block at the boundary — to skill routing.

## Design — gate the action, not the intent

A gate cannot semantically detect "this prompt was a bug report," so it does
not classify prompts. It enforces one workflow invariant via marker files:
**code cannot reach a commit until a gated specialist skill has actually run
this session.**

### 1. Marker emission

Each gated skill records proof of invocation as its FIRST step:

```
python3 ~/.raven-codex/scripts/raven-mark-skill.py andie-jr
```

(or the MCP tool `raven_mark_skill`). This appends one JSON line
`{ts, skill, session_id}` to `.raven/state/skill-invocations.jsonl`.
The **script** stamps the timestamp — the model cannot back-date a marker.

### 2. The gate — `raven-skill-gate.py`

Reads `.raven/state/routing-policy.json`:

| Key | Meaning | Default |
|---|---|---|
| `mode` | `shadow` (log only) · `soft` (warn) · `hard` (block) | `soft` |
| `soft_until` | auto-set 7 days after first run; past it, soft escalates to hard | +7d |
| `gated_skills` | which markers satisfy the gate | `andie`, `andie-jr` |
| `scope` | globs the gate cares about (docs pass freely) | code files |
| `freshness_hours` | fallback window when session start is unknown | 4 |
| `override_uses` | actions allowed per override touch | 5 |

A marker is **fresh** when it is newer than the start of the current session
(from `.raven/.model-session.json`), falling back to the `freshness_hours`
window. No fresh marker + in-scope file + hard mode → exit code 2 with:

> BLOCKED by raven-skill-gate: no specialist skill invoked this session. …

### 3. Enforcement boundaries (host-honest)

OpenAI Codex CLI has **no pre-tool hooks** — the only channels it honors are
the MCP server and instruction files. Cursor's hooks can deny shell and MCP
calls but have **no blocking pre-edit event**. So the gate binds where these
hosts actually enforce:

| Boundary | Mechanism | Blocking? |
|---|---|---|
| `git commit` | `.git/hooks/pre-commit` → `raven-skill-gate.py --event commit` (installed by `raven-codex-setup.sh`) | YES — works everywhere |
| Cursor agent shell | `~/.cursor/hooks.json` `beforeShellExecution` → `--cursor-hook` denies `git commit` (see `docs/cursor-hooks.example.json`) | YES in Cursor |
| Codex / any MCP host | `raven_gate_check` MCP tool; AGENTS.md instructs calling it before edits | advisory check, hard at commit |
| Edits themselves | not physically blockable in Codex/Cursor — soft/shadow violations are logged to `docs/observations/security_log.md` | no (by host design) |

### 4. Escape hatch — audited, never silent

```
touch .raven/state/gate-override
```

allows the next N (default 5) gated actions; every use is logged to
`docs/observations/security_log.md` with a countdown, and the touch-file is
consumed when the allowance runs out. Discipline with accountability, not a
lockout.

### 5. Rollout

New installs start in `soft` for 7 days (`soft_until`), then escalate to
`hard` — the same grace-period pattern as architecture-guard. Existing
installs pick the gate up via re-running `raven-codex-setup.sh` (installs the
pre-commit hook + default policy) or `raven-registry-sync`.

## Honest scope

The gate guarantees the specialist skill **ran** — a marker proves invocation,
nothing more. It does not and cannot guarantee the skill's output was used
well. That residual gap is inherent to LLM systems and is stated here rather
than papered over. Where a host offers no blocking edit event, edit-time
enforcement degrades to logged observation, and the hard stop moves to the
commit boundary.
