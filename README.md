# ClaudeWatch

A menu-bar + notification triage console for your **parallel Claude Code sessions** on macOS.

When you run several Claude Code sessions at once, you lose track of which ones are
blocked waiting on you and which have finished. ClaudeWatch watches them all and:

- 🔔 **Notifies you** when a session needs input or finishes — as a toast that appears
  on **the screen you're actually looking at** (not stuck on the main display), and
  **only for sessions you're not currently viewing** (focus-aware).
- 📋 Shows an always-visible **menu-bar badge** with the count of sessions needing you;
  click it to open the inbox panel.
- ⌨️ **Keyboard-driven**: one hotkey opens the inbox panel on your active screen, one
  jumps to the session a notification is about, one cycles through waiting sessions.
- 🖱️ **Click a notification or list row** to teleport to that exact iTerm2 tab.
- 🧹 **Self-heals** — closed tabs and stale sessions drop off automatically.

Built for **iTerm2**. Native menu-bar app + toast are PyObjC; hotkeys via `skhd`.

## How it works

```
Claude Code hooks  ──►  record_event.py  ──►  inbox.db (SQLite)  ──►  menu-bar app (badge + panel)
 Notification/Stop/       classify state,        one row per            toast popup (active screen)
 UserPromptSubmit/        capture iTerm2 tab      session that           CLI (claude-inbox)
 SessionEnd               id, decide notify      needs attention        hotkeys (skhd)
```

Everything is decoupled through the SQLite store: hooks write it; the menu-bar app,
toast, panel, CLI, and hotkeys are all just views/actions over it.

## Components

| File | Role |
|------|------|
| `hooks/record_event.py` | Hook target: classify a session event → upsert the store |
| `hooks/notify.py` | Focus-aware, two-tier notification decision → fires the toast |
| `hooks/toast.py` | Floating notification on the active screen (PyObjC), click-to-jump |
| `hooks/menubar_app.py` | Native menu-bar badge (PyObjC `NSStatusItem`); click → panel |
| `hooks/panel.py` | Inbox panel on the active screen (↑/↓ + Enter to jump, Esc to close) |
| `hooks/focus_session.py` | Deep-link: bring a session's iTerm2 tab to the front |
| `hooks/jump_to_oldest.py` | Hotkey: cycle through waiting sessions (round-robin) |
| `hooks/jump_to_last_notified.py` | Hotkey: jump to the session the current notification is about |
| `hooks/apply_config.py` | Regenerate the skhd hotkey bindings from `config.json` |
| `hooks/inbox_admin.py` | Maintenance actions (clear finished / clear all) |
| `cli/claude-inbox` | Terminal view of the inbox (`--watch` to live-refresh) |
| `config.json` | Hotkeys, notification toggles, sounds |

## Setup

Assumes the repo lives at `~/projects/claude-session-inbox` (paths are absolute).

**Dependencies**
```bash
brew install koekeishiya/formulae/skhd                 # global hotkey daemon
python3 -m venv .venv && .venv/bin/pip install pyobjc-framework-Cocoa   # menu bar + toast
```

**Claude Code hooks** — add to `~/.claude/settings.json` under `"hooks"`: `Notification`,
`Stop`, `UserPromptSubmit`, and `SessionEnd`, each running
`python3 ~/projects/claude-session-inbox/hooks/record_event.py <notification|stop|prompt|session_end>`.

**Menu-bar app** — run `hooks/menubar_app.py` under the venv python; install a LaunchAgent
(`~/Library/LaunchAgents`) with `RunAtLoad` + `KeepAlive` so it starts at login and stays up.

**Hotkeys** — `python3 hooks/apply_config.py` writes the bindings into `~/.skhdrc` and reloads
skhd. Grant **skhd** Accessibility permission (System Settings → Privacy & Security →
Accessibility).

**Permissions** — grant skhd + the menu-bar app access to control iTerm2 / System Events
when macOS prompts.

## Configuration (`config.json`)

| Key | Meaning |
|-----|---------|
| `hotkey` | cycle through waiting sessions |
| `panel_hotkey` | open the inbox panel on the active screen |
| `notify_hotkey` | jump to the session the current notification is about |
| `notify_on_needs_input` / `notify_on_done` | toggle each toast |
| `suppress_when_focused` | stay silent for the session you're viewing |
| `sound_needs_input` / `sound_done` | macOS sound name (e.g. `Ping`), or empty |

skhd combos use `modifier + modifier - key` (e.g. `alt - 0x32` for ⌥`). Change them from
the menu-bar app's Settings, or edit `config.json` and run `apply_config.py`.

## Status

Working: engine, native menu-bar badge, active-screen toasts (focus-aware), click-to-jump,
inbox panel, three configurable hotkeys, self-heal/expiry, launchd persistence.
Ideas: a themeable skin.
