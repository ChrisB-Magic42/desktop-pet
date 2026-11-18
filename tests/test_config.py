import json
import tempfile
import unittest
from pathlib import Path

from pet.config import (
    NAME_MAX,
    Settings,
    load_seen,
    load_settings,
    load_state,
    sanitise,
    save_seen,
    save_settings,
    save_state,
)


class SanitiseTest(unittest.TestCase):
    def test_non_dict_gives_defaults(self):
        self.assertEqual(sanitise(["bad"]), Settings())

    def test_numbers_are_clamped(self):
        result = sanitise({"scale": 99, "speed": -5, "break_minutes": 9999, "bounciness": 500, "gravity": 1})
        self.assertEqual(result.scale, 4.0)
        self.assertEqual(result.speed, 20)
        self.assertEqual(result.break_minutes, 240)
        self.assertEqual(result.bounciness, 95)
        self.assertEqual(result.gravity, 25)

    def test_no_bounce_is_allowed(self):
        self.assertEqual(sanitise({"bounciness": 0}).bounciness, 0)

    def test_break_reminder_can_be_switched_off(self):
        self.assertEqual(sanitise({"break_minutes": 0}).break_minutes, 0)

    def test_check_interval_is_clamped(self):
        self.assertEqual(sanitise({"check_minutes": 0}).check_minutes, 1)
        self.assertEqual(sanitise({"check_minutes": 999}).check_minutes, 60)

    def test_watch_flags_default_on_and_accept_false(self):
        defaults = sanitise({})
        self.assertTrue(defaults.watch_harvest and defaults.watch_github and defaults.github_participating)
        self.assertTrue(defaults.claude_jump)
        result = sanitise(
            {"watch_harvest": False, "watch_github": False, "github_participating": False, "claude_jump": False}
        )
        self.assertFalse(result.watch_harvest or result.watch_github or result.github_participating or result.claude_jump)

    def test_wrong_types_keep_defaults(self):
        result = sanitise(
            {"scale": "big", "speed": True, "sleepy": "yes", "name": 5, "hide_fullscreen": 1, "speech_bubbles": "no"}
        )
        self.assertEqual(result, Settings())

    def test_unknown_behaviour_keeps_default(self):
        self.assertEqual(sanitise({"behaviour": "fly"}).behaviour, "wander")

    def test_name_is_trimmed_and_shortened(self):
        result = sanitise({"name": "  " + "x" * 50 + "  "})
        self.assertEqual(result.name, "x" * NAME_MAX)

    def test_blank_name_keeps_default(self):
        self.assertEqual(sanitise({"name": "   "}).name, "Pika")


class FileTest(unittest.TestCase):
    def test_missing_file_gives_defaults(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(load_settings(Path(folder) / "none.json"), Settings())

    def test_corrupt_file_gives_defaults(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            path.write_text("{not json", encoding="utf-8")
            self.assertEqual(load_settings(path), Settings())

    def test_save_then_load_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "nested" / "settings.json"
            wanted = Settings(
                name="Sparky", scale=2.0, speed=150, behaviour="follow", sleepy=False,
                break_minutes=25, bounciness=40, gravity=150,
            )
            save_settings(wanted, path)
            self.assertEqual(load_settings(path), wanted)
            self.assertEqual(json.loads(path.read_text())["name"], "Sparky")


class StateTest(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "state.json"
            save_state({"screen": "HDMI-1", "offset": 420}, path)
            self.assertEqual(load_state(path), {"screen": "HDMI-1", "offset": 420})

    def test_missing_or_bad_state_gives_none(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "state.json"
            self.assertIsNone(load_state(path))
            for bad in ("{oops", "[1]", '{"screen": 5, "offset": 1}', '{"screen": "a", "offset": true}', '{"screen": "a"}'):
                path.write_text(bad, encoding="utf-8")
                self.assertIsNone(load_state(path), bad)


class SeenTest(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "seen.json"
            save_seen({"b:1", "a:2"}, path)
            self.assertEqual(load_seen(path), {"a:2", "b:1"})

    def test_missing_or_bad_file_gives_none(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "seen.json"
            self.assertIsNone(load_seen(path))
            for bad in ("{oops", '{"a": 1}', "[1, 2]"):
                path.write_text(bad, encoding="utf-8")
                self.assertIsNone(load_seen(path), bad)

    def test_empty_list_is_a_valid_saved_list(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "seen.json"
            save_seen(set(), path)
            self.assertEqual(load_seen(path), set())


if __name__ == "__main__":
    unittest.main()
