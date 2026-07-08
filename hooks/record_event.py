#!/usr/bin/env python3
"""Claude Code hook entry point.

Translates one fired hook into a domain Event and runs it through the engine.
All behavior lives in the `claudewatch` package (domain/ports/adapters/engine/
interpreter); this file is just the imperative shell: build the pieces, adapt the
payload, step once, exit.

    record_event.py notification   # Notification+permission_prompt: blocked on you
    record_event.py idle           # Notification+idle_prompt: done, waiting
    record_event.py posttooluse    # a tool ran (you answered) -> clear a needs_input row
    record_event.py prompt         # you submitted a prompt -> working again
    record_event.py session_end    # session closed -> clear the row

The hook payload arrives as JSON on stdin; ITERM_SESSION_ID is inherited from env.
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from claudewatch.adapters import hook_event_adapter  # noqa: E402
from claudewatch.adapters.focus import is_focused_on  # noqa: E402
from claudewatch.adapters.mac_toaster import MacToaster  # noqa: E402
from claudewatch.adapters.settings_file import load_settings  # noqa: E402
from claudewatch.adapters.sqlite_store import SqliteStore  # noqa: E402
from claudewatch.engine import Engine  # noqa: E402
from claudewatch.interpreter import Interpreter  # noqa: E402

DB_PATH = os.path.join(ROOT, "inbox.db")


def main():
    kind = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        payload = {}

    event = hook_event_adapter.to_event(kind, payload, os.environ)
    if event is None:
        return  # unknown / ignored kind (e.g. a stale `stop` hook)

    engine = Engine(
        SqliteStore(DB_PATH),
        Interpreter(load_settings(), MacToaster(), is_focused_on),
    )
    engine.step(event)


if __name__ == "__main__":
    main()
