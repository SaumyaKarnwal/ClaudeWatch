#!/usr/bin/env python3
"""ClaudeWatch settings window — record shortcuts + tune notifications.

Shortcuts: click Record, press a combo; it's saved to config.json and applied to
skhd immediately. Notifications: checkboxes + sound dropdowns, saved live.

skhd is a *global* hotkey listener, so while this window is open we suspend it —
otherwise pressing a combo that's already bound would trigger it instead of being
recorded. It's resumed (with any new bindings) when the window closes.

Run under the project venv python (has PyObjC).
"""

import json
import os
import subprocess
import warnings

warnings.simplefilter("ignore")

import objc
from AppKit import (
    NSApplication, NSApplicationActivationPolicyAccessory, NSBackingStoreBuffered,
    NSBeep, NSBezelStyleRounded, NSButton, NSButtonTypeSwitch, NSColor, NSEvent,
    NSEventModifierFlagCommand, NSEventModifierFlagControl, NSEventModifierFlagOption,
    NSEventModifierFlagShift, NSFont, NSPopUpButton, NSScreen, NSTextAlignmentCenter,
    NSTextField, NSView, NSWindow, NSWindowStyleMaskClosable, NSWindowStyleMaskTitled,
)
from Foundation import NSMakeRect, NSObject

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "config.json")
APPLY = os.path.join(ROOT, "hooks", "apply_config.py")
PY = "/usr/bin/python3"
SKHD = "/opt/homebrew/bin/skhd"

SHORTCUTS = [
    ("panel_hotkey", "Open inbox"),
    ("notify_hotkey", "Go to notification"),
    ("hotkey", "Cycle sessions"),
]
TOGGLES = [
    ("notify_on_needs_input", "Notify when a session needs input"),
    ("notify_on_done", "Notify when a session finishes"),
    ("suppress_when_focused", "Stay silent for the session I'm viewing"),
]
SOUNDS = [("sound_needs_input", "Needs-input sound"), ("sound_done", "Finished sound")]

RESERVED = {
    (frozenset({"cmd"}), "0x31"), (frozenset({"ctrl"}), "0x31"), (frozenset({"alt"}), "0x31"),
    (frozenset({"cmd"}), "0x32"), (frozenset({"cmd"}), "0x30"),
    (frozenset({"cmd"}), "q"), (frozenset({"cmd"}), "w"),
    (frozenset({"cmd"}), "h"), (frozenset({"cmd"}), "m"),
}
MOD_SYMBOL = {"cmd": "⌘", "ctrl": "⌃", "alt": "⌥", "shift": "⇧"}
KEY_SYMBOL = {"0x31": "Space", "0x32": "`", "0x30": "⇥", "0x24": "⏎"}

RECORDING = None
WIDGETS = {}
STATUS = None
PILL = None
WIN = None
VIEW = None


def sound_names():
    d = "/System/Library/Sounds"
    try:
        return sorted(f[:-5] for f in os.listdir(d) if f.endswith(".aiff"))
    except OSError:
        return ["Ping", "Glass", "Pop", "Tink"]


def event_to_combo(flags, keycode, chars):
    mods = []
    if flags & NSEventModifierFlagControl:
        mods.append("ctrl")
    if flags & NSEventModifierFlagOption:
        mods.append("alt")
    if flags & NSEventModifierFlagShift:
        mods.append("shift")
    if flags & NSEventModifierFlagCommand:
        mods.append("cmd")
    if not mods:
        return None, "Use at least one modifier (⌘ ⌃ ⌥)."
    if chars and len(chars) == 1 and chars.isascii() and chars.isalnum():
        key = chars.lower()
    else:
        key = "0x%x" % keycode
    if (frozenset(mods), key) in RESERVED:
        return None, "macOS already uses that — pick another."
    return " + ".join(mods) + " - " + key, None


def pretty(combo):
    if not combo:
        return "—"
    mod_part, _, key = combo.replace(" ", "").partition("-")
    mods = "".join(MOD_SYMBOL.get(m, m) for m in mod_part.split("+") if m)
    return mods + KEY_SYMBOL.get(key, key.upper())


def load_config():
    try:
        with open(CONFIG) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_config(key, value):
    cfg = load_config()
    cfg[key] = value
    with open(CONFIG, "w") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")


def set_status(text, kind="hint"):
    """Update the status line as a colored pill: error=red+⚠+beep, ok=green+✓, hint=quiet."""
    if kind == "error":
        fg, tint, text = NSColor.systemRedColor(), NSColor.systemRedColor(), "⚠  " + text
        NSBeep()
    else:
        fg, tint, text = NSColor.tertiaryLabelColor(), None, text
    STATUS.setStringValue_(text)
    STATUS.setTextColor_(fg)
    bg = tint.colorWithAlphaComponent_(0.15) if tint else NSColor.clearColor()
    PILL.layer().setBackgroundColor_(bg.CGColor())


def skhd_suspend():
    subprocess.run([SKHD, "--stop-service"], capture_output=True)


def skhd_resume():
    subprocess.run([SKHD, "--start-service"], capture_output=True)
    subprocess.run([SKHD, "--reload"], capture_output=True)


class RecorderView(NSView):
    def acceptsFirstResponder(self):
        return True

    def keyDown_(self, event):
        global RECORDING
        if event.keyCode() == 53:  # esc
            if RECORDING:
                _stop_recording()
                set_status("Click Record, then press your shortcut.", "hint")
            else:
                WIN.performClose_(None)
            return
        if not RECORDING:
            return
        combo, err = event_to_combo(event.modifierFlags(), event.keyCode(),
                                    event.charactersIgnoringModifiers())
        if err:
            set_status(err, "error")
            _stop_recording()
            return
        subprocess.run([PY, APPLY, "set", RECORDING, combo], capture_output=True)
        WIDGETS[RECORDING][0].setStringValue_(pretty(combo))  # the row updating is the confirmation
        set_status("Click Record, then press your shortcut.", "hint")
        _stop_recording()


def _stop_recording():
    global RECORDING
    if RECORDING:
        WIDGETS[RECORDING][1].setTitle_("Record")
    RECORDING = None


class Delegate(NSObject):
    def windowWillClose_(self, note):
        skhd_resume()
        NSApplication.sharedApplication().terminate_(None)


class Controller(NSObject):
    def record_(self, sender):
        global RECORDING
        _stop_recording()
        RECORDING = SHORTCUTS[sender.tag()][0]
        sender.setTitle_("Press keys…")
        set_status("Listening — press your shortcut (Esc to cancel)", "hint")
        WIN.makeFirstResponder_(VIEW)

    def toggle_(self, sender):
        save_config(TOGGLES[sender.tag()][0], bool(sender.state()))  # checkbox state = confirmation

    def soundChanged_(self, sender):
        title = sender.titleOfSelectedItem()
        save_config(SOUNDS[sender.tag()][0], "" if title == "None" else title)  # dropdown = confirmation


def _label(text, x, y, w, h, size, col, bold=False, align_right=False):
    tf = NSTextField.alloc().initWithFrame_(NSMakeRect(x, y, w, h))
    tf.setStringValue_(text)
    tf.setBezeled_(False)
    tf.setDrawsBackground_(False)
    tf.setEditable_(False)
    tf.setSelectable_(False)
    tf.setTextColor_(col)
    tf.setFont_(NSFont.boldSystemFontOfSize_(size) if bold else NSFont.systemFontOfSize_(size))
    if align_right:
        tf.setAlignment_(2)
    return tf


def main():
    global STATUS, PILL, WIN, VIEW
    cfg = load_config()
    skhd_suspend()  # so recording captures keys instead of triggering bound shortcuts

    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    controller = Controller.alloc().init()

    W, H = 470, 470
    m = NSEvent.mouseLocation()
    screen = next((s for s in NSScreen.screens()
                   if s.frame().origin.x <= m.x < s.frame().origin.x + s.frame().size.width
                   and s.frame().origin.y <= m.y < s.frame().origin.y + s.frame().size.height),
                  NSScreen.mainScreen())
    sf = screen.frame()
    win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        NSMakeRect(sf.origin.x + (sf.size.width - W) / 2, sf.origin.y + (sf.size.height - H) / 2, W, H),
        NSWindowStyleMaskTitled | NSWindowStyleMaskClosable, NSBackingStoreBuffered, False)
    win.setTitle_("ClaudeWatch Settings")
    view = RecorderView.alloc().initWithFrame_(NSMakeRect(0, 0, W, H))
    win.setContentView_(view)

    y = H - 16

    def header(text):
        nonlocal y
        y -= 24
        view.addSubview_(_label(text, 20, y, W - 40, 22, 14, NSColor.labelColor(), bold=True))
        y -= 8

    header("Keyboard shortcuts")
    for i, (key, label) in enumerate(SHORTCUTS):
        y -= 38
        view.addSubview_(_label(label, 20, y + 4, 180, 22, 13, NSColor.labelColor()))
        combo_lbl = _label(pretty(cfg.get(key, "")), 200, y + 4, 110, 22, 14,
                           NSColor.secondaryLabelColor(), align_right=True)
        view.addSubview_(combo_lbl)
        btn = NSButton.alloc().initWithFrame_(NSMakeRect(W - 120, y, 100, 30))
        btn.setTitle_("Record")
        btn.setBezelStyle_(NSBezelStyleRounded)
        btn.setTarget_(controller)
        btn.setAction_("record:")
        btn.setTag_(i)
        view.addSubview_(btn)
        WIDGETS[key] = (combo_lbl, btn)

    y -= 12
    header("Notifications")
    for i, (key, label) in enumerate(TOGGLES):
        y -= 28
        chk = NSButton.alloc().initWithFrame_(NSMakeRect(20, y, W - 40, 24))
        chk.setButtonType_(NSButtonTypeSwitch)
        chk.setTitle_("  " + label)
        chk.setState_(1 if cfg.get(key, True) else 0)
        chk.setTarget_(controller)
        chk.setAction_("toggle:")
        chk.setTag_(i)
        view.addSubview_(chk)

    names = ["None"] + sound_names()
    for i, (key, label) in enumerate(SOUNDS):
        y -= 34
        view.addSubview_(_label(label, 20, y + 3, 160, 22, 13, NSColor.labelColor()))
        pop = NSPopUpButton.alloc().initWithFrame_pullsDown_(NSMakeRect(190, y, 160, 26), False)
        pop.addItemsWithTitles_(names)
        pop.selectItemWithTitle_(cfg.get(key) or "None")
        pop.setTarget_(controller)
        pop.setAction_("soundChanged:")
        pop.setTag_(i)
        view.addSubview_(pop)

    # status pill: a rounded container with the label centered both ways inside it
    y -= 40
    PILL = NSView.alloc().initWithFrame_(NSMakeRect(20, y, W - 40, 30))
    PILL.setWantsLayer_(True)
    PILL.layer().setCornerRadius_(7.0)
    STATUS = _label("", 0, 7, W - 40, 16, 12, NSColor.tertiaryLabelColor())
    STATUS.setAlignment_(NSTextAlignmentCenter)
    PILL.addSubview_(STATUS)
    view.addSubview_(PILL)
    set_status("Click Record, then press your shortcut.", "hint")

    delegate = Delegate.alloc().init()
    win.setDelegate_(delegate)
    WIN, VIEW = win, view
    win.makeKeyAndOrderFront_(None)
    app.activateIgnoringOtherApps_(True)
    globals()["_refs"] = (controller, delegate)
    try:
        app.run()
    finally:
        skhd_resume()  # safety net: never leave skhd suspended


if __name__ == "__main__":
    main()
