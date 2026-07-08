"""Hook payload -> domain Event translation."""

import unittest

from claudewatch.adapters import hook_event_adapter
from claudewatch.domain.event import Done, NeedInput, SessionEnded, ToolRan, UserTyped

PAYLOAD = {"session_id": "s1", "cwd": "/Users/me/projects/deca/"}
ENV = {"ITERM_SESSION_ID": "w0t0p0:GUID"}


class HookEventAdapterTest(unittest.TestCase):
    def test_notification_maps_to_needinput_with_derived_project(self):
        e = hook_event_adapter.to_event("notification", PAYLOAD, ENV)
        self.assertEqual(e, NeedInput("s1", "deca", "/Users/me/projects/deca/", "w0t0p0:GUID"))

    def test_idle_maps_to_done(self):
        e = hook_event_adapter.to_event("idle", PAYLOAD, ENV)
        self.assertEqual(e, Done("s1", "deca", "/Users/me/projects/deca/", "w0t0p0:GUID"))

    def test_clearer_events_carry_only_session_id(self):
        self.assertEqual(hook_event_adapter.to_event("posttooluse", PAYLOAD, ENV), ToolRan("s1"))
        self.assertEqual(hook_event_adapter.to_event("prompt", PAYLOAD, ENV), UserTyped("s1"))
        self.assertEqual(hook_event_adapter.to_event("session_end", PAYLOAD, ENV), SessionEnded("s1"))

    def test_unknown_kind_returns_none(self):
        self.assertIsNone(hook_event_adapter.to_event("stop", PAYLOAD, ENV))
        self.assertIsNone(hook_event_adapter.to_event("", PAYLOAD, ENV))

    def test_missing_session_id_defaults(self):
        e = hook_event_adapter.to_event("posttooluse", {}, {})
        self.assertEqual(e.session_id, "unknown")

    def test_missing_iterm_is_empty(self):
        e = hook_event_adapter.to_event("notification", PAYLOAD, {})
        self.assertEqual(e.iterm_id, "")


if __name__ == "__main__":
    unittest.main()
