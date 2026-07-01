# ClaudeWatch

### Never lose track of a Claude Code session again.

You kick off three or four Claude Code sessions to work in parallel — then lose track of
which ones are waiting on you and which have finished. **ClaudeWatch watches them all**
and, the moment one needs you, tells you *on the screen you're actually looking at* and
lets you jump straight to it.

macOS · iTerm2 · 100% local — **nothing ever leaves your machine.**

---

## What it is

A tiny menu-bar companion for Claude Code. It sits in your menu bar showing how many
sessions need you, pops a small notification when something changes, and gives you
keyboard shortcuts to hop between sessions — so running many at once stops being chaos.

No cloud account. No background server. No Electron. Just a few small local scripts.

---

## What it does

**A live badge in your menu bar** — glance up, know instantly:

```
  🔔 2   ← two sessions are waiting on you
  ✓ 1   ← one finished, nothing blocking
  🌙     ← all clear
```

**A notification when a background session changes** — on the screen you're using, not
buried on another monitor, and never for the session you're already looking at:

```
  ┌──────────────────────────────────────┐
  │  🔴  Needs your input                  │
  │      deca-backend                      │   ← click it → jump to that tab
  └──────────────────────────────────────┘
```

**A keyboard-openable inbox** of everything that needs you:

```
  Claude Sessions
  ● deca-backend        4m        ✕
  ● console             1m        ✕
  ✓ library-refactor   12m        ✕
     ↑/↓ select · ⏎ jump · x dismiss · esc close
```

- 🖱️ **Click** a notification or a row → jump to that exact iTerm2 tab.
- ⌨️ **Shortcuts** to open the inbox, jump to the latest notification, or cycle sessions.
- 🧹 **Self-healing** — closed tabs and stale sessions drop off on their own.

---

## 🔒 Permissions & privacy — exactly what, and why

This is the honest, complete list. macOS will ask for **two** things:

| Permission | Granted to | Why | If denied |
|---|---|---|---|
| **Accessibility** | `skhd` | detect your keyboard shortcuts | shortcuts won't fire |
| **Automation → iTerm2** | ClaudeWatch | find + focus the right session tab | can't jump to sessions |
| **Automation → System Events** | ClaudeWatch | know which app/tab is frontmost, so it stays quiet about the session you're already viewing | you'd get pinged about the session you're looking at |

**What it deliberately does NOT ask for — and never will:**

- ❌ **No Notifications permission** — the popup is ClaudeWatch's own little window, not a
  system notification, so there's nothing to approve.
- ❌ **No Screen Recording** — it can't and doesn't read your screen. *(In fact, that's why
  this README has no screenshots — capturing the window cleanly would require Screen
  Recording, and we'd rather not have it.)*
- ❌ **No Full Disk Access, Camera, Microphone, Contacts, or Location.**
- ❌ **No network access.** State lives in one local SQLite file. Nothing is uploaded,
  nothing phones home, there is zero telemetry.

The whole footprint is: *listen for my hotkeys* + *talk to iTerm2 & System Events.* It's
~10 short Python files — read every line.

---

## Install

```bash
git clone https://github.com/SaumyaKarnwal/ClaudeWatch.git ~/ClaudeWatch
cd ~/ClaudeWatch
./install.sh
```

`install.sh` is **idempotent** (safe to re-run) and works from wherever you cloned it. It
installs `skhd` + a local Python env, adds ClaudeWatch's hooks to `~/.claude/settings.json`
(**merging** — it never overwrites your existing settings, and saves a backup), binds the
shortcuts, and installs the menu-bar app as a login item.

**Then grant the two permissions above** (the installer prints them and opens the right
Settings pane). That's it — the badge is live.

Prerequisites: macOS, iTerm2, Homebrew, Python 3.

---

## Using it efficiently

The workflow it's built for:

1. **Fire off several Claude Code sessions** in different iTerm2 tabs and get to work.
2. **Glance at the badge** now and then — the count tells you how many need you.
3. When a background session needs input, a **notification pops on your screen** → click
   it to jump right there, answer, and get back to what you were doing.
4. Prefer the keyboard? Hit **⌥`** to open the inbox on your active screen, use `↑/↓` and
   `⏎` to jump, or `x` to dismiss ones you don't care about.
5. Sessions clear themselves as you answer them — the badge always reflects reality.

**Default shortcuts** (all remappable — see Settings):

| Shortcut | Action |
|---|---|
| `⌥\`` | open the inbox on your active screen |
| `⌘⌃N` | jump to the session the last notification was about |
| `⌃\`` | cycle through waiting sessions |

**Tips**
- Turn off the "finished" notification if batch runs get chatty (Settings → uncheck it) —
  keep only "needs input" for true interruptions.
- "Stay silent for the session I'm viewing" is on by default, so you're only pinged about
  sessions you *aren't* looking at.

---

## Settings — no config files needed

**Right-click the menu-bar badge → "Edit Settings…"** opens a small window:

```
  Keyboard shortcuts
  Open inbox            ⌥`      [ Record ]
  Go to notification    ⌘⌃N     [ Record ]
  Cycle sessions        ⌃`      [ Record ]

  Notifications
  ☑ Notify when a session needs input
  ☑ Notify when a session finishes
  ☑ Stay silent for the session I'm viewing
  Needs-input sound   [ Ping  ▾ ]
  Finished sound      [ None  ▾ ]
```

- **Record a shortcut**: click *Record*, press the combo. If you pick something macOS
  already owns (like ⌘\`), a red ⚠ warning appears and nothing is saved — just try another.
- **Toggles and sounds** save instantly.

*(Everything is stored in `config.json` if you'd rather edit by hand — see [USAGE.md](USAGE.md).)*

---

## Full guide

📖 **[USAGE.md](USAGE.md)** — every shortcut, the panel keys, all settings, and troubleshooting.

---

## Uninstall

```bash
./uninstall.sh
```
Stops the menu-bar app and removes ClaudeWatch's hooks + shortcuts, keeping your other
settings. Shared tools (`skhd`, iTerm2) stay installed. Delete the folder to remove the rest.

---

## How it works

```
Claude Code hooks  ──►  record_event.py  ──►  inbox.db (SQLite)  ──►  menu-bar app (badge + panel)
 Notification/Stop/       classify state,        one row per            notification (active screen)
 UserPromptSubmit/        capture iTerm2 tab      session needing        CLI (cli/claude-inbox)
 SessionEnd               id, decide notify      attention              hotkeys (skhd)
```

Everything is decoupled through the local SQLite store: hooks write it; the badge,
notification, panel, CLI, and shortcuts are all just views over it.

---

macOS · iTerm2 · Homebrew · Python 3 · two permissions (Accessibility + Automation) · no
network, no cloud, no telemetry.
