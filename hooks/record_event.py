#!/usr/bin/env python3
"""Claude Code hook target: record a session lifecycle event into the inbox store.

Invoked by Claude Code hooks with the event kind as argv[1]:
    record_event.py notification   # Claude is blocked, waiting on the user
    record_event.py stop           # Claude finished its turn / is idle
    record_event.py prompt         # user submitted a new prompt -> session is working again

Hook payload (the event JSON) arrives on stdin. We pull identity from it, capture
the iTerm2 tab address from the inherited environment so a UI can later deep-link
back to the exact tab, and upsert one row per session into a SQLite store.

The store holds only sessions that warrant attention: a row exists while a session
is `needs_input` or `done`, and is deleted the moment the user resumes it (prompt).
"""

import json
import os
import sqlite3
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import notify  # noqa: E402  (sibling module in hooks/)

STORE_DIR = os.path.expanduser("~/projects/claude-session-inbox")
DB_PATH = os.path.join(STORE_DIR, "inbox.db")

# Hook kind (argv[1]) -> the state a session enters. `prompt` has no state: it
# clears the row, because a session the user just replied to needs nothing.
KIND_TO_STATE = {
    "notification": "needs_input",
    "stop": "done",
}


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

    conn = connect()
    try:
        if kind not in KIND_TO_STATE:
            # `prompt` (or anything unmapped): the user is engaging this session,
            # so it no longer needs attention -- drop it from the inbox.
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        else:
            state = KIND_TO_STATE[kind]
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
        conn.commit()
    finally:
        conn.close()

    # Alert after the store is consistent. `prompt` clears a row -> nothing to announce.
    if kind in KIND_TO_STATE:
        notify.maybe_notify(KIND_TO_STATE[kind], project, iterm_session_id)


if __name__ == "__main__":
    main()
