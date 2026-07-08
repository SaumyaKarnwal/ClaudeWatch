"""Store port — persistence for one row per session.

The core depends on this abstraction, never on SQLite directly, so a test can
swap a fake. `save` deletes the row when `state.label is None` (Absent) and
upserts otherwise, reading the row data off the state object.
"""

from abc import ABC, abstractmethod

from ..domain.session_state import SessionState


class Store(ABC):
    @abstractmethod
    def load(self, session_id: str) -> SessionState:
        """Return the session's current state, or Absent if it has no row."""

    @abstractmethod
    def save(self, session_id: str, state: SessionState) -> None:
        """Persist the state: upsert its row, or DELETE when the state is Absent."""
