#!/usr/bin/env bash
#
# ClaudeWatch installer. Idempotent: safe to re-run.
# Installs dependencies, wires the Claude Code hooks, binds the keyboard
# shortcuts, and starts the menu-bar app. It NEVER touches anything outside
# what it explicitly reports, and it does not require network access at runtime.
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST="$HOME/Library/LaunchAgents/com.claudewatch.menubar.plist"
SETTINGS="$HOME/.claude/settings.json"
VENV_PY="$ROOT/.venv/bin/python"

say()  { printf "\033[1;34m==>\033[0m %s\n" "$1"; }
ok()   { printf "  \033[32m✓\033[0m %s\n" "$1"; }
warn() { printf "  \033[33m!\033[0m %s\n" "$1"; }

# ---------------------------------------------------------------- preflight
say "Checking prerequisites"
[ "$(uname)" = "Darwin" ] || { echo "ClaudeWatch is macOS-only."; exit 1; }
[ -d /Applications/iTerm.app ] || warn "iTerm2 not found in /Applications — ClaudeWatch is built for iTerm2."
command -v brew >/dev/null   || { echo "Homebrew required: https://brew.sh"; exit 1; }
command -v /usr/bin/python3 >/dev/null || { echo "python3 required (install Xcode Command Line Tools)."; exit 1; }
ok "macOS + brew + python3 present"

# ---------------------------------------------------------------- skhd
say "Installing skhd (global hotkeys)"
if ! command -v skhd >/dev/null; then
    brew install koekeishiya/formulae/skhd
fi
ok "skhd: $(command -v skhd)"

# ---------------------------------------------------------------- python venv (PyObjC)
say "Setting up Python venv with PyObjC (menu bar + toast + panel)"
if [ ! -x "$VENV_PY" ]; then
    /usr/bin/python3 -m venv "$ROOT/.venv"
    "$VENV_PY" -m pip install --quiet --upgrade pip
fi
"$VENV_PY" -c "import AppKit" 2>/dev/null || "$VENV_PY" -m pip install --quiet pyobjc-framework-Cocoa
ok "PyObjC ready"

# ---------------------------------------------------------------- Claude Code hooks
say "Wiring Claude Code hooks into $SETTINGS"
mkdir -p "$HOME/.claude"
[ -f "$SETTINGS" ] && cp "$SETTINGS" "$SETTINGS.bak.$(date +%s)"
CW_ROOT="$ROOT" CW_SETTINGS="$SETTINGS" /usr/bin/python3 - <<'PY'
import json, os
root, path = os.environ["CW_ROOT"], os.environ["CW_SETTINGS"]
try:
    with open(path) as f: cfg = json.load(f)
except (OSError, ValueError):
    cfg = {}
hooks = cfg.setdefault("hooks", {})

# (event, matcher-or-None, record_event arg). Two Notification matchers:
#   permission_prompt -> needs_input ;  idle_prompt -> done (the true-idle signal).
# We deliberately do NOT hook Stop: it fires at every turn boundary (incl. while
# background subagents run), which caused repeated false "done"s.
SPECS = [
    ("Notification", "permission_prompt", "notification"),
    ("Notification", "idle_prompt", "idle"),
    ("UserPromptSubmit", None, "prompt"),
    ("SessionEnd", None, "session_end"),
]
managed = {e for e, _, _ in SPECS}
# Strip prior ClaudeWatch entries everywhere we manage -- incl. a stale `Stop`
# hook from an older install -- keeping any non-ClaudeWatch hooks intact.
for event in managed | {"Stop"}:
    if event in hooks:
        remaining = [e for e in hooks[event] if "record_event.py" not in json.dumps(e)]
        if remaining:
            hooks[event] = remaining
        else:
            del hooks[event]
for event, matcher, arg in SPECS:
    entry = {"hooks": [{"type": "command", "command": f"/usr/bin/python3 {root}/hooks/record_event.py {arg}"}]}
    if matcher:
        entry = {"matcher": matcher, **entry}
    hooks.setdefault(event, []).append(entry)
with open(path, "w") as f:
    json.dump(cfg, f, indent=2); f.write("\n")
print("  hooks: Notification(permission_prompt->needs_input, idle_prompt->done), UserPromptSubmit, SessionEnd (Stop dropped)")
PY
ok "hooks wired (existing settings preserved; backup saved)"

# ---------------------------------------------------------------- keyboard shortcuts
say "Binding keyboard shortcuts (skhd)"
/usr/bin/python3 "$ROOT/hooks/apply_config.py" >/dev/null
skhd --start-service 2>/dev/null || true
skhd --restart-service 2>/dev/null || true
ok "shortcuts bound + skhd started"

# ---------------------------------------------------------------- menu-bar app (launchd)
say "Installing the menu-bar app as a login agent"
mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.claudewatch.menubar</string>
    <key>ProgramArguments</key>
    <array>
        <string>$VENV_PY</string>
        <string>$ROOT/hooks/menubar_app.py</string>
    </array>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
    <key>StandardErrorPath</key><string>/tmp/claudewatch_menubar.err.log</string>
    <key>StandardOutPath</key><string>/tmp/claudewatch_menubar.out.log</string>
</dict>
</plist>
PLISTEOF
launchctl bootout "gui/$(id -u)/com.claudewatch.menubar" 2>/dev/null || true
sleep 1
# bootstrap fails with I/O error if the label is still registered; fall back to
# kickstart (restart the already-loaded agent) so re-runs are safe.
if ! launchctl bootstrap "gui/$(id -u)" "$PLIST" 2>/dev/null; then
    launchctl kickstart -k "gui/$(id -u)/com.claudewatch.menubar" 2>/dev/null || true
fi
ok "menu-bar app running + set to launch at login"

# ---------------------------------------------------------------- permissions
say "Two permissions to grant (macOS requires you to do this by hand)"
cat <<'EOF'
  1. Accessibility  →  skhd
     Why: to detect your keyboard shortcuts system-wide.
     System Settings ▸ Privacy & Security ▸ Accessibility ▸ add /opt/homebrew/bin/skhd, toggle ON.

  2. Automation  →  iTerm2  +  System Events
     Why: to focus the right iTerm2 tab (deep-link) and see which app is
     frontmost (so it stays quiet about the session you're already viewing).
     macOS will prompt the first time — click OK. (Privacy & Security ▸ Automation)

  It does NOT ask for: Notifications, Screen Recording, Full Disk, Camera/Mic, or network.
EOF
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility" 2>/dev/null || true

echo
say "Done. Menu-bar badge is live. Grant the two permissions above, then it's fully working."
echo "  Shortcuts:  ⌥\`  open inbox   ·   ⌘⌃N  go to notification   ·   ⌃\`  cycle sessions"
echo "  (change them in the menu-bar ▸ Settings, or edit config.json)"
