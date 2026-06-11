# Changelog

All notable changes to Raven-Codex are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

---

## [Unreleased] — 2026-06-10

### Andie v6.4 — one hard gate, visible routing, LOCAL_ONLY hard floor

- **Andie v6.4** (skills/andie): one-message mode card + pre-flight with ONE GO,
  implicit GO (substantive input counts as consent), ask-once gates, GATES
  ledger in every OODA block, mandatory critic voice (Devil's Advocate / Critic /
  Red Team / Saboteur) + named USER seat with the casting vote. Invocation
  toaster: first line always announces what is running, what triggered it, and
  the next step — never "in the background". "OODA runs continuously" replaced
  with "checkpoint after each round".
- **Andie Jr v1.1** (skills/andie-jr): same invocation announcement + validation line.
- **Routers v4.2** (scripts/triage-router.py, architect-router.py): mutually
  exclusive precedence — force wins exclusively; symptom overrides data-only;
  decision/architecture intent → andie via architect-router with triage silent
  even on brownfield (kills the double-fire); trivial bounded edits route
  nowhere; brownfield → andie-jr; greenfield → andie. One source of truth:
  triage loads architect-router's DECISION/SYMPTOM classifier via importlib,
  fail-soft. Emission is plain text with a user-visible 🪶 toaster as the first
  line — Raven never routes silently. 9-case matrix: tests/test_routing_matrix.py.
- **Model routing** (scripts/model-router.py, agent/scripts/model-router-hook.py):
  LOCAL_ONLY is a hard floor — `resolve_model("LOCAL_ONLY")` never returns a
  cloud model, even when .model.env misconfigures the tier; secrets-laden
  context resolves to the local ollama model or in-context handling only.
  `--hook` flag emits a 🔀/🔒 toaster + RAVEN_MODEL_TIER guidance; non-privacy
  tiers flag `cloud_fallback` when applicable.

### Added — deterministic skill-routing gate (raven-skill-gate)

- Specialist routing is no longer advisory-only. Gated skills (andie,
  andie-jr) record a script-stamped invocation marker as their first step
  (scripts/raven-mark-skill.py → .raven/state/skill-invocations.jsonl, also
  exposed as MCP tool `raven_mark_skill`).
- scripts/raven-skill-gate.py enforces the marker at the boundaries Codex
  hosts actually honor: git pre-commit (installed by raven-codex-setup.sh),
  Cursor `beforeShellExecution` (denies `git commit`; see
  docs/cursor-hooks.example.json), and the `raven_gate_check` MCP tool.
  Codex CLI has no pre-tool hooks and Cursor has no blocking pre-edit event,
  so the hard stop lives at the commit boundary; edit-time violations are
  logged (docs/observations/security_log.md).
- Modes shadow/soft/hard via .raven/state/routing-policy.json with scope
  globs + freshness window (session start, fallback 4h). New installs start
  soft for 7 days, then escalate to hard (architecture-guard grace pattern).
- Escape hatch: `touch .raven/state/gate-override` allows the next N actions,
  every use logged with a countdown — never silent.
- Router/banner advisory text rewritten to state the real contract
  ("enforced at commit time by raven-skill-gate") instead of unenforceable
  "MANDATORY before any file read".
- Honest scope documented (docs/SKILL-GATE.md): the gate guarantees the
  skill RAN, not that its output was used well.
- Tests: tests/test_skill_gate.py — blocked/allowed/stale/shadow/override/
  <100ms, all green.

### Added — tokenomics documentation + packaging

- docs/TOKENOMICS.md: measured per-message cost of the discipline layer
  (gate 0 tok out-of-band; one router max ~120–145 tok; model toaster ~55;
  session banner ~455 once; skill loads 1.5–3.6k one-time). Regression
  signal: overhead >175 tok/prompt means a router is double-firing.
- README: 🪙 Tokenomics section; Docs index expanded; MCP tool list updated
  (raven_mark_skill, raven_gate_check); skill-routing gate row added.
- docs/Agent_token_architecture_business.html (owner view) and
  docs/Agent_token_architecture_tech.html (engineer view; live-polls
  dashboard-server /metrics.json with a >175 tok/call alarm).
- make-plugin.sh: bundles docs (SKILL-GATE, TOKENOMICS, architecture pages,
  cursor-hooks example) into the plugin zip.

### Fixed — DOMAIN_SKILL_MAP precision (false-positive Oracle)

- Oracle entry no longer claims `**/*.sql` — a stray migration/SQLite-schema/
  test-fixture .sql file is NOT an Oracle signal and was shadowing later
  entries like FastAPI. Keeps `.pkb`/`.pks` (strong), adds `tnsnames.ora`
  marker and `cx_Oracle`/`oracledb` keywords in requirements.txt + pyproject.toml.
- Kubernetes: `charts` dir removed (matched JS charting folders); `Chart.yaml`
  marker added; k8s/kubernetes/helm dirs are weak signals.
- AWS: generic `template.yaml` marker replaced with an `AWS::` content check.
- `detect_domain` now returns (skill, name, strength); strong matches beat
  earlier weak ones; weak hits emit an advisory 💡 DOMAIN HINT instead of the
  mandatory ⚡ banner. Regression: tests/test_domain_detection.py (10 fixtures).
- plugin/make-plugin.sh now packages router_common.py (router dependency).

---

## [4.1.0] — 2026-06-06

### Pure Codex Implementation

- Purged all Claude Code plugin layer (`.claude-plugin/`, `.claude/hooks`, `.claude/scripts` symlinks)
- Converted all scripts to OpenAI Codex-native: claude-* model refs → openai/gpt-4o*
- Routing now OpenAI-first: gpt-4o-mini (SIMPLE), gpt-4o (MEDIUM), o1 (COMPLEX)
- Renamed agent: `claude-mem` → `codex-mem` (session memory manager)
- Updated all paths: .claude/ → .codex/, .model.env uses [openai] section
- MCP server v4.1.0: Codex plugin via .mcp.json, config.toml.example for CLI
- GitHub Actions: added raven-pr-gate.yml for CVE checks on requirements.txt changes
- All prose references: "Claude" → "Codex" (except data sources: anthropics/skills GitHub repo kept)

---

## [3.4.0] — 2026-06-01

### Storage Architecture Refresh

- Plugin manifest bumped to v3.4.0 in both `.claude-plugin/` and `.codex-plugin/`.
- Description updated to reflect current architecture.
- 61 specialist skills, 10 guard agents — unchanged from prior version.
- Multi-platform routing maintained: Claude, OpenAI, Gemini, Perplexity, Manus.
- Plugin zip rebuilt: `raven-codex-plugin-v3.4.0.zip`.
- Backwards-compatible with v3.3.0 — structural updates only.

---

## [3.3.0] — 2026-05-27

- Andie v6.3 routing refresh.
- Auto-trigger fixes for andie/andie-jr/andie-guru.
- Guard audit + notification fix.

---

## [3.0.0] and earlier

See git history.
