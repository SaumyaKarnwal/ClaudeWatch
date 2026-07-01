# ClaudeWatch

A menu-bar + notification triage console for your **parallel Claude Code sessions** on macOS.

When you run several Claude Code sessions at once, you lose track of which ones are
blocked waiting on you and which have finished. ClaudeWatch watches them all and:

- 🔔 **Notifies you** when a session needs input or finishes — as a toast that appears
  on **the screen you're actually looking at** (not stuck on the main display), and
  **only for sessions you're not currently viewing** (focus-aware).
- 📋 Shows an always-visible **menu-bar inbox** of every session and its state.
- ⌨️ Lets you **jump between waiting sessions by keyboard** — one hotkey cycles you
  through them, oldest-first; another opens the full inbox panel on your active screen.
- 🖱️ **Click a notification or list row** to teleport to that exact iTerm2 tab.
- 🧹 **Self-heals** — closed tabs and stale sessions drop off automatically.

Built for **iTerm2**.

## How it works

```
Claude Code hooks  ──►  record_event.py  ──►  inbox.db (SQLite)  ──►  menu bar (SwiftBar)
 Notification/Stop/       classify state,        one row per            CLI (claude-inbox)
 UserPromptSubmit/        capture iTerm2 tab      session that           toast popup (active screen)
 SessionEnd               id, decide notify      needs attention        ⌃`  jump hotkey (skhd)
```

Everything is decoupled through the SQLite store: hooks write it; the menu bar,
notifications, CLI, and hotkeys are all just views/actions over it.

## Components

| File | Role |
|------|------|
| `hooks/record_event.py` | Hook target: classify a session event → upsert the store |
| `hooks/notify.py` | Focus-aware, two-tier notification decision → fires the toast |
| `hooks/toast.py` | Floating notification on the active screen (PyObjC), click-to-jump |
| `hooks/focus_session.py` | Deep-link: bring a session's iTerm2 tab to the front |
| `hooks/jump_to_oldest.py` | Hotkey action: jump to / cycle waiting sessions |
| `hooks/panel.py` | Keyboard-openable inbox panel on the active screen |
| `hooks/apply_config.py` | Regenerate the skhd hotkey binding from `config.json` |
| `hooks/inbox_admin.py` | Menu maintenance actions (clear finished / clear all) |
| `menubar/claude_inbox.3s.py` | SwiftBar plugin: the menu-bar inbox |
| `cli/claude-inbox` | Terminal view of the inbox (`--watch` to live-refresh) |
| `config.json` | Hotkeys, notification toggles, sounds |

## Setup

Assumes the repo lives at `~/projects/claude-session-inbox` (paths are absolute).

**Dependencies**
```bash
brew install --cask swiftbar               # menu-bar host
brew install koekeishiya/formulae/skhd     # global hotkey daemon
python3 -m venv .venv && .venv/bin/pip install pyobjc-framework-Cocoa   # for the toast
```

**Claude Code hooks** — add to `~/.claude/settings.json` under `"hooks"`: `Notification`,
`Stop`, `UserPromptSubmit`, and `SessionEnd`, each running
`python3 ~/projects/claude-session-inbox/hooks/record_event.py <notification|stop|prompt|session_end>`.

**Menu bar** — point SwiftBar at `menubar/` and launch it:
```bash
defaults write com.ameba.SwiftBar PluginDirectory "$HOME/projects/claude-session-inbox/menubar"
open -a SwiftBar
```

**Hotkey** — `python3 hooks/apply_config.py` writes the binding into `~/.skhdrc` and reloads
skhd. Grant **skhd** Accessibility permission (System Settings → Privacy & Security →
Accessibility). Default jump hotkey: **⌃`**.

**Permissions** — grant SwiftBar and skhd access to control iTerm2 / System Events when
macOS prompts.

## Configuration (`config.json`)

| Key | Meaning |
|-----|---------|
| `hotkey` | skhd combo for "jump to next waiting session" |
| `notify_on_needs_input` / `notify_on_done` | toggle each toast |
| `suppress_when_focused` | stay silent for the session you're viewing |
| `sound_needs_input` / `sound_done` | macOS sound name (e.g. `Ping`), or empty |

## Status

Working: engine, menu bar, focus-aware active-screen toasts, click-to-jump, jump hotkey,
self-heal/expiry. In progress: inbox-panel hotkey binding, a themeable skin.
