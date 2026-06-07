# Changelog

All notable changes to Raven-Codex are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

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
