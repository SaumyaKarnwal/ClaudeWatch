#!/usr/bin/env python3
"""ClaudeWatch menu-bar app — the always-visible badge (replaces SwiftBar).

A native NSStatusItem showing an icon + count of sessions needing you, refreshed
every few seconds (and self-healing stale rows). Left-click opens the SAME
active-screen inbox panel used by the ⌘⌃O hotkey, so there's one consistent UI.
Right-click (or ctrl-click) shows a small admin menu.

Run under the project venv python (has PyObjC). Meant to run persistently.
"""

import os
import sqlite3
import subprocess
import time
import warnings

warnings.simplefilter("ignore")

import objc

from AppKit import (
    NSApplication, NSApplicationActivationPolicyAccessory, NSColor,
    NSEventMaskLeftMouseUp, NSEventMaskRightMouseUp, NSEventModifierFlagControl,
    NSEventTypeRightMouseUp, NSImage, NSImageSymbolConfiguration, NSMenu, NSMenuItem,
    NSStatusBar, NSTimer, NSVariableStatusItemLength,
)
from Foundation import NSObject

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "inbox.db")
PANEL = os.path.join(ROOT, "hooks", "panel.py")
ADMIN = os.path.join(ROOT, "hooks", "inbox_admin.py")
APPLY = os.path.join(ROOT, "hooks", "apply_config.py")
VENV_PY = os.path.join(ROOT, ".venv", "bin", "python")
PY = "/usr/bin/python3"

DONE_TTL = 30 * 60
NEEDS_TTL = 8 * 60 * 60
TICK = 0  # refresh counter; the (expensive) iTerm2 prune runs only every Nth tick

LIST_LIVE_GUIDS = '''
set ids to {}
tell application "iTerm2"
    repeat with w in windows
        repeat with t in tabs of w
            repeat with s in sessions of t
                tell s to set end of ids to (variable named "session.id")
            end repeat
        end repeat
    end repeat
end tell
set AppleScript's text item delimiters to linefeed
return ids as text
'''


def live_guids():
    try:
        out = subprocess.run(["osascript", "-e", LIST_LIVE_GUIDS],
                             capture_output=True, text=True, timeout=3).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return None
    return {ln.strip() for ln in out.splitlines() if ln.strip()}


def expire_by_time(conn):
    """Cheap, pure-SQL zombie expiry. Safe to run every refresh."""
    now = int(time.time())
    conn.execute("DELETE FROM sessions WHERE state='done' AND updated_at < ?", (now - DONE_TTL,))
    conn.execute("DELETE FROM sessions WHERE state='needs_input' AND updated_at < ?", (now - NEEDS_TTL,))
    conn.commit()


def prune_dead_tabs(conn):
    """Drop rows whose iTerm2 tab is gone. Costs one AppleScript round-trip, so
    it's throttled (called only occasionally, not every refresh)."""
    guids = live_guids()
    if guids is None:
        return
    rows = conn.execute("SELECT session_id, iterm_session_id FROM sessions WHERE iterm_session_id != ''").fetchall()
    dead = [sid for sid, it in rows if it.split(":", 1)[-1] not in guids]
    if dead:
        conn.executemany("DELETE FROM sessions WHERE session_id=?", [(s,) for s in dead])
        conn.commit()


class Controller(NSObject):
    @objc.python_method
    def setup(self):
        self.item = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
        button = self.item.button()
        button.setTarget_(self)
        button.setAction_("clicked:")
        button.sendActionOn_(NSEventMaskLeftMouseUp | NSEventMaskRightMouseUp)
        self.refresh_(None)
        self.timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            3.0, self, "refresh:", None, True)
        return self

    def refresh_(self, timer):
        global TICK
        TICK += 1
        needs = done = 0
        if os.path.exists(DB_PATH):
            conn = sqlite3.connect(DB_PATH, timeout=5.0)
            try:
                expire_by_time(conn)              # cheap SQL, every 3s
                if TICK % 10 == 1:                # AppleScript prune ~every 30s (and on start)
                    prune_dead_tabs(conn)
                needs = conn.execute("SELECT COUNT(*) FROM sessions WHERE state='needs_input'").fetchone()[0]
                done = conn.execute("SELECT COUNT(*) FROM sessions WHERE state='done'").fetchone()[0]
            finally:
                conn.close()
        self._render(needs, done)

    @objc.python_method
    def _render(self, needs, done):
        if needs:
            sym, col, txt = "bell.badge.fill", NSColor.systemRedColor(), f" {needs}"
        elif done:
            sym, col, txt = "checkmark.circle.fill", NSColor.systemGreenColor(), f" {done}"
        else:
            sym, col, txt = "moon.zzz.fill", NSColor.secondaryLabelColor(), ""
        button = self.item.button()
        img = NSImage.imageWithSystemSymbolName_accessibilityDescription_(sym, None)
        if img is not None:
            try:
                cfg = NSImageSymbolConfiguration.configurationWithPaletteColors_([col])
                img = img.imageWithSymbolConfiguration_(cfg)
                img.setTemplate_(False)
            except Exception:
                img.setTemplate_(True)
            button.setImage_(img)
        button.setTitle_(txt)

    def clicked_(self, sender):
        ev = NSApplication.sharedApplication().currentEvent()
        right = ev is not None and (ev.type() == NSEventTypeRightMouseUp
                                    or bool(ev.modifierFlags() & NSEventModifierFlagControl))
        if right:
            self._menu()
        else:
            subprocess.Popen([VENV_PY, PANEL])

    @objc.python_method
    def _menu(self):
        menu = NSMenu.alloc().init()
        for title, sel in [("Open Inbox", "openPanel:"), ("Clear Finished", "clearFinished:"),
                           ("Edit Settings…", "editSettings:")]:
            it = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, sel, "")
            it.setTarget_(self)
            menu.addItem_(it)
        menu.addItem_(NSMenuItem.separatorItem())
        q = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Quit ClaudeWatch", "quit:", "")
        q.setTarget_(self)
        menu.addItem_(q)
        self.item.popUpStatusItemMenu_(menu)

    def openPanel_(self, s):
        subprocess.Popen([VENV_PY, PANEL])

    def clearFinished_(self, s):
        subprocess.Popen([PY, ADMIN, "clear-finished"])

    def editSettings_(self, s):
        subprocess.Popen([VENV_PY, os.path.join(ROOT, "hooks", "settings.py")])

    def quit_(self, s):
        NSApplication.sharedApplication().terminate_(None)


def main():
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    globals()["_ctrl"] = Controller.alloc().init().setup()
    app.run()


if __name__ == "__main__":
    main()
