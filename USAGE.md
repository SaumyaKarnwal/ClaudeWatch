# Using & Configuring ClaudeWatch

How to operate ClaudeWatch day to day, and how to change its settings.
(For install + permissions, see the [README](README.md).)

---

## The menu-bar badge

The badge in your menu bar shows what's happening:

| Badge | Meaning |
|---|---|
| 🔔 **red + count** | that many sessions are **waiting on you** |
| ✓ **green + count** | sessions have **finished** (nothing blocking) |
| 🌙 grey | nothing needs you |

- **Left-click** → opens the inbox panel on the screen you're using.
- **Right-click** (or ⌃-click) → menu: Open Inbox · Clear Finished · Edit Settings · Quit.

---

## Notifications (toasts)

When a **background** session (one you're *not* looking at) changes state, a toast pops
on your active screen:

- 🔴 **Needs your input** — red, with a sound. Something is blocked on you.
- 🟢 **Finished** — green, quiet. A task completed.

**Click the toast** to jump straight to that session's iTerm2 tab. If you're already
looking at that session, no toast fires (it would just be noise).

---

## Keyboard shortcuts

| Default | Action |
|---|---|
| `⌥\`` | Open the inbox panel on your active screen |
| `⌘⌃N` | Jump to the session the current notification is about |
| `⌃\`` | Cycle through waiting sessions (press again for the next) |

**In the inbox panel:**

| Key | Action |
|---|---|
| `↑` / `↓` | move the selection |
| `Enter` | jump to the selected session's tab |
| `x` | dismiss the selected session from the inbox |
| `Esc` | close the panel |

---

## Settings (the easy way)

**Right-click the menu-bar badge ▸ "Edit Settings…"** to open the Settings window — no
files, no syntax:

- **Keyboard shortcuts** — click **Record** on a row, then press the combo you want. It's
  saved and goes live when you close the window. If you press something macOS already
  owns (e.g. ⌘\`), a red ⚠ warning appears and it isn't saved — just pick another.
- **Notifications** — checkboxes: notify on needs-input, notify on finished, and stay
  silent for the session you're viewing.
- **Sounds** — dropdowns to pick the needs-input and finished sounds (or None).

Notification changes apply instantly. Shortcuts go live when you close the window —
while it's open, global hotkeys are paused so your keypress is *recorded* rather than
triggering an existing shortcut.

### Editing `config.json` directly (optional)
Everything above is stored in `config.json` if you prefer to edit by hand. Notification
keys (`notify_on_needs_input`, `notify_on_done`, `suppress_when_focused`,
`sound_needs_input`, `sound_done`) apply on the next event. Shortcut keys (`hotkey`,
`panel_hotkey`, `notify_hotkey`) use skhd syntax — `modifier + modifier - key`, e.g.
`alt - 0x32` (⌥\`), `cmd + ctrl - n` (⌘⌃N) — and need `python3 hooks/apply_config.py`
to take effect.

---

## Troubleshooting

**Badge missing from the menu bar** → the app may not be running:
```bash
launchctl kickstart -k gui/$(id -u)/com.claudewatch.menubar
```

**A shortcut doesn't fire** →
- Confirm skhd is running: `pgrep -x skhd` (start it with `skhd --start-service`).
- Confirm skhd has **Accessibility** permission (System Settings ▸ Privacy & Security ▸ Accessibility).
- Re-apply after editing: `python3 hooks/apply_config.py`.
- Make sure the combo doesn't clash with a macOS or app shortcut.

**No toast appears** →
- It only fires for sessions you're **not** currently viewing (by design).
- Grant **Automation → System Events + iTerm2** when macOS prompts.

**Clicking a toast/row doesn't jump** → grant **Automation → iTerm2**.

**Check the raw state anytime:**
```bash
./cli/claude-inbox --watch
```
