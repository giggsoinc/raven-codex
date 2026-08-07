#!/bin/bash
set -e

RAVEN_DIR="$HOME/.raven-codex"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
CODEX_CONFIG="$CODEX_HOME/config.toml"

echo "Installing Raven-Codex..."

if [ -d "$RAVEN_DIR/.git" ]; then
  git -C "$RAVEN_DIR" pull --ff-only
else
  git clone https://github.com/giggsoinc/raven-codex.git "$RAVEN_DIR"
fi

chmod +x "$RAVEN_DIR/raven-codex-setup.sh"
chmod +x "$RAVEN_DIR/scripts/"*.py 2>/dev/null || true
chmod +x "$RAVEN_DIR/mcp/server.py" 2>/dev/null || true

echo "Installing Python dependencies..."
pip3 install -q openai requests packaging 2>/dev/null || true

# Add raven-codex-setup alias to shell profile
SHELL_PROFILE="$HOME/.zshrc"
[ -f "$HOME/.bashrc" ] && SHELL_PROFILE="$HOME/.bashrc"

if ! grep -q "raven-codex-setup" "$SHELL_PROFILE" 2>/dev/null; then
  echo "" >> "$SHELL_PROFILE"
  echo "# Raven-Codex" >> "$SHELL_PROFILE"
  echo "alias raven-codex-setup='bash $RAVEN_DIR/raven-codex-setup.sh'" >> "$SHELL_PROFILE"
fi

mkdir -p "$CODEX_HOME"
python3 - "$CODEX_CONFIG" "$RAVEN_DIR" <<'PY'
import sys
from pathlib import Path

config_path = Path(sys.argv[1])
raven_dir = Path(sys.argv[2])
text = config_path.read_text() if config_path.exists() else ""

gate = '''developer_instructions = """
RAVEN GATE (non-negotiable, applies to every prompt in every session):
1. Before generating any response, apply Raven Core routing (Step 0):
   classify the prompt and route through the matching Raven skill.
2. Every response MUST begin with exactly one protocol line:
   "Raven: routed -> <skill>"  or
   "Raven: passive (<one-line reason>)"  or
   "Raven: blocked -> <rule violated>"
   A response without this line is a defect.
3. If .raven/manifest.json exists in the repo, Raven is ACTIVE there.
   Never treat Raven as review-only or triggered-only.
"""
'''

if text.startswith("developer_instructions = "):
    end = text.index('"""\n', len('developer_instructions = """')) + 4
    text = gate + text[end:].lstrip("\n")
elif "\ndeveloper_instructions = " in text:
    start = text.index("\ndeveloper_instructions = ") + 1
    end = text.index('"""\n', start + len('developer_instructions = """')) + 4
    text = text[:start] + gate + text[end:].lstrip("\n")
else:
    text = gate + "\n" + text

server = f'''[mcp_servers.raven]
command = "python3"
args = ["{raven_dir / "mcp" / "server.py"}"]
startup_timeout_sec = 120
'''

lines = text.splitlines()
out = []
i = 0
while i < len(lines):
    if lines[i].strip() == "[mcp_servers.raven]":
        i += 1
        while i < len(lines) and not lines[i].startswith("["):
            i += 1
        if out and out[-1] != "":
            out.append("")
        out.extend(server.strip().splitlines())
        if i < len(lines):
            out.append("")
        continue
    out.append(lines[i])
    i += 1
text = "\n".join(out).rstrip() + "\n"
if "[mcp_servers.raven]" not in text:
    text = text.rstrip() + "\n\n" + server

config_path.write_text(text)
PY

echo ""
echo "✅ Raven-Codex installed at $RAVEN_DIR"
echo "✅ Raven gate written to $CODEX_CONFIG"
echo "✅ Raven MCP server registered in $CODEX_CONFIG"
echo ""
echo "Use in any repo:"
echo "  cd YourProject && codex"
echo "  Then say: raven init"
echo ""
