"""Events — the typed vocabulary of "something happened to a session".

Each event is an immutable value object. They form a closed family (all defined
here, in one file, on purpose — that's what makes the set legible and lets the
per-state handlers stay exhaustive). The two "notifier" events (NeedInput / Done)
carry the row's display data; the "clearer" events need only identity.

Runtime is Python 3.9 (hooks run under /usr/bin/python3), so no `match`/`|`
unions — dispatch is done with isinstance in the state handlers.
"""

from dataclasses import dataclass


class Event:
    """Base marker for the closed event family. `session_id` identifies the row."""

    session_id: str


@dataclass(frozen=True)
class NeedInput(Event):
    """A permission prompt / question is blocking on the user (from `Notification`
    + permission_prompt). Carries the data needed to render + deep-link a toast."""

    session_id: str
    project: str
    cwd: str
    iterm_id: str


@dataclass(frozen=True)
class Done(Event):
    """The session went truly idle — finished, waiting for the next prompt (from
    `Notification` + idle_prompt)."""

    session_id: str
    project: str
    cwd: str
    iterm_id: str


@dataclass(frozen=True)
class ToolRan(Event):
    """A tool finished (from `PostToolUse`) — the universal "you answered" signal
    (a granted permission's tool ran, or an AskUserQuestion completed)."""

    session_id: str


@dataclass(frozen=True)
class UserTyped(Event):
    """You submitted a prompt (from `UserPromptSubmit`) — engaging the session."""

    session_id: str


@dataclass(frozen=True)
class SessionEnded(Event):
    """The session closed (from `SessionEnd`)."""

    session_id: str
