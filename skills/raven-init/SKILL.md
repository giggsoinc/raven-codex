---
name: raven-init
description: Initialize Raven for a project. Auto-discovers stack on brownfield (existing code), asks interactively on greenfield (empty). Validates against schema, commits with audit trail.
allowed-tools: Read, Write, Edit, Bash
---

# /raven init

Initializes Raven for a project. On brownfield (existing code), auto-discovers stack and asks for confirmation. On greenfield (empty folder), asks questions one at a time. Generates manifest.json, validates, and commits.

---

## Pre-checks

1. Is `.raven/manifest.json` already present?
   - **YES** → Load it. Trust it. Proceed with the declared stack. Do not reinitialize. Do not modify unless user explicitly requests it.
   - **NO** → Continue to step 2.

2. Is Git initialized?
   - **NO** → Warn: "Git not initialized. Run `git init` first. Audit trail requires Git."

3. **Detect project type: Greenfield vs Brownfield**
   - Count source files in the directory (exclude hidden dirs, node_modules, venv, .venv, __pycache__)
   - **0 source files** → Greenfield. Run interactive creation (ask all questions).
   - **1+ source files** → Brownfield. Run auto-discovery below.

---

## Brownfield Auto-Discovery

When existing code is detected, auto-discover the stack from filesystem signals.
Only ask the user to **confirm** — never ask them to re-state what the code already tells you.

### Discovery scan

Run these checks:

| Signal | Files checked | Detected value |
|--------|--------------|----------------|
| Project name | Directory name | Use folder name (sanitized to `^[a-zA-Z0-9_-]+$`) |
| Work type | `.tf`/`.hcl` → infra; `.py`/`.ts`/`.go`/`.rs`/`.java` → code; both → mixed | Auto-set |
| Language | `*.py` → python (check version via `python3 --version` or pyproject.toml); `*.ts`/`tsconfig.json` → typescript; `*.go`/`go.mod` → go; `*.rs`/`Cargo.toml` → rust; `*.java`/`pom.xml` → java | Multi-select all found |
| Frontend | `next.config.*` → nextjs; `nuxt.config.*` → nuxtjs; `vite.config.*` + react → reactjs; `vite.config.*` + vue → vuejs; none → none | Auto-set |
| Cloud | `*.tf` with `provider "aws"` → aws; `provider "google"` → gcp; `provider "azurerm"` → azure; `provider "oci"` → oci; Dockerfile only → on-prem | Auto-set or ask if ambiguous |
| Database | `docker-compose.yml` service images; connection strings in config; ORM configs (alembic, prisma, TypeORM) | Multi-select all found |
| Infra tools | `Dockerfile` → docker-compose; `*.tf` → terraform; `helm/`/`Chart.yaml` → helm; `k8s/`/`*deployment.yaml` → kubernetes; `ansible/`/`playbook.yml` → ansible | Multi-select all found |

### Confidence output

Present findings as a confirmation, not questions:

```
🔍 Brownfield detected — auto-discovered stack:

  Project:    {name}
  Type:       {work_type}
  Language:   {languages}
  Frontend:   {framework}
  Cloud:      {cloud}
  Database:   {databases}
  Infra:      {tools}

✅ Accept this? (y/n)
  - y → proceed with these values
  - n → switch to interactive mode (ask each question)
```

If a field cannot be determined with confidence → mark as `⚠️ unknown` and ask only that one question.

### Remaining questions (always asked even in brownfield)

- **Email** (Q8) — cannot be discovered from code
- **Guard enabled** (Q9) — policy decision, not a code signal

---

## First-Run Admin Detection (Enterprise Only)

Check for `~/.raven/org-admin.json` (global) or `.raven/org-admin.json` (project override).

**No admin config found anywhere → you're the first. Collect admin setup (Question 0) before project questions.**

**Admin config exists → joining developer. Skip admin setup. Load org policy from Hub at end of init.**

---

## Question 0 — Admin Setup (First-Run Only)

**Q0a — Hub location:**
```
Where is your Raven Hub?
( ) SaaS — hub.raven.giggso.com
( ) Self-hosted — I'll enter the URL
( ) No Hub — local-only mode
```

**Q0b — Org name:** short, no spaces (e.g. acme, giggso)

**Q0c — Admin email:** becomes org admin contact

**Q0d — Initial policy mode:**
```
( ) shadow — all MCPs run, ungoverned ones logged (Recommended for day 1)
( ) soft   — first-use prompt for new MCPs, auto-continues
( ) hard   — all new MCPs need admin approval
```

After Q0d — write `~/.raven/org-admin.json` (admin_email, hub_url, org, policy_mode, setup_at, admin_since: "first-install") and `.raven/mcp-policy.json` (mode, default, allowed: [], blocked: []).

Show confirmation, then proceed to project questions.

---

## Greenfield Rules (0 source files only)

```
When NO source files exist in the project directory, every answer comes from the user.
The manifest is what the user declares for the project they intend to build.

EXCEPTION — project name only:
  Pre-populate from basename(cwd). Show as default. User confirms or overrides.
```

---

## Interactive Questions — one at a time, wait for each answer

**Q1 — Project name:**
Default from `basename(cwd)`, sanitized to `^[a-zA-Z0-9_-]+$`. User confirms or types new name.

**Q2 — Work type:**
```
( ) code    — application code (Python, TypeScript, Go, etc.)
( ) infra   — infrastructure only (Terraform, K8s, Helm)
( ) review  — reviewing code/docs/architecture (no files generated)
( ) mixed   — code + infrastructure
```
- code → full language + library validation
- infra → no language block on .yaml/.tf/.hcl/.json
- review → stack validation skipped entirely
- mixed → code rules for .py/.ts/.go · infra rules for .yaml/.tf/.hcl

**Q3 — Primary language(s):**

If `review` → skip. Set `stack.language: ["review-only"]`.

If `infra` → multi-select: yaml · hcl · json · dockerfile · bicep · shell

If `code` or `mixed` → multi-select: python3.13 · python3.12 · python3.11 · typescript · javascript · go · rust · java · kotlin · swift · csharp · sql+plsql · shell · yaml · hcl

If org manifest has locked languages → show pre-selected, explain they can't be changed.

**Q4 — Frontend framework:** (skip for `infra` or `review`)
```
( ) vuejs  ( ) reactjs  ( ) nextjs  ( ) nuxtjs  ( ) none
```

**Q5 — Cloud:**
```
( ) aws  ( ) gcp  ( ) azure  ( ) oci  ( ) on-prem  ( ) multi
```

**Q6 — Database(s):** multi-select:
postgresql · oracle-26ai · opensearch · falkordb (GraphDB preferred) · neo4j · dynamodb · kafka · rabbitmq · none

**Q7 — Infrastructure tools:** multi-select:
terraform · docker-compose · kubernetes · kubespray · helm · ansible

**Q8 — Author email:** basic email format. Becomes first changelog entry author.

**Q9 — Guard enabled?**
```
( ) yes — recommended
( ) no
```
If org manifest locks `guard.enabled: true` → skip, show: "Guard is enabled by org policy and cannot be disabled."

---

## Generate Manifest

1. Merge answers with org defaults (org locked fields win)
2. Generate `manifest.json` matching schema exactly
3. Add initial changelog entry: version 1.0 · changed_by from Q8 · ISO timestamp · summary of answers · pr: "pending" · approved_by from Q8
4. Show generated manifest → ask "Looks good? (yes / no — let me change something)"

---

## Save + Git (automatic — user does nothing)

On confirmation:

1. Create `.raven/` directory if needed
2. Write `.raven/manifest.json`
3. Write `.raven/.gitignore` containing: `manifest.secrets.json` and `.cache/`
4. Update root `.gitignore` silently — append if not present:
   ```
   # Raven
   .raven/manifest.secrets.json
   .raven/.cache/
   .model.env
   ```
5. Commit silently:
   ```bash
   git add .raven/manifest.json .raven/.gitignore .gitignore
   git commit -m "chore: init raven v3.0 [RAVEN:INIT]"
   ```
   Do NOT show git commands. Do NOT ask user to run them.

5b. **Secrets detection — mode-dependent:**
- **Solo mode** (no Hub URL in Q0) → skip entirely. Never mention secrets.
- **Team / Enterprise mode** → run `python3 .codex/scripts/secrets-init.py` silently. It handles its own output.

6. Write `.codex/AGENTS.md` if not already present. Create `.codex/` if needed. Never overwrite existing.

7. Show only:
```
─────────────────────────────────────────
  Raven ✅  {project}  initialized
─────────────────────────────────────────
  Stack:   {stack summary}
  Policy:  {mode}
  Guards:  active

  You're ready. What are we building?
─────────────────────────────────────────
```

No warnings. No manual steps. No git commands. Never mention manifest.secrets.json to solo users.

---

## Validation

Run after saving:
1. Validate against `manifest.schema.json`
2. Check required fields present
3. Check locked fields match org manifest (if present)
4. Check changelog has at least one entry

Show: ✅ for each check passed. On failure: `❌ {field}: {reason}` → "Fix and re-run /raven init"

---

## Audit Trail

Every init creates:
- `changelog` entry in `manifest.json` (in Git)
- Commit tagged `[RAVEN:INIT]` (in Git history)
- Timestamp + author on changelog entry

---

*Raven v3.0 — github.com/giggsoinc/raven*
