"""Session states + their transition rules (the State pattern).

Three states a session can be in. Each OWNS its response to every event in
`handle`, so the transition table lives with the states. `Absent` is a dataless
singleton (not in the inbox); `NeedsInput`/`DoneIdle` carry the row's display data
(`project`, `cwd`, `iterm_id`) so the store can persist a byte-identical row.

`label` is the bridge to the DB `state` column and drives persist-vs-delete:
None → not in the inbox → the store DELETEs the row; a string → the store upserts
it. So "clearing" is not special-cased anywhere — it is simply any transition
whose `next` is `Absent`.

The transition rules here reproduce the legacy `record_event.py` behavior exactly
(this is a refactor, not a behavior change). See `tests/test_session_state.py`,
which pins every (state, event) cell against that behavior.
"""

from typing import Optional

from .effect import Notify, NotifyKind
from .event import Done, Event, NeedInput, SessionEnded, ToolRan, UserTyped
from .transition import Transition


class SessionState:
    """Base for the closed state family. `label` is the persisted `state` value
    (None ⇒ not in the inbox). `handle` is a PURE (state, event) → Transition."""

    label = None  # type: Optional[str]

    def handle(self, event: Event) -> Transition:  # pragma: no cover - overridden
        raise NotImplementedError


class Absent(SessionState):
    """Not in the inbox — the session is working, or was never flagged. A dataless
    singleton: all instances are equal, and `ABSENT` is the shared one."""

    label = None  # type: Optional[str]

    def __eq__(self, other):
        return isinstance(other, Absent)

    def __hash__(self):
        return hash(Absent)

    def __repr__(self):
        return "Absent"

    def handle(self, event: Event) -> Transition:
        if isinstance(event, NeedInput):
            return Transition(
                NeedsInput(event.project, event.cwd, event.iterm_id),
                [Notify(NotifyKind.NEEDS_INPUT, event.project, event.iterm_id)],
            )
        if isinstance(event, Done):
            return Transition(
                DoneIdle(event.project, event.cwd, event.iterm_id),
                [Notify(NotifyKind.DONE, event.project, event.iterm_id)],
            )
        if isinstance(event, (ToolRan, UserTyped, SessionEnded)):
            return Transition(ABSENT)  # nothing to clear, nothing to announce
        raise AssertionError("unhandled event in Absent: %r" % (event,))


class _RowState(SessionState):
    """Shared plumbing for the two in-inbox states, which carry the row's display
    data. (Not part of the public state family — just avoids repeating fields.)"""

    def __init__(self, project: str, cwd: str, iterm_id: str):
        self.project = project
        self.cwd = cwd
        self.iterm_id = iterm_id

    def __eq__(self, other):
        return (
            type(self) is type(other)
            and self.project == other.project
            and self.cwd == other.cwd
            and self.iterm_id == other.iterm_id
        )

    def __hash__(self):
        return hash((type(self), self.project, self.cwd, self.iterm_id))

    def __repr__(self):
        return "%s(project=%r, iterm_id=%r)" % (type(self).__name__, self.project, self.iterm_id)


class NeedsInput(_RowState):
    """Blocked on the user (a permission prompt / question). The red state."""

    label = "needs_input"  # type: Optional[str]

    def handle(self, event: Event) -> Transition:
        if isinstance(event, NeedInput):
            # Re-ping on every new permission prompt — each is a distinct ask.
            return Transition(
                NeedsInput(event.project, event.cwd, event.iterm_id),
                [Notify(NotifyKind.NEEDS_INPUT, event.project, event.iterm_id)],
            )
        if isinstance(event, Done):
            return Transition(
                DoneIdle(event.project, event.cwd, event.iterm_id),
                [Notify(NotifyKind.DONE, event.project, event.iterm_id)],
            )
        if isinstance(event, (ToolRan, UserTyped, SessionEnded)):
            # You answered / engaged / it ended → leave the inbox (row deleted).
            return Transition(ABSENT)
        raise AssertionError("unhandled event in NeedsInput: %r" % (event,))


class DoneIdle(_RowState):
    """Finished, waiting for your next prompt. The green state."""

    label = "done"  # type: Optional[str]

    def handle(self, event: Event) -> Transition:
        if isinstance(event, NeedInput):
            return Transition(
                NeedsInput(event.project, event.cwd, event.iterm_id),
                [Notify(NotifyKind.NEEDS_INPUT, event.project, event.iterm_id)],
            )
        if isinstance(event, Done):
            # Repeated idle: stay done, don't re-announce. Still persisted (the
            # legacy idle branch upserts unconditionally, refreshing updated_at).
            return Transition(DoneIdle(event.project, event.cwd, event.iterm_id))
        if isinstance(event, ToolRan):
            # A tool ran while already done → ignore it completely. persist=False so
            # an unrelated (e.g. subagent) tool run never touches an unseen "done"
            # reminder or its updated_at. Matches the legacy `AND state='needs_input'`
            # guard on the PostToolUse delete.
            return Transition(self, persist=False)
        if isinstance(event, (UserTyped, SessionEnded)):
            return Transition(ABSENT)
        raise AssertionError("unhandled event in DoneIdle: %r" % (event,))


# The single Absent instance (like Kotlin's `data object`). Used everywhere.
ABSENT = Absent()
