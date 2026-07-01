#!/usr/bin/env python3
"""Fire a notification for a session state change -- focus-aware, two-tier.

Called by record_event.py after the store is updated. The alert is a floating
toast (hooks/toast.py) shown on the screen you're currently using -- chosen over
a macOS banner because banners stick to the main display and get swallowed by
Focus modes. Two rules shape it:
  - Focus-aware: if you're already looking at the exact iTerm2 session that
    changed, stay silent -- a popup would just be noise.
  - Two-tier: `needs_input` is urgent (red + sound); `done` is a gentle FYI (green).
Clicking the toast deep-links to the session's iTerm2 tab.
"""

import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CONFIG_PATH = os.path.join(ROOT, "config.json")
TOAST = os.path.join(HERE, "toast.py")
VENV_PY = os.path.join(ROOT, ".venv", "bin", "python")  # has PyObjC
# Records the session the most recent toast is about, so a hotkey can "click" it.
LAST_NOTIFIED = os.path.join(ROOT, ".last_notified")

RED = "#FF3B30"
GREEN = "#34C759"

DEFAULTS = {
    "notify_on_needs_input": True,
    "notify_on_done": True,
    "suppress_when_focused": True,
    "sound_needs_input": "Ping",
    "sound_done": "",
}

# Per-state copy + styling, keyed by the state strings record_event.py writes.
COPY = {
    "needs_input": {"title": "Needs your input", "accent": RED, "symbol": "bell.badge.fill",
                    "enabled_key": "notify_on_needs_input", "sound_key": "sound_needs_input"},
    "done": {"title": "Finished", "accent": GREEN, "symbol": "checkmark.circle.fill",
             "enabled_key": "notify_on_done", "sound_key": "sound_done"},
}

# One AppleScript round-trip: "are you in iTerm2?" + "which session is focused?"
FOCUS_PROBE = '''
set frontApp to ""
tell application "System Events" to set frontApp to name of first application process whose frontmost is true
set guid to ""
if frontApp is "iTerm2" then
    tell application "iTerm2"
        tell current session of current tab of current window
            set guid to (variable named "session.id")
        end tell
    end tell
end if
return frontApp & "|||" & guid
'''


def load_config():
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG_PATH) as f:
            cfg.update(json.load(f))
    except (OSError, ValueError):
        pass
    return cfg


def is_focused_on(iterm_session_id):
    """True if iTerm2 is frontmost AND its active session is this one."""
    guid = iterm_session_id.split(":", 1)[-1]
    try:
        out = subprocess.run(
            ["osascript", "-e", FOCUS_PROBE], capture_output=True, text=True, timeout=3
        ).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return False  # if we can't tell, err toward notifying
    front, _, focused_guid = out.partition("|||")
    return front == "iTerm2" and focused_guid == guid


def maybe_notify(state, project, iterm_session_id):
    copy = COPY.get(state)
    if not copy:
        return

    cfg = load_config()
    if not cfg.get(copy["enabled_key"], True):
        return
    if cfg.get("suppress_when_focused", True) and iterm_session_id and is_focused_on(iterm_session_id):
        return

    # remember which session this toast is about (for the "jump to current
    # notification" hotkey)
    try:
        with open(LAST_NOTIFIED, "w") as f:
            f.write(iterm_session_id or "")
    except OSError:
        pass

    # fire the toast on the active screen, detached (must not block the hook)
    try:
        subprocess.Popen(
            [VENV_PY, TOAST, copy["title"], project, copy["accent"], iterm_session_id or "",
             copy["symbol"]],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except OSError:
        pass  # a failed notification must never break the hook

    sound = cfg.get(copy["sound_key"], "")
    if sound:
        sound_file = f"/System/Library/Sounds/{sound}.aiff"
        if os.path.exists(sound_file):
            subprocess.Popen(["afplay", sound_file],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
