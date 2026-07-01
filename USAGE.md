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

## Configuring — `config.json`

All settings live in one file: **`config.json`** (repo root). Two kinds of settings,
and they take effect differently:

### Settings that apply immediately (no extra step)
Edit `config.json` and the next event uses the new value:

| Key | Meaning |
|---|---|
| `notify_on_needs_input` | `true`/`false` — toast when a session needs input |
| `notify_on_done` | `true`/`false` — toast when a session finishes |
| `suppress_when_focused` | `true` — stay silent for the session you're viewing |
| `sound_needs_input` | macOS sound name (e.g. `"Ping"`, `"Glass"`) or `""` for silent |
| `sound_done` | same, for the finished toast |

### Settings that need an "apply" step
The **shortcuts** are compiled into `~/.skhdrc`, so after changing them you must apply:

| Key | Meaning |
|---|---|
| `hotkey` | cycle waiting sessions |
| `panel_hotkey` | open the inbox panel |
| `notify_hotkey` | jump to the current notification's session |

**To change a shortcut:**
1. Edit its value in `config.json` (skhd syntax — see below).
2. Run `python3 hooks/apply_config.py` **— or** menu-bar ▸ Settings ▸ **Apply / reload**.

### skhd shortcut syntax
`modifier + modifier - key`, e.g.:
- `alt - 0x32` → ⌥`  (backtick is keycode `0x32`)
- `cmd + ctrl - n` → ⌘⌃N
- `alt - j` → ⌥J

Modifiers: `cmd`, `ctrl`, `alt` (Option), `shift`, `fn`. Use a letter, or `0x<keycode>`
for punctuation. Avoid combos macOS already owns (e.g. ⌘\` cycles windows).

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
