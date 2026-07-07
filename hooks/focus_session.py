#!/usr/bin/env python3
"""Deep-link: bring the iTerm2 tab for a given session to the front.

Usage:
    focus_session.py <ITERM_SESSION_ID>

Accepts either the full ITERM_SESSION_ID ("w0t1p0:GUID") or just the GUID.
iTerm2 exposes each session's GUID as the AppleScript variable "session.id",
which matches the GUID portion of ITERM_SESSION_ID -- that's the join key.
Exits 0 if the session was found and focused, 1 otherwise.
"""

import subprocess
import sys
import time

APPLESCRIPT = '''
on run argv
    set targetId to item 1 of argv
    tell application "iTerm2"
        repeat with aWindow in windows
            repeat with aTab in tabs of aWindow
                repeat with aSession in sessions of aTab
                    -- the `tell ... to (variable named ...)` form works inside a
                    -- loop; the `variable named X of aSession` form errors -1723.
                    tell aSession to set sid to (variable named "session.id")
                    if sid is targetId then
                        select aWindow
                        select aTab
                        tell aSession to select
                        activate
                        return "ok"
                    end if
                end repeat
            end repeat
        end repeat
    end tell
    return "notfound"
end run
'''


def main():
    if len(sys.argv) < 2 or not sys.argv[1]:
        print("usage: focus_session.py <ITERM_SESSION_ID>", file=sys.stderr)
        sys.exit(1)

    # ITERM_SESSION_ID is "w0t1p0:GUID"; the AppleScript variable is just the GUID.
    guid = sys.argv[1].split(":", 1)[-1]

    def jump():
        return subprocess.run(
            ["osascript", "-e", APPLESCRIPT, guid], capture_output=True, text=True
        )

    # Double-activate to cross desktops (Spaces): the FIRST `activate` just grabs
    # whatever iTerm window is on the current desktop (it "captures" the activate).
    # By then `select` has made the target the current window internally, so the
    # SECOND pass -- iTerm now already frontmost -- follows that selection to its
    # desktop. This mirrors the manual "click the notification twice" behavior and
    # needs no iTerm API. If once already lands right (no local iTerm window), the
    # second pass is a harmless no-op.
    #
    # This leans on undocumented `activate` behavior + a timing gap. If it ever
    # turns flaky, the deterministic fallback is iTerm2's Python API:
    # `session.async_activate(select_tab=True, order_window_front=True)` orders the
    # specific window front by id in one call (needs "Enable Python API" + the
    # iterm2 pip package).
    result = jump()
    output = (result.stdout or result.stderr).strip()
    if output != "ok":
        print(f"could not focus session {guid}: {output}", file=sys.stderr)
        sys.exit(1)
    time.sleep(0.4)
    jump()
    sys.exit(0)


if __name__ == "__main__":
    main()
