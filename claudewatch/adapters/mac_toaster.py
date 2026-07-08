"""macOS implementation of the Toaster port.

Fires the floating toast (hooks/toast.py, run under the venv's PyObjC), records
the session in `.last_notified` (so the "go to notification" hotkey can find it),
and plays the sound. All I/O is wrapped so a failed notification never breaks the
hook. Copied from the legacy notify.py; the enable/focus gating already happened
in the interpreter, so this just shows.
"""

import os
import subprocess
from typing import Optional

from ..domain.effect import NotifyKind

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_TOAST = os.path.join(_ROOT, "hooks", "toast.py")
_VENV_PY = os.path.join(_ROOT, ".venv", "bin", "python")  # has PyObjC
_LAST_NOTIFIED = os.path.join(_ROOT, ".last_notified")

_RED = "#FF3B30"
_GREEN = "#34C759"

# Per-tier presentation for the toast (title, accent hex, SF Symbol name).
_STYLE = {
    NotifyKind.NEEDS_INPUT: ("Needs your input", _RED, "bell.badge.fill"),
    NotifyKind.DONE: ("Finished", _GREEN, "checkmark.circle.fill"),
}


class MacToaster:
    def show(self, kind: NotifyKind, project: str, iterm_id: str, sound: Optional[str]) -> None:
        title, accent, symbol = _STYLE[kind]

        # Remember which session this toast is about (for the "jump to notification" hotkey).
        try:
            with open(_LAST_NOTIFIED, "w") as f:
                f.write(iterm_id or "")
        except OSError:
            pass

        # Fire the toast on the active screen, detached (must not block the hook).
        try:
            subprocess.Popen(
                [_VENV_PY, _TOAST, title, project, accent, iterm_id or "", symbol],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            pass  # a failed notification must never break the hook

        if sound:
            sound_file = "/System/Library/Sounds/%s.aiff" % sound
            if os.path.exists(sound_file):
                subprocess.Popen(
                    ["afplay", sound_file],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
