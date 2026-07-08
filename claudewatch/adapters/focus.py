"""Focus probe — "is the user looking at this exact iTerm2 session right now?"

One AppleScript round-trip asks System Events for the frontmost app and, if it's
iTerm2, the focused session's guid. Injected into the Interpreter so notifications
stay silent for the tab you're already viewing. Copied from the legacy notify.py;
errs toward notifying if it can't tell.
"""

import subprocess

# One round-trip: frontmost app name + (if iTerm2) the focused session's guid.
_FOCUS_PROBE = '''
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


def is_focused_on(iterm_session_id: str) -> bool:
    """True iff iTerm2 is frontmost AND its active session is this one."""
    guid = iterm_session_id.split(":", 1)[-1]
    try:
        out = subprocess.run(
            ["osascript", "-e", _FOCUS_PROBE], capture_output=True, text=True, timeout=3
        ).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return False  # if we can't tell, err toward notifying
    front, _, focused_guid = out.partition("|||")
    return front == "iTerm2" and focused_guid == guid
