import unittest
from datetime import datetime, timedelta

from pet.reminders import should_remind, should_warn_long

WEDNESDAY = datetime(2026, 11, 18, 10, 0)
SATURDAY = datetime(2026, 11, 21, 10, 0)


class ShouldRemindTest(unittest.TestCase):
    def test_first_reminder_in_working_hours(self):
        self.assertTrue(should_remind(WEDNESDAY, None))

    def test_not_before_start_or_from_end_of_day(self):
        self.assertFalse(should_remind(WEDNESDAY.replace(hour=8, minute=59), None))
        self.assertTrue(should_remind(WEDNESDAY.replace(hour=9, minute=0), None))
        self.assertTrue(should_remind(WEDNESDAY.replace(hour=17, minute=29), None))
        self.assertFalse(should_remind(WEDNESDAY.replace(hour=17, minute=30), None))

    def test_not_at_the_weekend(self):
        self.assertFalse(should_remind(SATURDAY, None))
        self.assertFalse(should_remind(SATURDAY + timedelta(days=1), None))

    def test_waits_between_reminders(self):
        self.assertFalse(should_remind(WEDNESDAY, WEDNESDAY - timedelta(minutes=9)))
        self.assertTrue(should_remind(WEDNESDAY, WEDNESDAY - timedelta(minutes=10)))


class ShouldWarnLongTest(unittest.TestCase):
    def test_only_from_eight_hours(self):
        self.assertFalse(should_warn_long(7.99, WEDNESDAY, None))
        self.assertTrue(should_warn_long(8.0, WEDNESDAY, None))

    def test_any_day_and_hour_because_a_forgotten_timer_runs_overnight(self):
        self.assertTrue(should_warn_long(12.0, SATURDAY.replace(hour=3), None))

    def test_waits_an_hour_between_warnings(self):
        self.assertFalse(should_warn_long(9.0, WEDNESDAY, WEDNESDAY - timedelta(minutes=59)))
        self.assertTrue(should_warn_long(9.0, WEDNESDAY, WEDNESDAY - timedelta(hours=1)))


if __name__ == "__main__":
    unittest.main()
