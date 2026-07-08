"""Transition — the pure result of a decision: where the session goes next, what
the shell must do, and whether the store should be touched at all."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class Transition:
    """Returned by `SessionState.handle`.

    - `next`    — the state to persist / land in.
    - `effects` — inert effects for the interpreter to perform (usually a `Notify`).
    - `persist` — whether this transition changes the stored record. Almost always
      True. It is False for exactly one case: a tool completing while a session is
      already `done`. The legacy behavior there is to touch nothing — not the row,
      not its `updated_at` (which drives inbox ordering + TTL expiry) — so an
      unrelated (e.g. subagent) tool run cannot refresh a `done` reminder you
      haven't seen. Modeling it as `persist=False` keeps `save` a dumb
      persist-the-next-state operation everywhere else.
    """

    next: "SessionState"  # noqa: F821  (string annotation avoids an import cycle)
    effects: List[Effect] = field(default_factory=list)  # noqa: F821
    persist: bool = True
