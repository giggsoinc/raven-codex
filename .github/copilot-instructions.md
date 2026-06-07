# Raven-Codex — GitHub Copilot Instructions

## MANDATORY FIRST STEP — Every Session, No Exceptions

**Invoke Andie before anything else.**

Andie (`skills/andie/SKILL.md`) is the orchestration layer for all work in this session. It is not optional. It is not skippable.

```
Step 1: Load Andie
Step 2: Andie runs PRE-FLIGHT (context, framework, team, token budget)
Step 3: Andie routes to the correct specialist skill
Step 4: Work begins
```

Do not invoke any specialist skill directly. Do not start writing code. Do not run raven_status. **Load Andie. Run PRE-FLIGHT. Then proceed.**

---

## Why Andie First

Without PRE-FLIGHT, Codex picks the nearest-looking skill and starts. That is the wrong behavior. Andie captures what you actually need, recommends the right framework, searches the skill library for the best specialist, and assembles the right team before any work starts.

---

## Andie Routes To

| Request type | Andie invokes |
|---|---|
| Technical domain question | FeynTech mode → domain specialist |
| Architecture / design decision | Drama mode → expert panel |
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
- `codex-mem` — session memory, loads prior decisions
- `task-observer` — silent log of corrections and patterns

---

## Manifest Rules

- Manifest exists → load it, trust it, proceed. Do not reinitialize.
- No manifest → run `/raven-init`. Ask the user everything. Never auto-detect from venv, requirements.txt, or project files.

---

## Non-Negotiable

```
1. Andie first — always
2. No secrets in code or logs
3. No library without approval flow
4. No commit without passing guard agents
5. No code before architecture diagram exists
```
