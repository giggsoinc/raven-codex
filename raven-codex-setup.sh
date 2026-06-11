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
read -p "OpenAI API key (for CVE deep scan): " OPENAI_KEY

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
OPENAI_API_KEY=$OPENAI_KEY
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

# Cursor wiring (optional): hooks live in ~/.cursor/hooks.json
if [[ -d "$HOME/.cursor" ]]; then
    echo "ℹ️  Cursor detected — merge docs/cursor-hooks.example.json into ~/.cursor/hooks.json"
    echo "   to deny 'git commit' from agent shells when the gate would block."
fi

echo ""
echo "✅ manifest.json written to .raven/"
echo "✅ Audit log directory created"
echo "✅ Skill-routing gate: mode soft for 7 days, then hard (edit .raven/state/routing-policy.json)"
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
