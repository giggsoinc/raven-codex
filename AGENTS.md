# CLAUDE.md — Raven-Codex

## Session Start — Mandatory

Before doing anything else, invoke **Andie** as the orchestration layer:

```
/andie
```

Andie runs PRE-FLIGHT — captures context, recommends the right framework, searches for the relevant specialist skill, assembles a team if needed, and presents an assembly card for approval before any work starts.

**Do not go directly to a specialist skill.** All specialist skills are loaded through Andie's routing after pre-flight completes.

---

## Skill Routing — Through Andie

| User request | Andie routes to |
|---|---|
| Technical domain question | FeynTech mode → domain specialist |
| Architecture / design decision | Drama mode → expert panel |
| DB work | db-specialist or postgres-specialist |
| Cloud infra | aws / gcp / azure / oci specialist |
| Security audit | security-specialist or raven-security |
| K8s / Terraform | k8s-specialist or terraform-specialist |
| Agent design | agent-chaining skill |
| Logging / observability | log-management-specialist |
| Unknown domain | dynamic-specialist — searches and constructs expert on demand |

---

## Guard Agents — Always On

10 guard agents run silently behind every action:

- **manifest-checker** — hard block if manifest missing
- **stack-validator** — wrong stack = hard block
- **style-enforcer** — advise during coding, block at commit
- **architecture-guard** — no diagram = warn → block after 24h
- **db-guard** — inline SQL, missing ERD, broken migrations
- **skill-guard** — no skill reads secrets or .env files
- **claude-mem** — session memory, loads prior decisions
- **task-observer** — silent log of corrections and patterns

---

## Non-Negotiable Rules

```
1. Always start with /andie — never go directly to a specialist
2. No secrets in code or logs — ever
3. No library without approval flow
4. No commit without passing guard agents
5. No code before architecture diagram exists
```
