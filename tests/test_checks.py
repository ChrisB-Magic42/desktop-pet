import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from pet.checks import NO_TIMER_TEXT, Checker
from pet.config import Settings, load_seen, save_seen
from pet.github import GitHubError, Notice

NOW = datetime(2026, 11, 18, 10, 0)
TIME_URL = "https://example.harvestapp.com/time"


class FakeHarvest:
    def __init__(self, entry=None, error=None):
        self.entry = entry
        self.error = error
        self.calls = 0

    def running_timer(self):
        self.calls += 1
        if self.error:
            raise self.error
        return self.entry

    def time_url(self):
        return TIME_URL


def notice(name):
    return Notice(name, f"text {name}", f"https://github.com/{name}")


class HarvestCheckTest(unittest.TestCase):
    def checker(self, harvest, **settings):
        return Checker(Settings(watch_github=False, **settings), harvest, now=lambda: NOW)

    def test_running_timer_gives_no_popup_and_resets_reminder(self):
        checker = self.checker(FakeHarvest({"hours": 1.0}))
        checker.last_reminded = NOW
        self.assertEqual(checker.poll(), [])
        self.assertIsNone(checker.last_reminded)

    def test_missing_timer_pops_up_when_rule_allows(self):
        checker = self.checker(FakeHarvest())
        with mock.patch("pet.checks.should_remind", return_value=True):
            self.assertEqual(checker.poll(), [(NO_TIMER_TEXT, TIME_URL)])
        self.assertEqual(checker.last_reminded, NOW)

    def test_missing_timer_is_quiet_when_rule_says_no(self):
        checker = self.checker(FakeHarvest())
        with mock.patch("pet.checks.should_remind", return_value=False):
            self.assertEqual(checker.poll(), [])
        self.assertIsNone(checker.last_reminded)

    def test_rule_receives_now_and_last_reminded(self):
        checker = self.checker(FakeHarvest())
        with mock.patch("pet.checks.should_remind", return_value=False) as rule:
            checker.poll()
        rule.assert_called_once_with(NOW, None)

    def test_switched_off_never_asks_harvest(self):
        harvest = FakeHarvest(error=OSError("should not be called"))
        self.assertEqual(self.checker(harvest, watch_harvest=False).poll(), [])
        self.assertEqual(harvest.calls, 0)

    def test_failure_is_printed_once_and_gives_no_popup(self):
        checker = self.checker(FakeHarvest(error=OSError("offline")))
        with mock.patch("builtins.print") as printed:
            self.assertEqual(checker.poll(), [])
            self.assertEqual(checker.poll(), [])
        printed.assert_called_once()


class SnoozeTest(unittest.TestCase):
    def setUp(self):
        self.clock = [NOW]
        self.harvest = FakeHarvest()
        self.checker = Checker(Settings(watch_github=False), self.harvest, now=lambda: self.clock[0])

    def test_snooze_silences_harvest_until_it_ends(self):
        self.checker.snooze(60)
        with mock.patch("pet.checks.should_remind", return_value=True):
            self.assertEqual(self.checker.poll(), [])
            self.assertEqual(self.harvest.calls, 0)
            self.clock[0] = NOW + timedelta(minutes=61)
            self.assertEqual(self.checker.poll(), [(NO_TIMER_TEXT, TIME_URL)])

    def test_cancel_snooze(self):
        self.checker.snooze(60)
        self.assertTrue(self.checker.snoozed())
        self.checker.cancel_snooze()
        self.assertFalse(self.checker.snoozed())

    def test_snooze_also_silences_the_long_timer_warning(self):
        self.harvest.entry = {"hours": 9.0}
        self.checker.snooze(60)
        self.assertEqual(self.checker.poll(), [])


class LongTimerTest(unittest.TestCase):
    def setUp(self):
        self.clock = [NOW]
        self.harvest = FakeHarvest({"hours": 9.25})
        self.checker = Checker(Settings(watch_github=False), self.harvest, now=lambda: self.clock[0])

    def test_warns_about_a_timer_left_running(self):
        [(text, url)] = self.checker.poll()
        self.assertIn("9.2 hours", text)
        self.assertEqual(url, TIME_URL)

    def test_warns_again_only_after_the_repeat_time(self):
        self.checker.poll()
        self.clock[0] = NOW + timedelta(minutes=30)
        self.assertEqual(self.checker.poll(), [])
        self.clock[0] = NOW + timedelta(minutes=61)
        self.assertEqual(len(self.checker.poll()), 1)

    def test_short_timer_gives_no_warning(self):
        self.harvest.entry = {"hours": 2.0}
        self.assertEqual(self.checker.poll(), [])

    def test_entry_without_hours_gives_no_warning(self):
        self.harvest.entry = {"id": 1}
        self.assertEqual(self.checker.poll(), [])


class GitHubCheckTest(unittest.TestCase):
    def checker(self, rounds, seen_path=None):
        answers = iter(rounds)
        fetch = lambda participating: next(answers)  # noqa: E731
        return Checker(Settings(watch_harvest=False), fetch=fetch, now=lambda: NOW, seen_path=seen_path)

    def test_first_round_only_records_existing_notifications(self):
        checker = self.checker([[notice("a"), notice("b")]])
        self.assertEqual(checker.poll(), [])

    def test_only_new_notifications_pop_up(self):
        checker = self.checker([[notice("a")], [notice("a"), notice("b")], [notice("a"), notice("b")]])
        checker.poll()
        self.assertEqual(checker.poll(), [("text b", "https://github.com/b")])
        self.assertEqual(checker.poll(), [])

    def test_failed_first_round_does_not_count_as_seeded(self):
        def fetch(participating):
            raise GitHubError("not logged in")

        checker = Checker(Settings(watch_harvest=False), fetch=fetch)
        with mock.patch("builtins.print"):
            self.assertEqual(checker.poll(), [])
        self.assertFalse(checker.seeded)

    def test_participating_setting_is_passed_on(self):
        asked = []

        def fetch(participating):
            asked.append(participating)
            return []

        Checker(Settings(watch_harvest=False, github_participating=False), fetch=fetch).poll()
        self.assertEqual(asked, [False])

    def test_switched_off_never_calls_gh(self):
        def fetch(participating):
            raise AssertionError("should not be called")

        self.assertEqual(Checker(Settings(watch_harvest=False, watch_github=False), fetch=fetch).poll(), [])


class SavedListTest(unittest.TestCase):
    def test_first_ever_round_saves_the_list_and_shows_nothing(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "seen.json"
            checker = GitHubCheckTest().checker([[notice("a")]], path)
            self.assertEqual(checker.poll(), [])
            self.assertEqual(load_seen(path), {"a"})

    def test_notification_that_came_while_the_pet_was_off_is_shown(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "seen.json"
            save_seen({"a"}, path)
            checker = GitHubCheckTest().checker([[notice("a"), notice("b")]], path)
            self.assertEqual(checker.poll(), [("text b", "https://github.com/b")])
            self.assertEqual(load_seen(path), {"a", "b"})

    def test_list_follows_what_is_unread_now(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "seen.json"
            save_seen({"a", "b"}, path)
            checker = GitHubCheckTest().checker([[notice("b")]], path)
            checker.poll()
            self.assertEqual(load_seen(path), {"b"})

    def test_unwritable_list_does_not_stop_the_check(self):
        checker = GitHubCheckTest().checker([[notice("a")], [notice("a"), notice("b")]], "/nonexistent-folder/x/seen.json")
        with mock.patch("pet.checks.save_seen", side_effect=OSError("read-only")), mock.patch("builtins.print"):
            checker.poll()
            self.assertEqual(checker.poll(), [("text b", "https://github.com/b")])


if __name__ == "__main__":
    unittest.main()
