#!/usr/bin/env python3
"""Claude Code hook target: record a session lifecycle event into the inbox store.

Invoked by Claude Code hooks with the event kind as argv[1]:
    record_event.py notification   # Notification+permission_prompt: blocked on you
    record_event.py idle           # Notification+idle_prompt: done, waiting for next prompt
    record_event.py posttooluse    # a tool ran (you answered) -> clear a needs_input row
    record_event.py prompt         # you submitted a prompt -> session is working again
    record_event.py session_end    # session closed -> clear the row

Hook payload (the event JSON) arrives on stdin. We pull identity from it, capture
the iTerm2 tab address from the inherited environment so a UI can later deep-link
back to the exact tab, and upsert one row per session into a SQLite store.

The store holds only sessions that warrant attention: a row exists while a session
is `needs_input` or `done`, and is deleted the moment you engage it.

Routing / notification policy:
  - `notification` (permission_prompt) -> needs_input, and ALWAYS notify. Each
    permission prompt is a distinct ask, so there's no transition-dedup; if Claude
    fires it, we fire. (notify.maybe_notify still stays silent for the session
    you're currently looking at -- that's focus-awareness, not dedup.)
  - `idle` (idle_prompt) -> done, notify only on a real transition, so a session
    sitting idle doesn't re-ping "done" over and over.
  - `posttooluse` -> you answered a permission/question and Claude ran a tool, so
    CLEAR the row -- but only if it's `needs_input`, so a tool call can never wipe
    a `done` reminder you haven't seen. (Known residual: a background subagent's
    PostToolUse carries the parent session_id and would also clear a genuinely
    pending needs_input; that's rare + low-harm -- the real prompt stays in the
    terminal and the next `notification` re-pings.)
  - `prompt` / `session_end` -> drop the row (you're engaging / it's gone).
  - `stop` -> ignored (fires at every turn boundary; not hooked, guard only).
"""

import json
import os
import sqlite3
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import notify  # noqa: E402  (sibling module in hooks/)

STORE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(STORE_DIR, "inbox.db")

IGNORED = {"stop"}  # fires every turn boundary; never mutate the inbox for it


def connect():
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    # WAL lets many short-lived hook processes write concurrently without locking
    # each other out -- several parallel sessions can fire hooks at the same instant.
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            session_id       TEXT PRIMARY KEY,
            project          TEXT,
            cwd              TEXT,
            iterm_session_id TEXT,
            state            TEXT,
            created_at       INTEGER,
            updated_at       INTEGER
        )
        """
    )
    return conn


def upsert_state(conn, session_id, project, cwd, iterm_session_id, state, now):
    conn.execute(
        """
        INSERT INTO sessions
            (session_id, project, cwd, iterm_session_id, state, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            project          = excluded.project,
            cwd              = excluded.cwd,
            iterm_session_id = excluded.iterm_session_id,
            state            = excluded.state,
            updated_at       = excluded.updated_at
        """,
        (session_id, project, cwd, iterm_session_id, state, now, now),
    )


def main():
    kind = sys.argv[1] if len(sys.argv) > 1 else ""

    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        payload = {}

    session_id = payload.get("session_id") or "unknown"
    cwd = payload.get("cwd") or os.getcwd()
    project = os.path.basename(cwd.rstrip("/")) or cwd
    # iTerm2 sets this for every session; the hook inherits it. It's how a UI
    # will later find and focus the exact tab this session lives in.
    iterm_session_id = os.environ.get("ITERM_SESSION_ID", "")
    now = int(time.time())

    if kind in IGNORED:
        return

    notify_state = None  # the state to announce, if any
    conn = connect()
    try:
        if kind == "notification":
            # Permission prompt: needs_input, and ALWAYS notify (no transition-dedup).
            upsert_state(conn, session_id, project, cwd, iterm_session_id, "needs_input", now)
            notify_state = "needs_input"
        elif kind == "idle":
            # Done/idle: notify only on a real transition into `done`.
            row = conn.execute(
                "SELECT state FROM sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
            if row is None or row[0] != "done":
                notify_state = "done"
            upsert_state(conn, session_id, project, cwd, iterm_session_id, "done", now)
        elif kind == "posttooluse":
            # You answered -> Claude ran a tool. Clear, but ONLY a needs_input row.
            conn.execute(
                "DELETE FROM sessions WHERE session_id = ? AND state = 'needs_input'",
                (session_id,),
            )
        else:
            # `prompt` / `session_end` (or anything unmapped): drop from the inbox.
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        conn.commit()
    finally:
        conn.close()

    if notify_state:
        notify.maybe_notify(notify_state, project, iterm_session_id)


if __name__ == "__main__":
    main()
