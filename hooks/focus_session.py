#!/usr/bin/env python3
"""Deep-link: bring the iTerm2 tab for a given session to the front, across Spaces.

Selects the target session (by GUID) and activates iTerm. Crossing to another
desktop (Space) can need a SECOND `activate`: the first one only grabs whatever
iTerm window is on your current desktop, and by then `select` has made the target
the current window internally, so a second activate -- iTerm already frontmost --
follows that selection across.

But that second activate re-focuses iTerm, and if you've since moved it re-grabs
focus on the new desktop. So we only do it when the first pass did NOT already
land on the target's desktop (i.e. a same-desktop jump, or a cross where iTerm had
no local window to capture the first activate, both need just one). System Events
lists only current-desktop windows, so "is the target window visible now?" tells
us whether we already landed.

Usage: focus_session.py <ITERM_SESSION_ID>   (full "wNtNpN:GUID" or bare GUID)
"""

import subprocess
import sys
import time

# Select the session's window/tab, activate iTerm, and return the window's
# "<left> <top>" (so we can tell whether we landed on its desktop). "notfound" if
# no session matches.
SELECT_AND_ACTIVATE = '''
on run argv
    set targetId to item 1 of argv
    tell application "iTerm2"
        repeat with aWindow in windows
            repeat with aTab in tabs of aWindow
                repeat with aSession in sessions of aTab
                    -- `tell ... to (variable named ...)` works in the loop;
                    -- `variable named X of aSession` errors -1723.
                    tell aSession to set sid to (variable named "session.id")
                    if sid is targetId then
                        select aWindow
                        select aTab
                        tell aSession to select
                        activate
                        set b to bounds of aWindow
                        return (item 1 of b as string) & " " & (item 2 of b as string)
                    end if
                end repeat
            end repeat
        end repeat
    end tell
    return "notfound"
end run
'''

# System Events only lists windows on the CURRENT desktop, so "is an iTerm window
# at (left, top) visible right now?" answers "are we already on the target's
# desktop?" Small tolerance (<=3px): iTerm bounds vs the OS position can differ ~1px.
ON_CURRENT_DESKTOP = '''
on run argv
    set L to (item 1 of argv) as integer
    set T to (item 2 of argv) as integer
    tell application "System Events" to tell process "iTerm2"
        repeat with w in windows
            set p to position of w
            if (((item 1 of p) - L) ^ 2 + ((item 2 of p) - T) ^ 2) <= 9 then return "yes"
        end repeat
    end tell
    return "no"
end run
'''


def osascript(script, *args):
    return subprocess.run(
        ["osascript", "-e", script, *args], capture_output=True, text=True
    )


def main():
    if len(sys.argv) < 2 or not sys.argv[1]:
        print("usage: focus_session.py <ITERM_SESSION_ID>", file=sys.stderr)
        sys.exit(1)
    # ITERM_SESSION_ID is "wNtNpN:GUID"; the AppleScript variable is just the GUID.
    guid = sys.argv[1].split(":", 1)[-1]

    # Pass 1: select the target + activate. Grabs the local-desktop window if there
    # is one; otherwise it already crosses.
    output = (osascript(SELECT_AND_ACTIVATE, guid).stdout or "").strip()
    parts = output.split()
    if output == "notfound" or len(parts) != 2:
        print(f"could not focus session {guid}: {output}", file=sys.stderr)
        sys.exit(1)
    left, top = parts

    # Did pass 1 land us on the target's desktop? If the target window is visible on
    # the current desktop now, yes -> done, no second activate (so we don't re-grab
    # focus). If not, a local window captured the first activate -> do the second
    # activate to follow the selection across. On any error we fall back to doing
    # the second pass (the old always-double behavior), which is never worse.
    on_desktop = (osascript(ON_CURRENT_DESKTOP, left, top).stdout or "").strip()
    if on_desktop != "yes":
        time.sleep(0.4)
        osascript(SELECT_AND_ACTIVATE, guid)
    sys.exit(0)


if __name__ == "__main__":
    main()
