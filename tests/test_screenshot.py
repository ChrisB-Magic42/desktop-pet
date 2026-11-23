import os
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pet.screenshot import KeyParser, ScreenshotKeys, keycodes_for  # noqa: E402

# What xinput test-xi2 prints for one key press, and for some noise around it
KEY_PRESS = """EVENT type 2 (KeyPress)
    device: 3 (11)
    time: 11169900
    detail: 107
    flags:
"""
MOUSE_MOVE = """EVENT type 6 (Motion)
    device: 9 (9)
    time: 11169743
    detail: 0
    flags:
"""
RAW_KEY_PRESS = """EVENT type 13 (RawKeyPress)
    device: 3 (11)
    time: 11169900
    detail: 107
"""


def feed_all(text):
    parser = KeyParser()
    return [code for code in (parser.feed(line) for line in text.splitlines()) if code is not None]


class KeyParserTest(unittest.TestCase):
    def test_key_press_gives_its_key_number(self):
        self.assertEqual(feed_all(KEY_PRESS), [107])

    def test_mouse_moves_and_raw_events_are_ignored(self):
        self.assertEqual(feed_all(MOUSE_MOVE + RAW_KEY_PRESS), [])

    def test_several_presses_in_a_row_with_grep_separators(self):
        text = KEY_PRESS + "--\n" + KEY_PRESS.replace("107", "75")
        self.assertEqual(feed_all(text), [107, 75])

    def test_detail_without_a_header_is_ignored(self):
        self.assertEqual(feed_all("    detail: 107\n"), [])

    def test_bad_detail_is_ignored_and_the_parser_recovers(self):
        parser = KeyParser()
        parser.feed("EVENT type 2 (KeyPress)")
        self.assertIsNone(parser.feed("    detail: abc"))
        self.assertIsNone(parser.feed("    detail: 107"))


@unittest.skipUnless(os.environ.get("DISPLAY"), "needs an X display")
class KeyCodesTest(unittest.TestCase):
    def test_known_names_are_found_and_unknown_ones_left_out(self):
        codes = keycodes_for(["Print", "NoSuchKeyName"])
        self.assertIn("Print", codes)
        self.assertNotIn("NoSuchKeyName", codes)

    def test_no_names_gives_nothing(self):
        self.assertEqual(keycodes_for([]), {})


class StartTest(unittest.TestCase):
    def test_missing_tools_switch_it_off_with_a_message(self):
        keys = ScreenshotKeys()
        with mock.patch("pet.screenshot.shutil.which", return_value=None), mock.patch("builtins.print") as printed:
            self.assertFalse(keys.start(["Print"]))
        self.assertIn("not found", printed.call_args[0][0])
        self.assertIsNone(keys.xinput)

    def test_keys_the_keyboard_does_not_have_switch_it_off(self):
        keys = ScreenshotKeys()
        with mock.patch("pet.screenshot.shutil.which", return_value="/usr/bin/x"), \
                mock.patch("pet.screenshot.keycodes_for", return_value={}), mock.patch("builtins.print") as printed:
            self.assertFalse(keys.start(["Nope"]))
        self.assertIn("none of the keys", printed.call_args[0][0])

    def test_pressed_signal_only_for_watched_keys(self):
        keys = ScreenshotKeys()
        keys.codes = {107}
        seen = []
        keys.pressed.connect(lambda: seen.append(1))

        class FakeGrep:
            def __init__(self, text):
                self.text = text

            def readAllStandardOutput(self):
                return self.text.encode()

        keys.grep = FakeGrep(KEY_PRESS + KEY_PRESS.replace("107", "75"))
        keys.read()
        self.assertEqual(seen, [1])


if __name__ == "__main__":
    unittest.main()
