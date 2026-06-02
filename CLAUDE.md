# CODEX.md — Raven-Codex (Codex)

## Mandatory First Step

**Use Andie as the compact routing layer before complex work.**

Andie (`skills/andie/SKILL.md`) classifies the request, preserves HITL/OODA discipline, and hands off executable plans. Brownfield bugs, regressions, stack traces, and debug tasks route directly to Andie Jr (`skills/andie-jr/SKILL.md`).

```
Step 1: Load Andie
Step 2: If this is brownfield/debug work, hand off to Andie Jr
Step 3: Otherwise Andie plans and routes to the right specialist
Step 4: Specialist execution begins after handoff
```

Do not use full Andie ceremony for bug fixes. Do not execute implementation as Andie; Andie plans and hands off.

---

## Why Andie First

Without routing, Codex can pick the nearest-looking specialist and skip context. Andie keeps the plan coherent, while Andie Jr keeps brownfield debugging fast.

---

## Andie Routes To

| Request type | Route |
|---|---|
| Brownfield bug / debug / stack trace | `andie-jr` |
| Technical domain question | Andie Deep plan → domain specialist |
| Architecture / design decision | Andie Drama plan → specialist execution |
| DB work | `db-specialist` or `postgres-specialist` |
| Cloud infra | `aws-specialist` / `gcp-specialist` / `azure-specialist` / `oci-specialist` |
| Security | `security-specialist` or `raven-security` |
| K8s / Terraform | `k8s-specialist` / `terraform-specialist` |
| Agent design | `agent-chaining` |
| Logging / observability | `log-management-specialist` |
| Unknown domain | `dynamic-specialist` — searches and constructs expert on demand |

---

## Guard Agents — Always On

These run silently behind every action. Do not disable them.

- `manifest-checker` — hard block if manifest missing
- `stack-validator` — wrong stack = hard block
- `style-enforcer` — advise during coding, block at commit
- `architecture-guard` — no diagram = warn → block after 24h
- `db-guard` — inline SQL, missing ERD, broken migrations
- `skill-guard` — no skill reads secrets or .env
- `claude-mem` — session memory, loads prior decisions
- `task-observer` — silent log of corrections and patterns

---

## Manifest Rules

- Manifest exists → load it, trust it, proceed. Do not reinitialize.
- No manifest + existing code (brownfield) → run `/raven-init`. Auto-discover stack from filesystem signals. Ask user to confirm.
- No manifest + empty folder (greenfield) → run `/raven-init`. Ask the user everything interactively.

---

## Non-Negotiable

```
1. Andie routes first; Andie Jr handles brownfield bugs
2. No secrets in code or logs
3. No library without approval flow
4. No commit without passing guard agents
5. No code before architecture diagram exists
```
