# Raven-Codex

AI coding discipline for OpenAI Codex, GitHub Copilot, and Claude Code.

CVE scanning · secret detection · PR gates · audit logs · 54 specialist skills · 10 guard agents · 13 engine scripts.

---

## Install — Claude Code

```bash
claude plugin install giggsoinc/raven-codex
```

## Install — Project Hooks + Engine Scripts

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/giggsoinc/raven-codex/main/install.sh)
```

Installs `.raven/manifest.json`, hook scripts (CVE check, secret scan, db-guard, audit log, schema-guard, session-start), and git pre-commit gate.

---

## What's Included

| Component | Count | What it does |
|---|---|---|
| Specialist skills | 54 | Andie v5.2 · Andie Jr · db-router · ui-router · DB · cloud · security · Oracle (6 specialists) · Salesforce · Odoo · AI/ML · Kafka · K8s · Terraform · FastAPI · agent chaining · log management and more |
| Guard agents | 10 | Always-on discipline — blocks inline SQL, secrets, undeclared stacks, missing architecture |
| Slash commands | 14 | `/raven-init` `/raven-harden` `/raven-debug` `/raven-incident` `/raven-registry-sync` `/raven-approve` `/raven-scaffold` `/raven-search` `/raven-sync` and more |
| Engine scripts | 13 | cve-check · secret-scan · audit-log · emit-violation · db-guard · schema-guard · cve-prompt-guard · pr-gate · server · obsidian-log · session-start and more |
| MCP server | 1 | `raven_status` · `raven_debug` · `raven_cve_check` · `raven_violation` · `raven_sync_libs` |

---

## Relationship to giggsoinc/raven

`raven-codex` is the **Codex / Copilot / multi-platform** variant.
`giggsoinc/raven` is the **Claude Code native** variant.

Both share the same skill set and guard agents. Skills, agents, and engine scripts are kept in sync with [giggsoinc/raven](https://github.com/giggsoinc/raven).

---

## Docs

- [Architecture](https://github.com/giggsoinc/raven)
- [Issues](https://github.com/giggsoinc/raven-codex/issues)

---

*Guardrails before you ship. — [Giggso / AntiGravity Projects](https://github.com/giggsoinc)*
