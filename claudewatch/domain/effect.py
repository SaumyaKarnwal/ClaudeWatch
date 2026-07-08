"""Effects — inert "to-do notes" the pure core emits. They *describe* work; the
interpreter (imperative shell) *performs* it.

There is exactly one effect today: `Notify`. Deliberately NOT effects:
  - clearing the inbox row  → that's just the next state being `Absent`, enacted
    by the store's `save` (a DELETE). The state is the single source of truth for
    in-inbox-or-not.
  - jumping to the iTerm tab → that fires when the user clicks the toast, a
    separate flow outside this machine.
  - playing a sound         → part of *performing* a Notify (the interpreter picks
    the sound from kind + settings), not its own effect.

`Notify` carries a `kind` rather than being split into two subclasses: the
interpreter does the *same work* (show a toast) with *different styling data*.
"""

from dataclasses import dataclass
from enum import Enum


class NotifyKind(Enum):
    """The tier of a notification — a label, so an enum, not a sealed class."""

    NEEDS_INPUT = "needs_input"  # urgent: red + sound
    DONE = "done"                # gentle FYI: green


class Effect:
    """Base marker for the closed effect family (kept open to grow: a future
    Slack/log effect would force the interpreter's dispatch to handle it)."""


@dataclass(frozen=True)
class Notify(Effect):
    """Alert the user about a session. `project` + `iterm_id` are what the toast
    displays and deep-links to."""

    kind: NotifyKind
    project: str
    iterm_id: str
