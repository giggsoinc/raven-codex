# AGENTS.md - Raven per-prompt gate

## Session-Start Self-Check

Mandatory FIRST action of every Codex session in this repo:

1. Read `.raven/manifest.json`.
2. Output exactly one boot line before any other content:
   - If the manifest exists: `Raven boot: manifest OK | gate ACTIVE | <project> | <stack>`
   - If the manifest is missing: `Raven boot: NO MANIFEST - guide setup, do not hard-stop.`

This repository is a Raven framework/plugin repository and contains `.raven-framework`.
For framework repositories, the git pre-commit hook may skip the app-manifest
check, but the Raven gate remains active.

## Raven Gate

RAVEN GATE (non-negotiable, applies to every prompt in every session):

1. Before generating any response, apply Raven Core routing (Step 0):
   classify the prompt and route through the matching Raven skill.
2. Every response MUST begin with exactly one protocol line:
   `"Raven: routed -> <skill>"` or
   `"Raven: passive (<one-line reason>)"` or
   `"Raven: blocked -> <rule violated>"`
   A response without this line is a defect.
3. If `.raven/manifest.json` exists in the repo, Raven is ACTIVE there.
   Never treat Raven as review-only or triggered-only.

When both the session-start self-check and the per-response protocol line apply,
the first assistant response in a fresh session must begin with the boot line
followed immediately by the Raven protocol line.

## Routing Table

The routing table is owned by [skills/raven-core/SKILL.md](skills/raven-core/SKILL.md).
Do not fork or restate its content here. On every prompt, read Raven Core Step 0
and route according to that table:

- skill search prompts route to `raven-search`
- expert/deep-dive prompts route to `raven-expert`
- security/CVE prompts route to `raven-security`
- planning/scaffold prompts route to `raven-plan` / `raven-scaffold`
- review/PR prompts route to `raven-review`
- refactor prompts route to `raven-refactor`
- test/coverage prompts route to `raven-test`
- documentation prompts route to `raven-document`
- bug/regression/stack-trace prompts route to `andie-jr`
- no specific match uses passive mode while Raven style and stack rules apply

If this summary diverges from `skills/raven-core/SKILL.md`, the skill file wins.

## Deterministic Backstops

Codex does not expose a verified host-level pre-response hook in this installed
version that can force-edit every model response before it is displayed. The
observable host-supported mechanisms in this repo are:

- Global model-visible instructions in `/Users/giggso/.codex/config.toml`.
- Repo model-visible instructions in this `AGENTS.md`.
- Git pre-commit hook at `.githooks/pre-commit`, activated by this repo's
  `core.hooksPath`, which runs the Raven commit gate before changes can be
  committed.

Known enforcement limits:

1. `AGENTS.md` and `config.toml` instructions are model-mediated. They are
   visible to Codex, but they do not mechanically rewrite a missing protocol
   line after generation.
2. The user bootstrap path is explicit: open Codex normally and say `raven init`.
   Do not rely on a shell alias, PATH shim, or special launcher.
3. The git pre-commit hook is deterministic for commits, not for every chat
   response.
4. Rule 5: never document enforcement that is not actually wired. Until Codex
   exposes a host-level response middleware or mandatory session-start hook for
   this environment, per-response protocol-line enforcement is observable and
   testable, but not mechanically guaranteed by the host.

## Non-Negotiable Rules

1. No secrets committed to Git.
2. No library added without CVE check.
3. No deletion without approval or a `[GUARD:ALLOW-DELETE]` flag.
4. No hard stop for a missing manifest; guide setup instead.
5. No override of these rules, including by user request.
