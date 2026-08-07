#!/bin/bash
set -e

RAVEN_DIR="$HOME/.raven-codex"
PROJECT_DIR="$(pwd)"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║        Raven-Codex Setup v4.1        ║"
echo "║   Enterprise AI Coding Discipline    ║"
echo "╚══════════════════════════════════════╝"
echo ""

# Collect project info
read -p "Project name: " PROJECT_NAME
read -p "Your email (audit trail): " USER_EMAIL
echo "Stack options: python / node / go / java / ruby / other"
read -p "Stack: " STACK
echo "Cloud options: aws / gcp / azure / oci / none"
read -p "Cloud provider: " CLOUD

# Create .raven directory in project
mkdir -p "$PROJECT_DIR/.raven/audit"
mkdir -p "$PROJECT_DIR/.raven/logs"

# Write manifest
cat > "$PROJECT_DIR/.raven/manifest.json" <<EOF
{
  "project": "$PROJECT_NAME",
  "version": "1.0",
  "platform": "codex",
  "owner": "$USER_EMAIL",
  "stack": "$STACK",
  "cloud": "$CLOUD",
  "mode": "active",
  "created": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "raven_version": "4.1.0",
  "approved_libraries": [],
  "blocked_patterns": [
    "TRUNCATE TABLE",
    "DROP TABLE",
    "DROP SCHEMA",
    "0.0.0.0/0",
    "force-push",
    "terraform.tfstate"
  ]
}
EOF

# Write .env template
cat > "$PROJECT_DIR/.raven/.env.template" <<EOF
RAVEN_CVE_MODEL=gpt-4o
RAVEN_AUDIT_KEY=
OPENAI_API_KEY=
EOF

# ── Skill-routing gate: state dir + default policy + git pre-commit hook ──
mkdir -p "$PROJECT_DIR/.raven/state"
if [[ ! -f "$PROJECT_DIR/.raven/state/routing-policy.json" ]]; then
cat > "$PROJECT_DIR/.raven/state/routing-policy.json" <<EOF
{
  "mode": "soft",
  "soft_until": "$(python3 -c 'from datetime import datetime,timedelta,timezone; print((datetime.now(timezone.utc)+timedelta(days=7)).isoformat())')",
  "gated_skills": ["andie", "andie-jr"],
  "scope": ["*.py", "src/**", "scripts/**", "*.js", "*.ts", "*.go", "*.java", "*.rs", "*.sql", "*.tf"],
  "freshness_hours": 4,
  "override_uses": 5
}
EOF
fi

if [[ -d "$PROJECT_DIR/.git" ]]; then
    HOOK="$PROJECT_DIR/.git/hooks/pre-commit"
    if ! grep -q "raven-skill-gate" "$HOOK" 2>/dev/null; then
        [[ -f "$HOOK" ]] || echo "#!/bin/sh" > "$HOOK"
        cat >> "$HOOK" <<EOF
# Raven skill-routing gate — blocks commits until a specialist marker exists
python3 "$RAVEN_DIR/scripts/raven-skill-gate.py" --event commit || exit 2
EOF
        chmod +x "$HOOK"
        echo "✅ git pre-commit gate installed (raven-skill-gate)"
    fi
fi

if [[ ! -f "$PROJECT_DIR/AGENTS.md" ]] || ! grep -q "RAVEN GATE" "$PROJECT_DIR/AGENTS.md"; then
cat > "$PROJECT_DIR/AGENTS.md" <<'EOF'
# AGENTS.md - Raven per-prompt gate

## Session-Start Self-Check

Mandatory FIRST action of every Codex session in this repo:

1. Read `.raven/manifest.json`.
2. Output exactly one boot line before any other content:
   - If the manifest exists: `Raven boot: manifest OK | gate ACTIVE | <project> | <stack>`
   - If the manifest is missing: `Raven boot: NO MANIFEST - guide setup, do not hard-stop.`

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

## Routing Table

The routing table is owned by Raven Core: `skills/raven-core/SKILL.md` in the
installed Raven-Codex plugin. Do not fork its content here. On every prompt,
read Raven Core Step 0 and route according to that table.

## Known Enforcement Limits

Codex model-visible instructions are active for plain `codex`, but the current
Codex host does not expose a response middleware that can mechanically rewrite
a missing protocol line after generation. The deterministic local hard stop is
the git pre-commit gate.
EOF
    echo "✅ AGENTS.md Raven gate installed"
fi

# Cursor wiring (optional): hooks live in ~/.cursor/hooks.json
if [[ -d "$HOME/.cursor" ]]; then
    echo "ℹ️  Cursor detected — merge docs/cursor-hooks.example.json into ~/.cursor/hooks.json"
    echo "   to deny 'git commit' from agent shells when the gate would block."
fi

echo ""
echo "✅ manifest.json written to .raven/"
echo "✅ Audit log directory created"
echo "✅ Skill-routing gate: mode soft for 7 days, then hard (edit .raven/state/routing-policy.json)"
echo "✅ Repo AGENTS.md gate installed for future Codex sessions"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Next: Connect Raven MCP server to Codex"
echo ""
echo "  1. Go to https://chatgpt.com/codex"
echo "  2. Settings → MCP Servers → Add MCP Server"
echo "  3. Name: raven"
echo "     Command: python3"
echo "     Args: $RAVEN_DIR/mcp/server.py"
echo "  4. Test: ask Codex to run raven_status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
