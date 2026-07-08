"""Toaster port — the thing that actually shows an alert on screen.

Kept abstract so the interpreter can drive a real macOS toast in production and a
recording fake in tests. `sound` is the resolved system-sound name (or None);
the interpreter has already applied the enable/focus gating before calling this.
"""

from abc import ABC, abstractmethod
from typing import Optional

from ..domain.effect import NotifyKind


class Toaster(ABC):
    @abstractmethod
    def show(self, kind: NotifyKind, project: str, iterm_id: str, sound: Optional[str]) -> None:
        """Display the notification for `project`/`iterm_id` at the given tier."""
