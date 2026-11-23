"""Checks on the pet window that need Qt, run on the off-screen platform so no window is shown."""
import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DESKTOP_PET_CONFIG_DIR", tempfile.mkdtemp())

from PyQt5.QtWidgets import QApplication, QMenu  # noqa: E402

from pet.checks import Checker  # noqa: E402
from pet.config import Settings  # noqa: E402
from pet.pet_window import PetWindow  # noqa: E402
from pet.sprites import FRAMES_DIR, SpriteSet  # noqa: E402

app = QApplication.instance() or QApplication([])


class OtherScreen:
    """Stands in for a screen that is not the main one."""

    def __init__(self, area):
        self.area = area

    def name(self):
        return "other"

    def availableGeometry(self):
        return self.area

    def geometry(self):
        return self.area


@unittest.skipUnless(FRAMES_DIR.exists(), "run tools/slice_sheet.py first")
class NoticeTest(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch("pet.pet_window.save_state")
        self.saved = patcher.start()
        self.addCleanup(patcher.stop)
        # The real checker would read your Harvest token and the saved notification list
        checker_patch = mock.patch.object(Checker, "create", side_effect=lambda settings: Checker(settings))
        checker_patch.start()
        self.addCleanup(checker_patch.stop)
        settings = Settings(watch_harvest=False, watch_github=False)
        self.pet = PetWindow(settings, SpriteSet(settings.scale))
        self.main_area = QApplication.primaryScreen().availableGeometry()

    def on_other_screen(self):
        """Make the pet believe it stands on a screen that is not the main one."""
        other = OtherScreen(self.main_area)
        self.pet.current_screen = lambda: other
        self.pet.pos_x, self.pet.pos_y = -5000.0, 10.0

    def test_notice_from_another_screen_teleports_to_the_middle_of_the_main_screen(self):
        self.on_other_screen()
        self.pet.show_notice("hello", None)
        del self.pet.current_screen
        centre = self.pet.pos_x + self.pet.width() / 2
        self.assertAlmostEqual(centre, self.main_area.center().x(), delta=1)
        self.assertEqual(self.pet.pos_y, self.main_area.bottom() + 1 - self.pet.height())
        self.saved.assert_called()

    def test_notice_then_hops(self):
        self.on_other_screen()
        self.pet.show_notice("hello", None)
        self.assertEqual(self.pet.state, "hop")
        self.assertEqual(self.pet.link_bubble.text, "Pika! hello")

    def test_pet_already_on_main_screen_stays_where_it_is(self):
        self.pet.pos_x = self.main_area.left() + 10.0
        self.pet.pos_y = self.pet.floor_y()
        self.pet.show_notice("hello", None)
        self.assertEqual(self.pet.pos_x, self.main_area.left() + 10.0)
        self.assertEqual(self.pet.state, "hop")

    def test_pet_held_by_the_mouse_is_not_moved(self):
        self.on_other_screen()
        self.pet.state = "grabbed"
        self.pet.show_notice("hello", None)
        self.assertEqual(self.pet.pos_x, -5000.0)
        self.assertEqual(self.pet.state, "grabbed")
        self.assertTrue(self.pet.link_bubble.isVisible())

    def test_claude_messages_teleport_and_hop_with_a_matching_face(self):
        faces = {"done": "hop", "fail": "hop_sad", "attention": "hop_alert"}
        for command, face in faces.items():
            with self.subTest(command=command):
                self.on_other_screen()
                self.pet.set_state("idle", 5)
                self.pet.handle_command(command)
                del self.pet.current_screen
                self.assertEqual(self.pet.state, face)
                centre = self.pet.pos_x + self.pet.width() / 2
                self.assertAlmostEqual(centre, self.main_area.center().x(), delta=1)
                self.assertTrue(self.pet.bubble.isVisible())

    def test_hop_faces_end_back_on_the_floor(self):
        for face in ("hop", "hop_sad", "hop_alert"):
            with self.subTest(face=face):
                self.pet.pos_y = self.pet.floor_y()
                self.pet.start_hop(face)
                for _ in range(500):
                    if self.pet.state not in ("hop", "hop_sad", "hop_alert"):
                        break
                    self.pet.hop(0.033)
                self.assertEqual(self.pet.state, "idle")

    def test_claude_jump_off_keeps_the_old_faces_and_stays_put(self):
        self.pet.settings = Settings(watch_harvest=False, watch_github=False, claude_jump=False)
        self.on_other_screen()
        self.pet.set_state("idle", 5)
        self.pet.handle_command("fail")
        self.assertEqual(self.pet.state, "sad")
        self.assertEqual(self.pet.pos_x, -5000.0)
        self.assertTrue(self.pet.bubble.isVisible())

    def test_notice_goes_into_the_history_and_counts_as_unread(self):
        changes = []
        self.pet.unread_changed.connect(changes.append)
        self.pet.receive_notice("one", "https://github.com/a")
        self.assertEqual(len(self.pet.history), 1)
        self.assertEqual(self.pet.unread, 1)
        self.pet.mark_read()
        self.assertEqual(self.pet.unread, 0)
        self.assertEqual(changes, [True, False])

    def test_history_keeps_only_the_last_ten(self):
        for number in range(12):
            self.pet.receive_notice(f"m{number}", None)
        self.assertEqual(len(self.pet.history), 10)
        self.assertEqual(self.pet.history[0][1], "m2")

    def test_notice_waits_while_a_full_screen_app_is_open(self):
        self.pet.auto_hidden = True
        self.pet.receive_notice("later", "https://github.com/a")
        self.assertFalse(self.pet.link_bubble.isVisible())
        self.assertEqual(len(self.pet.pending), 1)
        self.assertEqual(len(self.pet.history), 1)
        self.pet.auto_hidden = False
        self.pet.flush_pending()
        self.assertEqual(self.pet.link_bubble.text, "Pika! later")
        self.assertEqual(len(self.pet.pending), 0)

    def test_menu_lists_recent_messages_newest_first(self):
        self.pet.receive_notice("old", "https://github.com/o")
        self.pet.receive_notice("new", None)
        menu = QMenu()
        self.pet.add_notice_actions(menu)
        recent = next(a for a in menu.actions() if a.text() == "Recent messages").menu()
        first, second = recent.actions()
        self.assertTrue(first.text().endswith("new"))
        self.assertTrue(second.text().endswith("old"))
        self.assertFalse(first.isEnabled())
        self.assertTrue(second.isEnabled())

    def test_menu_with_no_messages_says_so(self):
        menu = QMenu()
        self.pet.add_notice_actions(menu)
        recent = next(a for a in menu.actions() if a.text() == "Recent messages").menu()
        self.assertEqual([a.text() for a in recent.actions()], ["No messages yet"])

    def test_snooze_item_only_appears_with_harvest_and_toggles(self):
        menus = []

        def texts():
            menus.append(QMenu())
            self.pet.add_notice_actions(menus[-1])
            return {a.text(): a for a in menus[-1].actions()}

        self.assertFalse(any("nooze" in text for text in texts()))
        self.pet.settings = Settings(watch_github=False)
        self.pet.watcher.checker.harvest = object()
        texts()["Snooze Harvest for 1 hour"].trigger()
        self.assertTrue(self.pet.watcher.checker.snoozed())
        [cancel] = [a for text, a in texts().items() if text.startswith("Harvest snoozed until")]
        cancel.trigger()
        self.assertFalse(self.pet.watcher.checker.snoozed())

    def test_break_reminder_teleports_then_runs(self):
        self.on_other_screen()
        self.pet.handle_command("break")
        del self.pet.current_screen
        self.assertEqual(self.pet.state, "remind_walk")
        self.assertAlmostEqual(self.pet.pos_x + self.pet.width() / 2, self.main_area.center().x(), delta=1)

    def test_hidden_pet_does_not_move_for_a_claude_message(self):
        self.on_other_screen()
        self.pet.user_hidden = True
        self.pet.handle_command("done")
        self.assertEqual(self.pet.pos_x, -5000.0)

    def test_screenshot_key_hides_the_pet_and_brings_it_back(self):
        self.pet.show()
        self.assertIsNone(self.pet.shots.xinput)
        self.pet.shots.pressed.emit()
        self.assertFalse(self.pet.isVisible())
        self.assertTrue(self.pet.shot_timer.isActive())
        self.pet.end_screenshot_hide()
        self.assertTrue(self.pet.isVisible())

    def test_screenshot_hides_the_bubble_but_keeps_its_message(self):
        self.pet.show()
        self.pet.show_notice("hello", "https://github.com/a")
        self.assertTrue(self.pet.link_bubble.isVisible())
        self.pet.begin_screenshot_hide()
        self.assertFalse(self.pet.link_bubble.isVisible())
        self.pet.end_screenshot_hide()
        self.assertTrue(self.pet.link_bubble.isVisible())
        self.assertEqual(self.pet.link_bubble.text, "Pika! hello")

    def test_message_that_arrives_during_a_screenshot_waits(self):
        self.pet.show()
        self.pet.begin_screenshot_hide()
        self.pet.receive_notice("later", "https://github.com/a")
        self.assertFalse(self.pet.link_bubble.isVisible())
        self.assertEqual(len(self.pet.pending), 1)
        self.assertEqual(len(self.pet.history), 1)
        self.pet.end_screenshot_hide()
        self.assertEqual(self.pet.link_bubble.text, "Pika! later")
        self.assertEqual(len(self.pet.pending), 0)

    def test_pet_does_not_teleport_or_speak_during_a_screenshot(self):
        self.pet.show()
        self.on_other_screen()
        self.pet.begin_screenshot_hide()
        self.pet.handle_command("done")
        self.assertEqual(self.pet.pos_x, -5000.0)
        self.assertFalse(self.pet.bubble.isVisible())

    def test_screenshot_hiding_can_be_switched_off(self):
        self.pet.show()
        self.pet.settings = Settings(watch_harvest=False, watch_github=False, hide_for_screenshots=False)
        self.pet.begin_screenshot_hide()
        self.assertTrue(self.pet.isVisible())

    def test_pet_the_user_hid_stays_hidden_after_a_screenshot(self):
        self.pet.show()
        self.pet.toggle_user_hidden()
        self.pet.begin_screenshot_hide()
        self.pet.end_screenshot_hide()
        self.assertFalse(self.pet.isVisible())

    def test_repeated_key_presses_keep_it_hidden_longer(self):
        self.pet.show()
        self.pet.begin_screenshot_hide()
        self.pet.begin_screenshot_hide()
        self.assertFalse(self.pet.isVisible())
        self.assertTrue(self.pet.shot_timer.isActive())

    def test_hop_ends_back_on_the_floor(self):
        self.pet.pos_y = self.pet.floor_y()
        self.pet.start_hop()
        for _ in range(500):
            if self.pet.state != "hop":
                break
            self.pet.hop(0.033)
        self.assertEqual(self.pet.state, "idle")
        self.assertEqual(self.pet.pos_y, self.pet.floor_y())

    def test_long_notice_is_shortened(self):
        self.pet.show_notice("x" * 300, None)
        self.assertTrue(self.pet.link_bubble.text.endswith("..."))
        self.assertLessEqual(len(self.pet.link_bubble.text), 6 + 140)


if __name__ == "__main__":
    unittest.main()
