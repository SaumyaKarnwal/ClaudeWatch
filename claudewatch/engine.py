"""Engine — the single, total entry point.

Every event goes through `step`, and `step` always does the whole sequence:
load → decide (pure) → persist → run effects. Nothing else calls `handle` or
holds a `Transition`, so effects can never be "forgotten" and state + notifications
can't drift apart. (Same order as the legacy code: commit the store, then notify.)
"""

from .domain.event import Event
from .interpreter import Interpreter
from .ports.store import Store


class Engine:
    def __init__(self, store: Store, interpreter: Interpreter):
        self.store = store
        self.interpreter = interpreter

    def step(self, event: Event) -> None:
        current = self.store.load(event.session_id)    # where were we?
        transition = current.handle(event)             # decide (pure)
        if transition.persist:                         # persist (upsert / delete),
            self.store.save(event.session_id, transition.next)  # unless the event is ignored
        for effect in transition.effects:              # act
            self.interpreter.run(effect)
