---
name: governance_gate
description: Explicit user decision gate before ANY command execution — Raven routing or direct proceed
metadata:
  type: feedback
---

**Rule: Ask before executing ANY command**

Before responding to any user command (code response, Bash, git, file edit, anything actionable), ask:

> "Raven or lucky? Say **Raven** for governance routing, **Go** to proceed direct."

Wait for their response. Do not assume or infer intent.

- **"Raven"**, **"Go"**, or no response (default) → Invoke the matching Raven specialist skill (raven-review, raven-security, raven-refactor, etc.)
- **"Lucky"** → Proceed directly, no governance gates

**Why:** Removes discretionary judgment calls about "what deserves routing." Governance is their choice, explicit every time, not something I silently decide based on whether a task "feels mechanical" or "obvious."

**How to apply:** This is the first gate. Before any tool call or code change, ask. Every time. No exceptions for "feels safe" or "we're deep in flow" or "specific command."
