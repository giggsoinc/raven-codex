# Raven-Codex v3.4

AI coding discipline for OpenAI Codex, GitHub Copilot, and Claude Code.

CVE scanning · secret detection · PR gates · audit logs · 61 specialist skills · 10 guard agents · 13 engine scripts.

Andie greets you on install. ≤2 questions. No bash. No 8-question wizard.

---

## Install — 90 seconds, zero questions

1. Download [`raven-codex-plugin-v3.4.0.zip`](plugin/raven-codex-plugin-v3.4.0.zip)
2. Open Claude Desktop → Settings → Extensions → Add plugin → drop the zip
3. Open your project. Type anything.

Andie greets you, scans your project, builds the manifest — done.

> 👋 *"Hey, I'm Andie. I'm the mind of your installed Raven. Good — you have a keen ask for responsible and resilient AI. I noticed you don't have a manifest yet — to get Raven working, I need to scan your project and build one. OK to proceed?"*

That's it. No setup script. No 8 questions. Andie infers everything she can and asks at most 2.

<details>
<summary>Prefer terminal install? (advanced)</summary>

```bash
# Claude Code direct
claude plugin install giggsoinc/raven-codex

# Or curl-pipe (writes project hooks + engine scripts)
bash <(curl -fsSL https://raw.githubusercontent.com/giggsoinc/raven-codex/main/install.sh)
```

The terminal installer writes `.raven/manifest.json`, hook scripts, and git pre-commit gate. Most users don't need this — the plugin install does it via Andie on first use.
</details>

---

## What's Included

| Component | Count | What it does |
|---|---|---|
| Specialist skills | 61 | Andie v6.3 · Andie Jr · agent-chaining · ui-router · DB · cloud · security · Oracle (6 specialists) · Salesforce · Odoo · AI/ML · Kafka · K8s · Terraform · FastAPI · log management and more |
| Guard agents | 10 | Always-on discipline — blocks inline SQL, secrets, undeclared stacks, missing architecture |
| Slash commands | 14 | `/raven-init` `/raven-harden` `/raven-debug` `/raven-incident` `/raven-registry-sync` `/raven-approve` `/raven-scaffold` `/raven-search` `/raven-sync` and more |
| Engine scripts | 13 | cve-check · secret-scan · audit-log · emit-violation · db-guard · schema-guard · cve-prompt-guard · pr-gate · server · obsidian-log · session-start and more |
| MCP server | 1 | `raven_status` · `raven_debug` · `raven_cve_check` · `raven_violation` · `raven_sync_libs` |

---

## Performance

Token cost is a first-class design constraint. Skills load once on invocation and remain in the context window — smaller skills mean every subsequent message is cheaper.

| Optimisation | Saving |
|---|---|
| Andie v6.3 (−69% size, 200-word cap, Feynman recap) | −6,852 tok per session |
| db-router pure routing table | −2,560 tok per session |
| ui-router trimmed | −1,564 tok per session |
| agent-chaining trimmed | −1,686 tok per session |
| `raven-skill-reminder` first-message-only | −61 tok × every message after msg 1 |
| Obsidian → session-start continuity | ~80 tok of prior context, no cold start |

**~57% reduction in skill token footprint vs v2.9.1. In a 20-message session: ~53% fewer context-tokens carried.**

---

## Relationship to giggsoinc/raven

`raven-codex` is the **Codex / Copilot / multi-platform** variant.
`giggsoinc/raven` is the **Claude Code native** variant.

Both share the same skill set and guard agents. Skills, agents, and engine scripts are kept in sync.

---

## Docs

- [Issues](https://github.com/giggsoinc/raven-codex/issues)

---

*Guardrails before you ship. — [Giggso / AntiGravity Projects](https://github.com/giggsoinc)*
