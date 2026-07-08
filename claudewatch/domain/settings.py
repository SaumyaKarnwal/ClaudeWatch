"""Settings — the config as a value object, not a loose dict.

`config.json` is parsed once at the edge (adapters/settings_file.py) into this
immutable object, and everything downstream asks it questions (`enabled(kind)`,
`sound_for(kind)`) instead of reading raw string keys. The flat on-disk keys stay
human-friendly; the mapping to `NotifyKind` lives here.

Defaults mirror the legacy `notify.py` DEFAULTS exactly.
"""

from dataclasses import dataclass
from typing import Optional

from .effect import NotifyKind


@dataclass(frozen=True)
class Settings:
    notify_needs_input: bool = True
    notify_done: bool = True
    suppress_when_focused: bool = True
    sound_needs_input: str = "Ping"
    sound_done: str = ""

    @classmethod
    def from_config(cls, cfg: dict) -> "Settings":
        """Build from a parsed config.json dict; missing keys fall back to defaults."""
        return cls(
            notify_needs_input=cfg.get("notify_on_needs_input", True),
            notify_done=cfg.get("notify_on_done", True),
            suppress_when_focused=cfg.get("suppress_when_focused", True),
            sound_needs_input=cfg.get("sound_needs_input", "Ping"),
            sound_done=cfg.get("sound_done", ""),
        )

    def enabled(self, kind: NotifyKind) -> bool:
        return self.notify_needs_input if kind is NotifyKind.NEEDS_INPUT else self.notify_done

    def sound_for(self, kind: NotifyKind) -> Optional[str]:
        """The system sound name for this tier, or None if silent."""
        name = self.sound_needs_input if kind is NotifyKind.NEEDS_INPUT else self.sound_done
        return name or None
