#!/usr/bin/env python3
"""Keyboard-openable inbox panel on the screen you're focused on.

Bound to a hotkey. Lists every session in the inbox (needs-input first) on the
active screen (where the mouse is). Navigate with ↑/↓, Enter to jump to the
selected session's iTerm2 tab, Esc or click-away to close. Clicking a row jumps
directly. Chosen over opening the SwiftBar menu because that would pop on the
main display, not the screen you're using.

Must run under the project venv python (has PyObjC).
"""

import os
import sqlite3
import subprocess
import sys
import time
import warnings

warnings.simplefilter("ignore")

from AppKit import (
    NSApplication, NSApplicationActivationPolicyAccessory, NSBackingStoreBuffered,
    NSBezierPath, NSColor, NSEvent, NSFont, NSFontAttributeName,
    NSForegroundColorAttributeName, NSFloatingWindowLevel, NSScreen, NSString, NSView,
    NSWindow, NSWindowStyleMaskBorderless,
)
from Foundation import NSMakeRect, NSObject

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "inbox.db")
FOCUS = os.path.join(ROOT, "hooks", "focus_session.py")

RED, GREEN, GRAY = "#FF3B30", "#34C759", "#8E8E93"
PAD, HEADER_H, ROW_H, WIDTH = 10, 34, 34, 360

SESSIONS = []   # list of (session_id, project, state, updated_at, iterm_session_id)
SELECTED = 0
NOW = 0
WIN = None      # window + view + top-anchor, set in main() so we can rebuild on delete
VIEW = None
TOP = 0
LEFT = 0


def color(hexstr, alpha=1.0):
    h = hexstr.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    return NSColor.colorWithSRGBRed_green_blue_alpha_(r, g, b, alpha)


def age(seconds):
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    return f"{seconds // 3600}h"


def load_sessions():
    if not os.path.exists(DB_PATH):
        return []
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    try:
        return conn.execute(
            """
            SELECT session_id, project, state, updated_at, iterm_session_id FROM sessions
            ORDER BY CASE state WHEN 'needs_input' THEN 0 ELSE 1 END, updated_at ASC
            """
        ).fetchall()
    finally:
        conn.close()


def jump(idx):
    if 0 <= idx < len(SESSIONS):
        iterm = SESSIONS[idx][4]
        if iterm:
            subprocess.Popen(["/usr/bin/python3", FOCUS, iterm])
    NSApplication.sharedApplication().terminate_(None)


def delete_session(idx):
    """Dismiss a session from the inbox, then rebuild the panel in place."""
    global SELECTED
    if not (0 <= idx < len(SESSIONS)):
        return
    sid = SESSIONS[idx][0]
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    try:
        conn.execute("DELETE FROM sessions WHERE session_id = ?", (sid,))
        conn.commit()
    finally:
        conn.close()
    rebuild()


def rebuild():
    global SESSIONS, SELECTED
    SESSIONS = load_sessions()
    if SELECTED >= len(SESSIONS):
        SELECTED = max(0, len(SESSIONS) - 1)
    n = max(1, len(SESSIONS))
    h = HEADER_H + n * ROW_H + PAD
    # keep the top edge anchored while the height shrinks
    WIN.setFrame_display_(NSMakeRect(LEFT, TOP - h, WIDTH, h), True)
    VIEW.setFrame_(NSMakeRect(0, 0, WIDTH, h))
    VIEW.setNeedsDisplay_(True)


def draw_text(s, x, y, w, h, size, col, bold=False):
    font = NSFont.boldSystemFontOfSize_(size) if bold else NSFont.systemFontOfSize_(size)
    attrs = {NSFontAttributeName: font, NSForegroundColorAttributeName: col}
    NSString.stringWithString_(s).drawInRect_withAttributes_(NSMakeRect(x, y, w, h), attrs)


class KeyPanel(NSWindow):
    def canBecomeKeyWindow(self):
        return True


class PanelView(NSView):
    def acceptsFirstResponder(self):
        return True

    def drawRect_(self, rect):
        H = self.bounds().size.height
        draw_text("Claude Sessions", PAD + 6, H - HEADER_H + 6, WIDTH - 20, 22, 13,
                  NSColor.whiteColor(), bold=True)

        if not SESSIONS:
            draw_text("No sessions waiting ✨", PAD + 6, H - HEADER_H - 26, WIDTH - 20, 20,
                      12, color(GRAY))
            return

        for i, (_, project, state, updated_at, _iterm) in enumerate(SESSIONS):
            row_y = H - HEADER_H - (i + 1) * ROW_H
            if i == SELECTED:
                hl = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                    NSMakeRect(PAD, row_y + 2, WIDTH - 2 * PAD, ROW_H - 4), 8, 8)
                color("#ffffff", 0.10).set()
                hl.fill()
            accent = RED if state == "needs_input" else GREEN
            glyph = "●" if state == "needs_input" else "✓"
            ty = row_y + (ROW_H - 18) / 2
            draw_text(glyph, PAD + 10, ty, 16, 18, 13, color(accent))
            draw_text(project, PAD + 32, ty, WIDTH - 150, 18, 12, NSColor.whiteColor())
            draw_text(age(NOW - updated_at), WIDTH - 100, ty, 44, 18, 11, color(GRAY))
            # dismiss affordance on the right
            draw_text("✕", WIDTH - 28, ty, 18, 18, 12, color(GRAY))

    # rightmost strip of a row is the ✕ (delete) hit zone
    DELETE_ZONE = 40

    def _row_at(self, point):
        H = self.bounds().size.height
        i = int((H - HEADER_H - point.y) // ROW_H)
        return i if 0 <= i < len(SESSIONS) else -1

    def mouseDown_(self, event):
        p = self.convertPoint_fromView_(event.locationInWindow(), None)
        idx = self._row_at(p)
        if idx < 0:
            return
        if p.x >= WIDTH - self.DELETE_ZONE:   # clicked the ✕
            delete_session(idx)
        else:
            jump(idx)

    def keyDown_(self, event):
        global SELECTED
        code = event.keyCode()
        if code == 53:  # esc
            NSApplication.sharedApplication().terminate_(None)
        elif code == 36 and SESSIONS:  # return -> jump
            jump(SELECTED)
        elif code in (7, 51) and SESSIONS:  # 'x' key or delete/backspace -> dismiss selected
            delete_session(SELECTED)
        elif code == 126 and SESSIONS:  # up
            SELECTED = max(0, SELECTED - 1)
            self.setNeedsDisplay_(True)
        elif code == 125 and SESSIONS:  # down
            SELECTED = min(len(SESSIONS) - 1, SELECTED + 1)
            self.setNeedsDisplay_(True)


class Delegate(NSObject):
    def windowDidResignKey_(self, note):
        NSApplication.sharedApplication().terminate_(None)


def main():
    global SESSIONS, NOW, WIN, VIEW, TOP, LEFT
    try:
        with open("/tmp/claude_inbox_panel.log", "a") as f:
            f.write(f"panel fired {int(time.time())}\n")
    except OSError:
        pass
    SESSIONS = load_sessions()
    NOW = int(time.time())

    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

    n = max(1, len(SESSIONS))
    H = HEADER_H + n * ROW_H + PAD
    mouse = NSEvent.mouseLocation()
    screen = next((s for s in NSScreen.screens()
                   if s.frame().origin.x <= mouse.x < s.frame().origin.x + s.frame().size.width
                   and s.frame().origin.y <= mouse.y < s.frame().origin.y + s.frame().size.height),
                  NSScreen.mainScreen())
    f = screen.frame()
    x = f.origin.x + f.size.width - WIDTH - 22
    y = f.origin.y + f.size.height - H - 22

    win = KeyPanel.alloc().initWithContentRect_styleMask_backing_defer_(
        NSMakeRect(x, y, WIDTH, H), NSWindowStyleMaskBorderless, NSBackingStoreBuffered, False)
    win.setLevel_(NSFloatingWindowLevel)
    win.setOpaque_(False)
    win.setBackgroundColor_(NSColor.clearColor())

    view = PanelView.alloc().initWithFrame_(NSMakeRect(0, 0, WIDTH, H))
    view.setWantsLayer_(True)
    view.layer().setBackgroundColor_(color("#1c1c1e", 0.97).CGColor())
    view.layer().setCornerRadius_(14.0)
    win.setContentView_(view)

    WIN, VIEW, LEFT, TOP = win, view, x, y + H  # top edge stays fixed on rebuild

    delegate = Delegate.alloc().init()
    win.setDelegate_(delegate)
    win.makeKeyAndOrderFront_(None)
    win.makeFirstResponder_(view)
    app.activateIgnoringOtherApps_(True)
    globals()["_delegate"] = delegate  # keep alive
    app.run()


if __name__ == "__main__":
    main()
