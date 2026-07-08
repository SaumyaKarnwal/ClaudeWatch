"""Hook event adapter — translates one fired Claude Code hook into a domain Event.

This is the inbound adapter (your "EventSource" rename): there is no stream to
poll — each hook fires one payload, so the job is pure translation. It is the ONLY
place raw payload/env keys become typed objects. `project` is derived from `cwd`
exactly as the legacy code did (basename, falling back to the raw cwd).

Returns None for an unrecognized / ignored kind (e.g. a stale `stop` hook), so the
entry point can simply do nothing.
"""

import os
from typing import Optional

from ..domain.event import Done, Event, NeedInput, SessionEnded, ToolRan, UserTyped


def to_event(kind: str, payload: dict, env: dict) -> Optional[Event]:
    session_id = payload.get("session_id") or "unknown"
    cwd = payload.get("cwd") or os.getcwd()
    project = os.path.basename(cwd.rstrip("/")) or cwd
    # iTerm2 sets this per session; the hook process inherits it. It's how the UI
    # later deep-links back to the exact tab.
    iterm_id = env.get("ITERM_SESSION_ID", "")

    if kind == "notification":
        return NeedInput(session_id, project, cwd, iterm_id)
    if kind == "idle":
        return Done(session_id, project, cwd, iterm_id)
    if kind == "posttooluse":
        return ToolRan(session_id)
    if kind == "prompt":
        return UserTyped(session_id)
    if kind == "session_end":
        return SessionEnded(session_id)
    return None  # unknown/ignored (e.g. a stale `stop` hook) → the caller no-ops
