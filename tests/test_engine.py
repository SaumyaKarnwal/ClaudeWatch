"""Engine wiring: load -> decide -> persist (or skip) -> run effects, with fakes."""

import unittest

from claudewatch.domain.effect import Notify, NotifyKind
from claudewatch.domain.event import Done, NeedInput, ToolRan, UserTyped
from claudewatch.domain.session_state import ABSENT, DoneIdle, NeedsInput
from claudewatch.engine import Engine


class FakeStore:
    def __init__(self, initial=None):
        self._rows = dict(initial or {})
        self.saves = []  # (session_id, state) in call order

    def load(self, session_id):
        return self._rows.get(session_id, ABSENT)

    def save(self, session_id, state):
        self.saves.append((session_id, state))
        if state.label is None:
            self._rows.pop(session_id, None)
        else:
            self._rows[session_id] = state


class RecordingInterpreter:
    def __init__(self):
        self.effects = []

    def run(self, effect):
        self.effects.append(effect)


class EngineTest(unittest.TestCase):
    def _engine(self, initial=None):
        store = FakeStore(initial)
        interp = RecordingInterpreter()
        return Engine(store, interp), store, interp

    def test_needinput_from_absent_saves_and_notifies(self):
        engine, store, interp = self._engine()
        engine.step(NeedInput("s1", "proj", "/cwd", "iterm"))
        self.assertEqual(store._rows["s1"], NeedsInput("proj", "/cwd", "iterm"))
        self.assertEqual(interp.effects, [Notify(NotifyKind.NEEDS_INPUT, "proj", "iterm")])

    def test_tool_clears_needs_input_row(self):
        engine, store, interp = self._engine({"s1": NeedsInput("proj", "/cwd", "iterm")})
        engine.step(ToolRan("s1"))
        self.assertNotIn("s1", store._rows)             # row deleted
        self.assertEqual(store.saves[-1], ("s1", ABSENT))  # via save(Absent)
        self.assertEqual(interp.effects, [])            # no toast

    def test_tool_while_done_does_not_write_at_all(self):
        # The persist=False case: an unseen "done" reminder (and its updated_at)
        # must be untouched by a tool completing.
        engine, store, interp = self._engine({"s1": DoneIdle("proj", "/cwd", "iterm")})
        engine.step(ToolRan("s1"))
        self.assertEqual(store.saves, [])               # NO write happened
        self.assertEqual(store._rows["s1"], DoneIdle("proj", "/cwd", "iterm"))
        self.assertEqual(interp.effects, [])

    def test_repeat_idle_persists_but_stays_silent(self):
        # done+done still upserts (refreshes updated_at) but must not re-notify.
        engine, store, interp = self._engine({"s1": DoneIdle("old", "/old", "iterm")})
        engine.step(Done("s1", "new", "/new", "iterm"))
        self.assertEqual(store.saves[-1], ("s1", DoneIdle("new", "/new", "iterm")))  # a write
        self.assertEqual(interp.effects, [])            # but no notification

    def test_typed_clears_any_row(self):
        engine, store, interp = self._engine({"s1": DoneIdle("proj", "/cwd", "iterm")})
        engine.step(UserTyped("s1"))
        self.assertNotIn("s1", store._rows)
        self.assertEqual(interp.effects, [])


if __name__ == "__main__":
    unittest.main()
