"""Settings value object: config.json dict -> behavior, mirroring legacy defaults."""

import unittest

from claudewatch.domain.effect import NotifyKind
from claudewatch.domain.settings import Settings


class SettingsTest(unittest.TestCase):
    def test_defaults_match_legacy(self):
        s = Settings.from_config({})
        self.assertTrue(s.enabled(NotifyKind.NEEDS_INPUT))
        self.assertTrue(s.enabled(NotifyKind.DONE))
        self.assertTrue(s.suppress_when_focused)
        self.assertEqual(s.sound_for(NotifyKind.NEEDS_INPUT), "Ping")
        self.assertIsNone(s.sound_for(NotifyKind.DONE))  # "" -> None (silent)

    def test_overrides(self):
        s = Settings.from_config({
            "notify_on_done": False,
            "suppress_when_focused": False,
            "sound_needs_input": "Glass",
            "sound_done": "Pop",
        })
        self.assertTrue(s.enabled(NotifyKind.NEEDS_INPUT))
        self.assertFalse(s.enabled(NotifyKind.DONE))
        self.assertFalse(s.suppress_when_focused)
        self.assertEqual(s.sound_for(NotifyKind.NEEDS_INPUT), "Glass")
        self.assertEqual(s.sound_for(NotifyKind.DONE), "Pop")

    def test_empty_sound_is_silent(self):
        s = Settings.from_config({"sound_needs_input": ""})
        self.assertIsNone(s.sound_for(NotifyKind.NEEDS_INPUT))


if __name__ == "__main__":
    unittest.main()
