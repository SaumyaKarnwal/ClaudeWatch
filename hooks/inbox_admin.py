#!/usr/bin/env python3
"""Small maintenance actions on the inbox store, invoked from the menu bar.

    inbox_admin.py clear-finished   # remove all `done` rows
    inbox_admin.py clear-all        # empty the inbox
"""

import os
import sqlite3
import sys

DB_PATH = os.path.expanduser("~/projects/claude-session-inbox/inbox.db")

ACTIONS = {
    "clear-finished": "DELETE FROM sessions WHERE state = 'done'",
    "clear-all": "DELETE FROM sessions",
}


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    sql = ACTIONS.get(action)
    if not sql:
        print(f"unknown action: {action!r}; valid: {', '.join(ACTIONS)}", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(DB_PATH):
        return
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    try:
        conn.execute(sql)
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
