# Codex Governance Gate: Raven or Lucky

## The Rule

Before executing ANY command, the assistant asks:

```
Raven or lucky?
```

**Semantics:**
- **"Raven"**, **"Go"**, or silence (default) → Route through Raven specialist skill. Governance ENABLED.
- **"Lucky"** → Proceed direct. NO governance gates.

## Why This Exists

Silent judgment calls about "what deserves governance" were causing:
- Git operations to skip security review
- Merge-to-main moments to feel "mechanical" and bypass escalation  
- Momentum/speed bias to override discipline
- Pre-commit guards to substitute for active review

This gate removes discretion entirely. You decide, explicitly, every time.

## When to Say "Raven"

- Security-sensitive work (auth, keys, access control)
- Refactoring with high blast radius
- Merges to main or protected branches
- Operations touching infrastructure or persistence
- Anything "feeling safe" (exact moment governance exists for)

## When to Say "Lucky"

- Trivial fixes with minimal scope
- Well-scoped feature work with clear requirements
- Straightforward testing or documentation changes
- When speed is essential and you're confident

## Raven Specialist Skills

The assistant will route to one of:
- `raven:raven-security` — security-critical work
- `raven:raven-review` — code review and validation
- `raven:raven-refactor` — refactoring and migration
- `raven:raven-core` — infrastructure and system work
- `raven:raven-sync` — dependency and version management
- Others as appropriate for the task domain

## Integration

This governance gate is the **only** decision point. After you choose, Raven handles the rest:
- Pre-commit guards run automatically on every commit
- Post-edit hooks validate code changes
- The specialist skill applies the domain discipline

You are never in a position to silently opt out.
