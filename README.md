# Raven-Codex v4.1

AI coding discipline for OpenAI Codex, GitHub Copilot, and any MCP-compatible agent.

CVE scanning · secret detection · PR gates · audit logs · 61 specialist skills · 10 guard agents · engine scripts.

Andie greets you on first use. ≤2 questions. No bash. No 8-question wizard.

---

## Install

Raven-Codex enforces discipline through three platform-agnostic channels: an **MCP server** (tool-level checks), a **GitHub PR gate** (server-side enforcement on every PR), and **AGENTS.md** (instruction layer your agent reads automatically).

### 1. OpenAI Codex CLI — MCP server (90 seconds)

```bash
# Clone the engine
bash <(curl -fsSL https://raw.githubusercontent.com/giggsoinc/raven-codex/main/install.sh)
```

Then merge the snippet from [`config.toml.example`](config.toml.example) into `~/.codex/config.toml`:

```toml
[mcp_servers.raven]
command = "python3"
args = ["/Users/YOUR_USERNAME/.raven-codex/mcp/server.py"]
```

Restart Codex and ask it to run `raven_status`. That's it — the `raven_*` tools are now available.

### 2. GitHub PR gate — enforced on every PR

Copy [`.github/workflows/raven-pr-gate.yml`](.github/workflows/raven-pr-gate.yml) into your repo and run `raven-setup` to create `.raven/manifest.json`. The gate posts a `discipline-check` status on each PR: CVE scan · secret detection · manifest validation. Make it a required check in branch protection to hard-block merges.

### 3. Per-project setup

```bash
cd YourProject && raven-codex-setup
```

Writes `.raven/manifest.json`, hook scripts, and the local git pre-commit gate.

---

## 💰 Cost-Aware Routing — Built In

Raven classifies every prompt and routes it to the cheapest adequate model:

| Tier | Triggers | Approx cost |
|------|----------|-------------|
| **SIMPLE** | "fix typo", "rename var", single-file edits | lowest tier |
| **MEDIUM** | tests, docs, debug, refactor scope | mid tier |
| **COMPLEX** | architecture, security audit, multi-file reasoning | top tier |
| **LOCAL_ONLY** | secrets detected in prompt, offline mode | free, on-machine |

- **Session token counter + cost shown in banner** every session start.
- **Stop event writes session summary** to `~/RavenVault/sessions/` (Obsidian-compatible).
- **Secrets in your prompt** → automatically forced to a local model. The cloud never sees them.
- **No telemetry. Local-only.** All cost data stays on your machine.

Configure via `.raven/.model.env` — `raven-init` writes it for you.

---

## What's Included

| Component | Count | What it does |
|---|---|---|
| Specialist skills | 61 | Andie · Andie Jr · agent-chaining · ui-router · DB · cloud · security · Oracle (6 specialists) · Salesforce · Odoo · AI/ML · Kafka · K8s · Terraform · FastAPI · log management and more |
| Guard agents | 10 | Always-on discipline — blocks inline SQL, secrets, undeclared stacks, missing architecture |
| Slash commands | 14 | `/raven-init` `/raven-harden` `/raven-debug` `/raven-incident` `/raven-registry-sync` `/raven-approve` `/raven-scaffold` `/raven-search` `/raven-sync` and more |
| Engine scripts | 13 | cve-check · secret-scan · audit-log · emit-violation · db-guard · schema-guard · cve-prompt-guard · pr-gate · obsidian-log · session-start and more |
| MCP server | 1 | `raven_status` · `raven_debug` · `raven_cve_check` · `raven_violation` · `raven_sync_libs` |

---

## Performance

Token cost is a first-class design constraint. Skills load once on invocation and remain in the context window — smaller skills mean every subsequent message is cheaper.

| Optimisation | Saving |
|---|---|
| Andie (−69% size, 200-word cap, Feynman recap) | −6,852 tok per session |
| db-router pure routing table | −2,560 tok per session |
| ui-router trimmed | −1,564 tok per session |
| agent-chaining trimmed | −1,686 tok per session |
| Obsidian → session-start continuity | ~80 tok of prior context, no cold start |

**~57% reduction in skill token footprint vs v2.9.1. In a 20-message session: ~53% fewer context-tokens carried.**

---

## 🪙 Tokenomics — what Raven costs per message

**Enforcement is free. Routing is cheap. Skills are the spend — paid once, only when invoked.**

| Layer | Per-prompt tokens | When |
|---|---|---|
| Skill-routing gate (`raven-skill-gate`) | **0** | out-of-band: pre-commit exit code, Cursor shell-deny, MCP — never injected context |
| Router emission (triage **or** architect — mutually exclusive, never both) | ~120–145 | only when routing fires; data-only / trivial prompts inject **0** |
| Model-router toaster (`--hook`) | ~55 | per prompt, if wired |
| Session-start banner | ~455 | once per session |
| Specialist skill load (andie ~3.6k · andie-jr ~1.5k) | one-time | only on invocation; one mode file, never all four |

Worst case ≈ 175 tokens/prompt (~$0.0004 on gpt-4o); typical ≈ 55; many prompts 0. Overhead is metered separately from your work in `.raven/.model-session.json` (`raven_overhead` vs `user_work`) — watch it live at `http://127.0.0.1:9787` via `scripts/dashboard-server.py`.

Full note: [docs/TOKENOMICS.md](docs/TOKENOMICS.md) · Diagrams: [business view](docs/Agent_token_architecture_business.html) · [tech view](docs/Agent_token_architecture_tech.html)

---

## Relationship to giggsoinc/raven

`raven-codex` is the **OpenAI Codex / Copilot / multi-platform** variant.
`giggsoinc/raven` is the **IDE-native** variant.

Both share the same skill set and guard agents. Skills, agents, and engine scripts are kept in sync.

---

## Docs

- [Test environment guide](CODEX-TEST-GUIDE.md)
- [Issues](https://github.com/giggsoinc/raven-codex/issues)

---

*Guardrails before you ship. — [Giggso / AntiGravity Projects](https://github.com/giggsoinc)*
