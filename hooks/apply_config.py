#!/usr/bin/env python3
"""Apply settings -- regenerate the skhd hotkey bindings from config.json.

    apply_config.py                     # rewrite all bindings from config.json + reload
    apply_config.py set <which> "<combo>"   # set a hotkey (which: jump|panel|notify)
    apply_config.py open                # open config.json in the default text editor

Three actions can be bound (each optional -- leave its config key empty to skip):
    hotkey         -> jump to next waiting session (round-robin)
    panel_hotkey   -> open the inbox panel on the active screen
    notify_hotkey  -> jump to the session the current notification is about

All bindings are written into a *managed block* in ~/.skhdrc; anything you add
outside that block is left untouched.
"""

import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "config.json")
SKHDRC = os.path.expanduser("~/.skhdrc")
PY = "/usr/bin/python3"
VENV_PY = os.path.join(ROOT, ".venv", "bin", "python")
SKHD = "/opt/homebrew/bin/skhd"

# config key -> the command its hotkey should run
ACTIONS = {
    "jump": ("hotkey", f"{PY} {os.path.join(ROOT, 'hooks', 'jump_to_oldest.py')}"),
    "panel": ("panel_hotkey", f"{VENV_PY} {os.path.join(ROOT, 'hooks', 'panel.py')}"),
    "notify": ("notify_hotkey", f"{PY} {os.path.join(ROOT, 'hooks', 'jump_to_last_notified.py')}"),
}

BEGIN = "# >>> claude-session-inbox (managed) >>>"
END = "# <<< claude-session-inbox (managed) <<<"
MANAGED_RE = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?", re.S)


def load_config():
    try:
        with open(CONFIG) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def set_hotkey(which, combo):
    key = ACTIONS[which][0]
    cfg = load_config()
    cfg[key] = combo
    with open(CONFIG, "w") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")


def apply():
    cfg = load_config()
    lines = []
    for _, (key, command) in ACTIONS.items():
        combo = (cfg.get(key) or "").strip()
        if combo:
            lines.append(f"{combo} : {command}")
    block = f"{BEGIN}\n" + "\n".join(lines) + f"\n{END}\n"

    existing = ""
    if os.path.exists(SKHDRC):
        with open(SKHDRC) as f:
            existing = f.read()
    cleaned = MANAGED_RE.sub("", existing).rstrip()
    new = f"{cleaned}\n\n{block}" if cleaned else block
    with open(SKHDRC, "w") as f:
        f.write(new)

    subprocess.run([SKHD, "--reload"], capture_output=True)
    print("bindings applied:\n  " + "\n  ".join(lines))


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "open":
        subprocess.run(["open", "-t", CONFIG])
        return
    if cmd == "set":
        which = sys.argv[2] if len(sys.argv) > 2 else ""
        combo = sys.argv[3] if len(sys.argv) > 3 else ""
        if which not in ACTIONS:
            print(f"unknown action: {which!r}; valid: {', '.join(ACTIONS)}", file=sys.stderr)
            sys.exit(1)
        set_hotkey(which, combo)
    apply()


if __name__ == "__main__":
    main()
