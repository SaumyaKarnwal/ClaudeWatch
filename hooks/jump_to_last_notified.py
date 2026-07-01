#!/usr/bin/env python3
"""Hotkey action: jump to the session the most recent notification was about.

This is the keyboard equivalent of clicking the toast that's on screen -- it
reads the session recorded by notify.py and focuses that iTerm2 tab.
"""

import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAST_NOTIFIED = os.path.join(ROOT, ".last_notified")
FOCUS = os.path.join(ROOT, "hooks", "focus_session.py")


def main():
    try:
        with open(LAST_NOTIFIED) as f:
            iterm = f.read().strip()
    except OSError:
        iterm = ""

    if iterm:
        subprocess.run(["/usr/bin/python3", FOCUS, iterm])
    else:
        subprocess.run(["osascript", "-e", "beep"])


if __name__ == "__main__":
    main()
