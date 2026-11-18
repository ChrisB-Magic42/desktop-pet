"""The rules for when to remind you about your Harvest timer."""
from datetime import time, timedelta

WORK_DAYS = range(5)
WORK_START = time(9, 0)
WORK_END = time(17, 30)
REPEAT = timedelta(minutes=10)
LONG_TIMER_HOURS = 8
LONG_TIMER_REPEAT = timedelta(hours=1)


def should_remind(now, last_reminded):
    """True on a working weekday, inside working hours, and at least REPEAT after the last popup."""
    if now.weekday() not in WORK_DAYS or not WORK_START <= now.time() < WORK_END:
        return False
    return last_reminded is None or now - last_reminded >= REPEAT


def should_warn_long(hours, now, last_warned):
    """True when a running timer has passed LONG_TIMER_HOURS and the last warning was long enough ago."""
    if hours < LONG_TIMER_HOURS:
        return False
    return last_warned is None or now - last_warned >= LONG_TIMER_REPEAT
