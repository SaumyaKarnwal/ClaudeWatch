#!/usr/bin/env python3
"""Apply settings -- regenerate the skhd hotkey binding from config.json.

    apply_config.py                 # rewrite the binding from config.json + reload skhd
    apply_config.py preset <name>   # set hotkey to a named preset, then apply
    apply_config.py set "<combo>"   # set hotkey to a raw skhd combo, then apply
    apply_config.py open            # open config.json in the default text editor

The binding is written into a *managed block* in ~/.skhdrc so any other skhd
bindings the user has are left untouched.
"""

import json
import os
import re
import subprocess
import sys

ROOT = os.path.expanduser("~/projects/claude-session-inbox")
CONFIG = os.path.join(ROOT, "config.json")
JUMP = os.path.join(ROOT, "hooks", "jump_to_oldest.py")
SKHDRC = os.path.expanduser("~/.skhdrc")
PY = "/usr/bin/python3"
SKHD = "/opt/homebrew/bin/skhd"

PRESETS = {
    "cmd-ctrl-j": "cmd + ctrl - j",
    "ctrl-alt-j": "ctrl + alt - j",
    "cmd-ctrl-space": "cmd + ctrl - space",
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


def set_hotkey(combo):
    cfg = load_config()
    cfg["hotkey"] = combo
    with open(CONFIG, "w") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")


def apply():
    combo = load_config().get("hotkey", "cmd + ctrl - j")
    block = f"{BEGIN}\n{combo} : {PY} {JUMP}\n{END}\n"

    existing = ""
    if os.path.exists(SKHDRC):
        with open(SKHDRC) as f:
            existing = f.read()
    # drop any prior managed block, keep everything else the user added
    cleaned = MANAGED_RE.sub("", existing).rstrip()
    new = f"{cleaned}\n\n{block}" if cleaned else block
    with open(SKHDRC, "w") as f:
        f.write(new)

    subprocess.run([SKHD, "--reload"], capture_output=True)
    print(f"hotkey applied: {combo}")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "open":
        subprocess.run(["open", "-t", CONFIG])
        return
    if cmd == "preset":
        name = sys.argv[2] if len(sys.argv) > 2 else ""
        if name not in PRESETS:
            print(f"unknown preset: {name!r}", file=sys.stderr)
            sys.exit(1)
        set_hotkey(PRESETS[name])
    elif cmd == "set":
        set_hotkey(sys.argv[2])
    apply()


if __name__ == "__main__":
    main()
