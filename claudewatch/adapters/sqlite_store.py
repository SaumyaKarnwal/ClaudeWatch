"""SQLite implementation of the Store port.

Schema, PRAGMA, and the upsert SQL are copied verbatim from the legacy
record_event.py so existing rows and every reader (menubar / panel / jump
scripts) keep working unchanged. WAL lets the many short-lived hook processes
write without locking each other out.

`save` maps a state back to a row: `label is None` (Absent) → DELETE; otherwise
INSERT … ON CONFLICT UPDATE, which (like the legacy code) refreshes
project/cwd/iterm/state + `updated_at` but preserves `created_at`.
"""

import sqlite3
import time

from ..domain.session_state import ABSENT, DoneIdle, NeedsInput, SessionState

_SCHEMA = """
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

_UPSERT = """
INSERT INTO sessions
    (session_id, project, cwd, iterm_session_id, state, created_at, updated_at)
VALUES (?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(session_id) DO UPDATE SET
    project          = excluded.project,
    cwd              = excluded.cwd,
    iterm_session_id = excluded.iterm_session_id,
    state            = excluded.state,
    updated_at       = excluded.updated_at
"""


class SqliteStore:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _connect(self):
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(_SCHEMA)
        return conn

    def load(self, session_id: str) -> SessionState:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT project, cwd, iterm_session_id, state FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return ABSENT
        project, cwd, iterm_id, state = row
        if state == "needs_input":
            return NeedsInput(project, cwd, iterm_id)
        if state == "done":
            return DoneIdle(project, cwd, iterm_id)
        return ABSENT  # unknown label → treat as not-in-inbox (defensive)

    def save(self, session_id: str, state: SessionState) -> None:
        conn = self._connect()
        now = int(time.time())
        try:
            if state.label is None:
                conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            else:
                conn.execute(
                    _UPSERT,
                    (session_id, state.project, state.cwd, state.iterm_id, state.label, now, now),
                )
            conn.commit()
        finally:
            conn.close()
