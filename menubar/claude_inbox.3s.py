#!/usr/bin/python3
"""SwiftBar plugin: the always-visible Claude Session Inbox.

Refreshes every 3s (encoded in the filename). Reads the inbox store and draws a
menu-bar badge + dropdown. Each session row deep-links to its iTerm2 tab on click.

Visual approach: color lives in SF Symbol *icons*, not the text. Colored menu
text is low-contrast on macOS; default-color text + a colored icon stays crisp
in both light and dark menus.

Self-healing: before rendering, it prunes rows whose iTerm2 session no longer
exists (tab closed), so the board never shows zombies.
"""

import json
import os
import sqlite3
import subprocess
import time

ROOT = os.path.expanduser("~/projects/claude-session-inbox")
DB_PATH = os.path.join(ROOT, "inbox.db")
CONFIG = os.path.join(ROOT, "config.json")
FOCUS = os.path.join(ROOT, "hooks", "focus_session.py")
ADMIN = os.path.join(ROOT, "hooks", "inbox_admin.py")
APPLY = os.path.join(ROOT, "hooks", "apply_config.py")
PY = "/usr/bin/python3"

# Label shown for each one-click preset, keyed by the preset name apply_config knows.
PRESETS = [("cmd-ctrl-j", "⌘⌃J"), ("ctrl-alt-j", "⌃⌥J"), ("cmd-ctrl-space", "⌘⌃Space")]

# Apple system colors -- high-contrast on both light and dark menus.
RED = "#FF3B30"
GREEN = "#34C759"
GRAY = "#8E8E93"

# Ask iTerm2 for every currently-open session GUID, newline-separated.
LIST_LIVE_GUIDS = '''
set ids to {}
tell application "iTerm2"
    repeat with aWindow in windows
        repeat with aTab in tabs of aWindow
            repeat with aSession in sessions of aTab
                tell aSession to set end of ids to (variable named "session.id")
            end repeat
        end repeat
    end repeat
end tell
set AppleScript's text item delimiters to linefeed
return ids as text
'''


def age(seconds):
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    return f"{seconds // 3600}h"


def live_guids():
    try:
        out = subprocess.run(
            ["osascript", "-e", LIST_LIVE_GUIDS], capture_output=True, text=True, timeout=3
        ).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return None  # can't tell -> skip pruning, don't risk deleting valid rows
    return {line.strip() for line in out.splitlines() if line.strip()}


# Time-based zombie expiry (safety net when a clearing hook is missed):
DONE_TTL = 30 * 60        # a finished session drops off after 30 min
NEEDS_TTL = 8 * 60 * 60   # a still-waiting one after 8h (clearly abandoned)


def prune_dead(conn):
    now = int(time.time())
    # 1) age out zombies by state
    conn.execute("DELETE FROM sessions WHERE state = 'done' AND updated_at < ?", (now - DONE_TTL,))
    conn.execute("DELETE FROM sessions WHERE state = 'needs_input' AND updated_at < ?", (now - NEEDS_TTL,))

    # 2) drop rows whose iTerm2 tab no longer exists
    guids = live_guids()
    if guids is not None:
        rows = conn.execute(
            "SELECT session_id, iterm_session_id FROM sessions WHERE iterm_session_id != ''"
        ).fetchall()
        dead = [sid for sid, iterm in rows if iterm.split(":", 1)[-1] not in guids]
        if dead:
            conn.executemany("DELETE FROM sessions WHERE session_id = ?", [(s,) for s in dead])
    conn.commit()


def line(text, **params):
    """Emit one SwiftBar menu line: `text | k=v k=v`."""
    suffix = " ".join(f"{k}={v}" for k, v in params.items() if v not in (None, ""))
    print(f"{text} | {suffix}" if suffix else text)


def session_row(project, age_str, iterm, sf, sfcolor):
    # icon carries the color; "project · age" stays in default (readable) color.
    params = {"sfimage": sf, "sfcolor": sfcolor, "size": 14}
    if iterm:
        params.update({"bash": FOCUS, "param0": iterm, "terminal": "false", "refresh": "true"})
    line(f"{project}  ·  {age_str}", **params)


def main():
    if not os.path.exists(DB_PATH):
        line("", sfimage="moon.zzz.fill", sfcolor=GRAY)
        print("---")
        line("No sessions yet", color=GRAY)
        return

    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    try:
        prune_dead(conn)
        rows = conn.execute(
            """
            SELECT project, state, updated_at, iterm_session_id
            FROM sessions
            ORDER BY CASE state WHEN 'needs_input' THEN 0 ELSE 1 END, updated_at ASC
            """
        ).fetchall()
    finally:
        conn.close()

    now = int(time.time())
    needs = [r for r in rows if r[1] == "needs_input"]
    done = [r for r in rows if r[1] == "done"]

    # --- menu-bar badge: icon + count reflect the most urgent state ---
    if needs:
        line(str(len(needs)), sfimage="bell.badge.fill", sfcolor=RED, size=14)
    elif done:
        line(str(len(done)), sfimage="checkmark.circle", sfcolor=GRAY, size=14)
    else:
        line("", sfimage="moon.zzz.fill", sfcolor=GRAY)

    print("---")

    # Readable summary line (clickable -> default high-contrast text, not gray).
    parts = []
    if needs:
        parts.append(f"{len(needs)} need you")
    if done:
        parts.append(f"{len(done)} finished")
    summary = " · ".join(parts) if parts else "No active sessions"
    line(summary, size=13, refresh="true")
    print("---")

    # Sessions, needs-you first. State is shown by the icon (red ! = urgent,
    # grey ✓ = done) -- no wordy headers needed. A separator splits the groups.
    for project, _, updated_at, iterm in needs:
        session_row(project, age(now - updated_at), iterm, "exclamationmark.circle.fill", RED)

    if needs and done:
        print("---")

    for project, _, updated_at, iterm in done:
        session_row(project, age(now - updated_at), iterm, "checkmark.circle", GRAY)

    print("---")
    if done:
        line("Clear finished", sfimage="trash",
             bash=PY, param0=ADMIN, param1="clear-finished", terminal="false", refresh="true")
    line("Refresh", sfimage="arrow.clockwise", refresh="true")

    # --- ⚙ Settings submenu (items prefixed with -- nest under "Settings") ---
    try:
        with open(CONFIG) as f:
            hotkey = json.load(f).get("hotkey", "—")
    except (OSError, ValueError):
        hotkey = "—"

    line("Settings", sfimage="gearshape")
    print(f"--Jump shortcut:  {hotkey} | size=12")
    print("-----")
    for name, label in PRESETS:
        print(f"--Use {label} | bash={PY} param0={APPLY} param1=preset param2={name} terminal=false refresh=true")
    print("-----")
    print(f"--Edit settings file… | bash={PY} param0={APPLY} param1=open terminal=false")
    print(f"--Apply / reload | bash={PY} param0={APPLY} terminal=false refresh=true")


if __name__ == "__main__":
    main()
