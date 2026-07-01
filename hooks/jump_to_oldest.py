#!/usr/bin/env python3
"""Hotkey action: jump to the next Claude session that needs attention.

Cycles your inbox -- needs-input first (oldest first), then finished -- and
focuses the first one you're NOT already on. Press the bound hotkey repeatedly
to tour every waiting session in turn, draining the board by keyboard alone.

Falls back to a quiet beep if the inbox is empty.
"""

import os
import subprocess
import sqlite3

ROOT = os.path.expanduser("~/projects/claude-session-inbox")
DB_PATH = os.path.join(ROOT, "inbox.db")
FOCUS = os.path.join(ROOT, "hooks", "focus_session.py")

# Which iTerm2 session is focused right now (empty if iTerm2 isn't frontmost)?
CURRENT_GUID = '''
set g to ""
tell application "System Events" to set front to name of first application process whose frontmost is true
if front is "iTerm2" then
    tell application "iTerm2"
        tell current session of current tab of current window
            set g to (variable named "session.id")
        end tell
    end tell
end if
return g
'''


def current_guid():
    try:
        return subprocess.run(
            ["osascript", "-e", CURRENT_GUID], capture_output=True, text=True, timeout=3
        ).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return ""


def main():
    # diagnostic breadcrumb: proves skhd actually invoked us on keypress.
    try:
        with open("/tmp/claude_inbox_jump.log", "a") as f:
            f.write(f"fired {int(__import__('time').time())}\n")
    except OSError:
        pass

    if not os.path.exists(DB_PATH):
        return

    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    try:
        rows = conn.execute(
            """
            SELECT iterm_session_id
            FROM sessions
            WHERE iterm_session_id != ''
            ORDER BY CASE state WHEN 'needs_input' THEN 0 ELSE 1 END, updated_at ASC
            """
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        # Always give VISIBLE feedback. An alert window shows regardless of Focus
        # or notification settings (unlike a banner), and auto-closes after 1s.
        subprocess.run([
            "osascript", "-e",
            'display alert "Claude Session Inbox" message "No sessions waiting on you ✨" '
            'giving up after 1',
        ])
        return

    here = current_guid()
    targets = [r[0] for r in rows]
    guids = [t.split(":", 1)[-1] for t in targets]
    # Round-robin: advance to the session AFTER the one we're on, wrapping around,
    # so repeated presses tour ALL sessions instead of ping-ponging between two.
    # If we're not on any tracked session, start at the first (oldest).
    nxt = targets[(guids.index(here) + 1) % len(targets)] if here in guids else targets[0]

    # explicit interpreter -- skhd runs with a minimal PATH that may lack python3.
    subprocess.run(["/usr/bin/python3", FOCUS, nxt])


if __name__ == "__main__":
    main()
