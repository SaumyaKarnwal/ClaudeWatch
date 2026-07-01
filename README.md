# ClaudeWatch

**Never lose track of a parallel Claude Code session again.** ClaudeWatch watches all
your running Claude Code sessions and tells you — on the screen you're actually looking
at — the moment one needs your input or finishes, and lets you jump straight to it.

Built for **macOS + iTerm2**. Everything runs locally; **nothing leaves your machine**.

📖 **Already installed? See [USAGE.md](USAGE.md)** for how to use it, all the shortcuts,
and how to change settings.

---

## What it does

- 🔔 **Toast notification** when a session needs input or finishes — appears on the
  screen you're using (not stuck on your main display), and **only for sessions you're
  not currently looking at**.
- 📋 **Always-visible menu-bar badge** with a count of sessions needing you; click it to
  open the inbox.
- ⌨️ **Keyboard-driven**: open the inbox, jump to the session a notification is about, or
  cycle through waiting sessions — all configurable shortcuts.
- 🖱️ **Click a toast or a row** → jump to that exact iTerm2 tab.
- 🧹 **Self-healing** — closed tabs and stale sessions drop off automatically.

---

## What it needs (and nothing more)

| Dependency | Why | Installed by `install.sh`? |
|---|---|---|
| **iTerm2** | ClaudeWatch finds and focuses your session tabs | you install it |
| **Homebrew** | to install `skhd` | you install it ([brew.sh](https://brew.sh)) |
| **skhd** | listens for your keyboard shortcuts | ✅ yes |
| **PyObjC** (in a local venv) | draws the menu-bar badge, toast, and inbox panel | ✅ yes |
| **Python 3** | runs the hooks and scripts | built into macOS |

That's the whole list. No Electron, no background server, no cloud account.

---

## 🔒 Permissions — exactly what, and exactly why

macOS will ask you to grant **two** things. Here's every one, why it's needed, and what
happens without it:

| Permission | Granted to | Why | Without it |
|---|---|---|---|
| **Accessibility** | `skhd` | Detect your keyboard shortcuts system-wide | shortcuts don't fire |
| **Automation → iTerm2** | ClaudeWatch | Find which tab a session is in and bring it to the front | can't jump to sessions |
| **Automation → System Events** | ClaudeWatch | See which app/tab is frontmost, so it stays quiet about the session you're already viewing | you'd get notified about the session you're looking at |

**What it deliberately does *not* request:**

- ❌ **No Notification permission** — the toast is ClaudeWatch's own small window, not a
  system notification, so there's nothing to approve.
- ❌ **No Screen Recording, Full Disk Access, Camera, Microphone, Contacts, or Location.**
- ❌ **No network access.** State lives in a local SQLite file. Nothing phones home,
  nothing is uploaded, there is no telemetry.

The entire footprint is: *listen for my hotkeys* + *talk to iTerm2 and System Events*.
You can read every line — it's ~10 short Python files.

---

## Install

```bash
git clone https://github.com/SaumyaKarnwal/ClaudeWatch.git ~/ClaudeWatch
cd ~/ClaudeWatch
./install.sh
```

`install.sh` is **idempotent** (safe to re-run) and works from wherever you cloned it.
It will:
1. Install `skhd` and a local Python venv with PyObjC.
2. Add ClaudeWatch's hooks to `~/.claude/settings.json` — **merging**, never overwriting
   your existing settings (a timestamped backup is saved).
3. Bind the keyboard shortcuts and start `skhd`.
4. Install the menu-bar app as a login agent (starts at login, restarts if it crashes).
5. Print the two permissions to grant and open the right Settings pane.

**Then grant the two permissions** (see the table above). That's it — the menu-bar badge
is live and you're done.

---

## Using it

- **Menu-bar badge** — shows the count of sessions needing you. Click to open the inbox
  panel; right-click for Clear Finished / Settings / Quit.
- **Toast** — pops on your active screen when a background session needs input (red) or
  finishes (green). Click it to jump to that tab.
- **Shortcuts** (defaults; change them in the menu-bar ▸ Settings, or `config.json`):
  | Shortcut | Action |
  |---|---|
  | `⌥\`` | open the inbox panel on your active screen |
  | `⌘⌃N` | jump to the session the current notification is about |
  | `⌃\`` | cycle through waiting sessions |
- **In the panel**: `↑`/`↓` to select, `Enter` to jump, `x` to dismiss a session, `Esc` to close.

### Configuration (`config.json`)
| Key | Meaning |
|---|---|
| `hotkey` / `panel_hotkey` / `notify_hotkey` | the three shortcuts (skhd syntax, e.g. `alt - 0x32` = ⌥`) |
| `notify_on_needs_input` / `notify_on_done` | toggle each toast |
| `suppress_when_focused` | stay silent for the session you're viewing |
| `sound_needs_input` / `sound_done` | macOS sound name (e.g. `Ping`), or empty |

After editing `config.json`, run `python3 hooks/apply_config.py` (or use the menu's
"Apply / reload").

---

## Uninstall

```bash
./uninstall.sh
```
Stops the menu-bar app, removes ClaudeWatch's hooks from `settings.json` (keeping your
other settings), and removes its skhd bindings. Shared tools (`skhd`, iTerm2) are left
installed. Delete the cloned folder to remove the rest.

---

## How it works

```
Claude Code hooks  ──►  record_event.py  ──►  inbox.db (SQLite)  ──►  menu-bar app (badge + panel)
 Notification/Stop/       classify state,        one row per            toast (active screen)
 UserPromptSubmit/        capture iTerm2 tab      session needing        CLI (cli/claude-inbox)
 SessionEnd               id, decide notify      attention              hotkeys (skhd)
```

Everything is decoupled through the SQLite store: hooks write it; the badge, toast,
panel, CLI, and shortcuts are all just views/actions over it.

---

## Requirements recap
macOS · iTerm2 · Homebrew · Python 3. Two permissions (Accessibility for skhd; Automation
for iTerm2 + System Events). No network, no cloud, no telemetry.
