# Raven-Codex

AI coding discipline for OpenAI Codex, GitHub Copilot, and Claude Code.

CVE scanning · secret detection · PR gates · audit logs · 23 specialist skills · 10 guard agents.

---

## Install — Claude Code

```bash
claude plugin install giggsoinc/raven-codex
```

## Install — Project Hooks + Engine Scripts

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/giggsoinc/raven-codex/main/install.sh)
```

Installs `.raven/manifest.json`, hook scripts (CVE check, secret scan, db-guard, audit log), and git pre-commit gate.

---

## What's Included

| Component | Count | What it does |
|---|---|---|
| Specialist skills | 23 | DB · cloud · security · Salesforce · Odoo · AI/ML · Kafka · K8s · Terraform · FastAPI · agent chaining · log management and more |
| Guard agents | 10 | Always-on discipline — blocks inline SQL, secrets, undeclared stacks, missing architecture |
| Slash commands | 10 | `/raven-init` `/raven-harden` `/raven-debug` `/raven-incident` `/raven-registry-sync` and more |
| Engine scripts | 5 | cve-check · secret-scan · audit-log · emit-violation · db-guard |
| MCP server | 1 | `raven_status` · `raven_debug` · `raven_cve_check` · `raven_violation` |

---

## Relationship to giggsoinc/raven

`raven-codex` is the **Codex / Copilot / multi-platform** variant.
`giggsoinc/raven` is the **Claude Code native** variant.

Both share the same skill set and guard agents. `raven-codex` is maintained in sync with the `codex/` subdirectory of the [raven monorepo](https://github.com/giggsoinc/raven/tree/main/codex).

---

## Docs

- [How to use](https://github.com/giggsoinc/raven/blob/main/codex/HOW-TO-USE.md)
- [Architecture](https://github.com/giggsoinc/raven)
- [Issues](https://github.com/giggsoinc/raven-codex/issues)

---

*Guardrails before you ship. — [Giggso / AntiGravity Projects](https://github.com/giggsoinc)*
