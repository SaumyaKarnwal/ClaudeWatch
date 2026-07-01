#!/usr/bin/env bash
#
# ClaudeWatch uninstaller. Reverses install.sh: stops the menu-bar app, removes
# the Claude Code hooks, and removes the skhd bindings. Leaves the cloned repo,
# the venv, and shared tools (skhd, iTerm2) in place — delete those yourself if
# you want them gone.
#
set -euo pipefail

PLIST="$HOME/Library/LaunchAgents/com.claudewatch.menubar.plist"
SETTINGS="$HOME/.claude/settings.json"
SKHDRC="$HOME/.skhdrc"

say() { printf "\033[1;34m==>\033[0m %s\n" "$1"; }
ok()  { printf "  \033[32m✓\033[0m %s\n" "$1"; }

say "Stopping the menu-bar app"
launchctl bootout "gui/$(id -u)/com.claudewatch.menubar" 2>/dev/null || true
rm -f "$PLIST"
pkill -f menubar_app.py 2>/dev/null || true
ok "menu-bar app stopped + login agent removed"

say "Removing Claude Code hooks from $SETTINGS"
if [ -f "$SETTINGS" ]; then
    cp "$SETTINGS" "$SETTINGS.bak.$(date +%s)"
    CW_SETTINGS="$SETTINGS" /usr/bin/python3 - <<'PY'
import json, os
path = os.environ["CW_SETTINGS"]
with open(path) as f: cfg = json.load(f)
hooks = cfg.get("hooks", {})
for event in list(hooks):
    hooks[event] = [e for e in hooks[event] if "record_event.py" not in json.dumps(e)]
    if not hooks[event]:
        del hooks[event]
if not hooks:
    cfg.pop("hooks", None)
with open(path, "w") as f:
    json.dump(cfg, f, indent=2); f.write("\n")
PY
    ok "hooks removed (other settings preserved; backup saved)"
fi

say "Removing skhd bindings"
if [ -f "$SKHDRC" ]; then
    /usr/bin/python3 - "$SKHDRC" <<'PY'
import re, sys
path = sys.argv[1]
text = open(path).read()
begin, end = "# >>> claude-session-inbox (managed) >>>", "# <<< claude-session-inbox (managed) <<<"
text = re.sub(re.escape(begin) + r".*?" + re.escape(end) + r"\n?", "", text, flags=re.S).rstrip() + "\n"
open(path, "w").write(text)
PY
    command -v skhd >/dev/null && skhd --reload 2>/dev/null || true
    ok "skhd bindings removed"
fi

echo
say "Uninstalled. The repo + venv remain — 'rm -rf' this folder to delete them."
echo "  Shared tools left installed: skhd, iTerm2. Remove with: brew uninstall skhd"
