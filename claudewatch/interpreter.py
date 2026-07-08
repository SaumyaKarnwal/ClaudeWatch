"""Interpreter — the shell that performs effects. Owns Settings + the Toaster.

This is where the I/O that used to live inline in notify.py's `maybe_notify`
now lives. The pure core emits a `Notify` (intent); the interpreter applies the
user's toggles and focus-suppression, then delegates the actual toast to the
Toaster. Keeping this out of the core is what lets `handle` stay pure.
"""

from typing import Callable

from .domain.effect import Effect, Notify
from .ports.toaster import Toaster


class Interpreter:
    def __init__(self, settings, toaster: Toaster, is_focused_on: Callable[[str], bool]):
        self.settings = settings
        self.toaster = toaster
        # Injected so tests can fake "is the user looking at this tab?" without AppleScript.
        self.is_focused_on = is_focused_on

    def run(self, effect: Effect) -> None:
        if isinstance(effect, Notify):
            if not self.settings.enabled(effect.kind):
                return  # user turned this tier off
            if (
                self.settings.suppress_when_focused
                and effect.iterm_id
                and self.is_focused_on(effect.iterm_id)
            ):
                return  # you're already looking at it — a popup would be noise
            self.toaster.show(
                effect.kind, effect.project, effect.iterm_id, self.settings.sound_for(effect.kind)
            )
            return
        raise AssertionError("unhandled effect: %r" % (effect,))
