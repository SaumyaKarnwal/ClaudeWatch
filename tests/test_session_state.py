"""The full transition table — one assertion per (state, event) cell.

This IS the behavior spec, and the proof the refactor changed nothing: each row
below reproduces exactly what the legacy record_event.py did.

Legacy mapping being pinned:
  - notification (any state) -> upsert needs_input + always notify   -> next=NeedsInput, Notify, persist
  - idle from absent/needs   -> upsert done + notify                 -> next=DoneIdle, Notify, persist
  - idle while already done   -> upsert done, NO notify (dedup)       -> next=DoneIdle, no effect, persist
  - posttooluse while needs   -> delete the row                       -> next=Absent, persist
  - posttooluse while done    -> NO write at all (guarded delete)     -> next=DoneIdle(self), persist=False
  - posttooluse while absent  -> delete (0 rows)                      -> next=Absent, persist
  - prompt / session_end      -> delete                              -> next=Absent, persist
"""

import unittest

from claudewatch.domain.effect import Notify, NotifyKind
from claudewatch.domain.event import Done, NeedInput, SessionEnded, ToolRan, UserTyped
from claudewatch.domain.session_state import ABSENT, DoneIdle, NeedsInput
from claudewatch.domain.transition import Transition

# Event data distinct from the current-state data, so we can prove the *event's*
# meta (not the loaded row's) is what gets carried into the next state.
NEED = NeedInput("s1", "proj2", "/cwd2", "iterm2")
DONE = Done("s1", "proj2", "/cwd2", "iterm2")
TOOL = ToolRan("s1")
TYPED = UserTyped("s1")
ENDED = SessionEnded("s1")

NI_NOTIFY = Notify(NotifyKind.NEEDS_INPUT, "proj2", "iterm2")
DONE_NOTIFY = Notify(NotifyKind.DONE, "proj2", "iterm2")

CUR_NI = NeedsInput("proj1", "/cwd1", "iterm1")
CUR_DONE = DoneIdle("proj1", "/cwd1", "iterm1")

# (label, current_state, event, expected_transition)
CASES = [
    # --- from Absent ---
    ("absent+need", ABSENT, NEED, Transition(NeedsInput("proj2", "/cwd2", "iterm2"), [NI_NOTIFY])),
    ("absent+done", ABSENT, DONE, Transition(DoneIdle("proj2", "/cwd2", "iterm2"), [DONE_NOTIFY])),
    ("absent+tool", ABSENT, TOOL, Transition(ABSENT)),
    ("absent+typed", ABSENT, TYPED, Transition(ABSENT)),
    ("absent+ended", ABSENT, ENDED, Transition(ABSENT)),
    # --- from NeedsInput ---
    ("need+need", CUR_NI, NEED, Transition(NeedsInput("proj2", "/cwd2", "iterm2"), [NI_NOTIFY])),
    ("need+done", CUR_NI, DONE, Transition(DoneIdle("proj2", "/cwd2", "iterm2"), [DONE_NOTIFY])),
    ("need+tool", CUR_NI, TOOL, Transition(ABSENT)),
    ("need+typed", CUR_NI, TYPED, Transition(ABSENT)),
    ("need+ended", CUR_NI, ENDED, Transition(ABSENT)),
    # --- from DoneIdle ---
    ("done+need", CUR_DONE, NEED, Transition(NeedsInput("proj2", "/cwd2", "iterm2"), [NI_NOTIFY])),
    ("done+done", CUR_DONE, DONE, Transition(DoneIdle("proj2", "/cwd2", "iterm2"))),  # no notify
    ("done+tool", CUR_DONE, TOOL, Transition(CUR_DONE, persist=False)),  # ignored, no write
    ("done+typed", CUR_DONE, TYPED, Transition(ABSENT)),
    ("done+ended", CUR_DONE, ENDED, Transition(ABSENT)),
]


class TransitionTableTest(unittest.TestCase):
    def test_table(self):
        for label, state, event, expected in CASES:
            with self.subTest(case=label):
                self.assertEqual(state.handle(event), expected)

    def test_only_done_plus_tool_skips_persistence(self):
        # persist=False must be unique to done+posttooluse; everything else persists.
        for label, state, event, _expected in CASES:
            with self.subTest(case=label):
                persist = state.handle(event).persist
                self.assertEqual(persist, label != "done+tool")

    def test_notify_fires_only_on_meaningful_transitions(self):
        # done+done and done+tool must be silent (dedup / ignore); the rest that
        # enter needs_input or a fresh done must notify.
        silent = {"absent+tool", "absent+typed", "absent+ended", "need+tool", "need+typed",
                  "need+ended", "done+done", "done+tool", "done+typed", "done+ended"}
        for label, state, event, _expected in CASES:
            with self.subTest(case=label):
                effects = state.handle(event).effects
                self.assertEqual(effects == [], label in silent)


if __name__ == "__main__":
    unittest.main()
