#!/usr/bin/env python3
"""A floating toast popup on the screen you're currently focused on.

    toast.py "<title>" "<message>" [accent_hex] [iterm_session_id]

Unlike a macOS notification banner (which sticks to the main display and can be
swallowed by Focus modes), this is a borderless floating window we place at the
top-right of the screen containing the mouse -- i.e. the screen you're using. It
does not steal focus, auto-dismisses after a few seconds, and if given an iTerm2
session id, clicking it jumps to that tab.

Must run under the project venv python (has PyObjC).
"""

import os
import subprocess
import sys
import warnings

warnings.simplefilter("ignore")  # hide PyObjC CGColor pointer warnings

from AppKit import (
    NSApplication, NSApplicationActivationPolicyAccessory, NSBackingStoreBuffered,
    NSColor, NSEvent, NSFont, NSFloatingWindowLevel, NSImage, NSImageScaleProportionallyUpOrDown,
    NSImageView, NSScreen, NSTextField, NSView, NSWindow, NSWindowStyleMaskBorderless,
)
from Foundation import NSMakeRect, NSObject, NSTimer

ROOT = os.path.expanduser("~/projects/claude-session-inbox")
FOCUS = os.path.join(ROOT, "hooks", "focus_session.py")

SESSION = None  # iTerm2 session id to jump to on click (set from argv)


def color(hexstr, alpha=1.0):
    h = hexstr.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    return NSColor.colorWithSRGBRed_green_blue_alpha_(r, g, b, alpha)


class ToastView(NSView):
    def mouseDown_(self, event):
        if SESSION:
            subprocess.Popen(["/usr/bin/python3", FOCUS, SESSION])
        NSApplication.sharedApplication().terminate_(None)


class Closer(NSObject):
    def close_(self, timer):
        NSApplication.sharedApplication().terminate_(None)


def active_screen():
    """The screen containing the mouse -- the one the user is focused on."""
    mouse = NSEvent.mouseLocation()
    for s in NSScreen.screens():
        f = s.frame()
        if (f.origin.x <= mouse.x < f.origin.x + f.size.width
                and f.origin.y <= mouse.y < f.origin.y + f.size.height):
            return s
    return NSScreen.mainScreen()


def add_label(view, text, x, y, w, h, size, col, bold=False):
    tf = NSTextField.alloc().initWithFrame_(NSMakeRect(x, y, w, h))
    tf.setStringValue_(text)
    tf.setBezeled_(False)
    tf.setDrawsBackground_(False)
    tf.setEditable_(False)
    tf.setSelectable_(False)
    tf.setTextColor_(col)
    tf.setFont_(NSFont.boldSystemFontOfSize_(size) if bold else NSFont.systemFontOfSize_(size))
    view.addSubview_(tf)


def main():
    global SESSION
    title = sys.argv[1] if len(sys.argv) > 1 else "Claude"
    message = sys.argv[2] if len(sys.argv) > 2 else ""
    accent = sys.argv[3] if len(sys.argv) > 3 else "#FF3B30"
    SESSION = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] else None
    symbol = sys.argv[5] if len(sys.argv) > 5 and sys.argv[5] else "bell.badge.fill"

    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)  # no dock icon

    W, H, margin = 380, 82, 22
    f = active_screen().frame()
    x = f.origin.x + f.size.width - W - margin
    y = f.origin.y + f.size.height - H - margin  # top of that screen

    win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        NSMakeRect(x, y, W, H), NSWindowStyleMaskBorderless, NSBackingStoreBuffered, False)
    win.setLevel_(NSFloatingWindowLevel)
    win.setOpaque_(False)
    win.setBackgroundColor_(NSColor.clearColor())

    view = ToastView.alloc().initWithFrame_(NSMakeRect(0, 0, W, H))
    view.setWantsLayer_(True)
    view.layer().setBackgroundColor_(color("#ffffff", 0.98).CGColor())
    view.layer().setCornerRadius_(16.0)
    view.layer().setBorderWidth_(0.5)
    view.layer().setBorderColor_(color("#000000", 0.06).CGColor())
    win.setHasShadow_(True)

    # rounded accent chip with a white SF Symbol inside -- iOS-notification style
    chip = NSView.alloc().initWithFrame_(NSMakeRect(16, H / 2 - 20, 40, 40))
    chip.setWantsLayer_(True)
    chip.layer().setBackgroundColor_(color(accent).CGColor())
    chip.layer().setCornerRadius_(11.0)
    view.addSubview_(chip)

    icon_img = NSImage.imageWithSystemSymbolName_accessibilityDescription_(symbol, None)
    if icon_img is not None:
        iv = NSImageView.alloc().initWithFrame_(NSMakeRect(9, 9, 22, 22))
        iv.setImage_(icon_img)
        iv.setImageScaling_(NSImageScaleProportionallyUpOrDown)
        iv.setContentTintColor_(NSColor.whiteColor())
        chip.addSubview_(iv)

    add_label(view, title, 70, H - 37, W - 86, 22, 15, color("#111114"), bold=True)
    add_label(view, message, 70, H - 59, W - 86, 18, 12, color("#8a8a8e"))

    win.setContentView_(view)
    win.orderFrontRegardless()  # show without stealing keyboard focus

    closer = Closer.alloc().init()
    NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        6.5, closer, "close:", None, False)
    app.run()


if __name__ == "__main__":
    main()
