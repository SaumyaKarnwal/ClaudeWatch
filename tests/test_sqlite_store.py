"""SqliteStore round-trips + the byte-faithful upsert semantics (created_at kept,
updated_at bumped, delete on Absent). Uses a throwaway DB file."""

import os
import sqlite3
import tempfile
import unittest

from claudewatch.adapters.sqlite_store import SqliteStore
from claudewatch.domain.session_state import ABSENT, DoneIdle, NeedsInput


class SqliteStoreTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.db = os.path.join(self.dir, "inbox.db")
        self.store = SqliteStore(self.db)

    def tearDown(self):
        for name in os.listdir(self.dir):
            os.remove(os.path.join(self.dir, name))
        os.rmdir(self.dir)

    def _row(self, session_id):
        conn = sqlite3.connect(self.db)
        try:
            return conn.execute(
                "SELECT project, cwd, iterm_session_id, state, created_at, updated_at "
                "FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        finally:
            conn.close()

    def test_load_absent_when_no_row(self):
        self.assertEqual(self.store.load("nope"), ABSENT)

    def test_save_and_load_needs_input_roundtrip(self):
        self.store.save("s1", NeedsInput("proj", "/cwd", "iterm"))
        self.assertEqual(self.store.load("s1"), NeedsInput("proj", "/cwd", "iterm"))

    def test_save_absent_deletes_row(self):
        self.store.save("s1", NeedsInput("proj", "/cwd", "iterm"))
        self.store.save("s1", ABSENT)
        self.assertIsNone(self._row("s1"))
        self.assertEqual(self.store.load("s1"), ABSENT)

    def test_upsert_preserves_created_at_and_bumps_updated_at(self):
        # Seed a row with an old created_at/updated_at, then upsert a new state.
        conn = sqlite3.connect(self.db)
        conn.execute(self._schema())
        conn.execute(
            "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("s1", "old", "/old", "iterm", "needs_input", 1000, 1000),
        )
        conn.commit()
        conn.close()

        self.store.save("s1", DoneIdle("new", "/new", "iterm"))

        project, cwd, iterm, state, created_at, updated_at = self._row("s1")
        self.assertEqual((project, cwd, iterm, state), ("new", "/new", "iterm", "done"))
        self.assertEqual(created_at, 1000)      # preserved across the conflict
        self.assertGreater(updated_at, 1000)    # bumped to "now"

    def test_load_unknown_label_is_absent(self):
        conn = sqlite3.connect(self.db)
        conn.execute(self._schema())
        conn.execute(
            "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("s1", "p", "/c", "i", "weird", 1, 1),
        )
        conn.commit()
        conn.close()
        self.assertEqual(self.store.load("s1"), ABSENT)

    @staticmethod
    def _schema():
        return (
            "CREATE TABLE IF NOT EXISTS sessions (session_id TEXT PRIMARY KEY, project TEXT, "
            "cwd TEXT, iterm_session_id TEXT, state TEXT, created_at INTEGER, updated_at INTEGER)"
        )


if __name__ == "__main__":
    unittest.main()
