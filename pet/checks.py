"""One round of checks: is a Harvest timer running, and is there a new GitHub notification."""
import subprocess
from datetime import datetime, timedelta

from pet.config import SEEN_FILE, load_seen, save_seen
from pet.github import GitHubError, fetch_notifications, popups_for
from pet.harvest import CREDENTIALS_FILE, HarvestClient, insecure_permissions
from pet.reminders import should_remind, should_warn_long

NO_TIMER_TEXT = "No Harvest timer is running"


class Checker:
    def __init__(self, settings, harvest=None, fetch=fetch_notifications, now=datetime.now, seen_path=None):
        self.settings = settings
        self.harvest = harvest
        self.fetch = fetch
        self.now = now
        self.seen_path = seen_path
        self.last_reminded = None
        self.last_long_warning = None
        self.snoozed_until = None
        self.seen = set()
        self.seeded = False
        self.last_problem = {}
        saved = load_seen(seen_path) if seen_path else None
        if saved is not None:
            # Notifications that came while the pet was off still count as new
            self.seen, self.seeded = saved, True
        if settings.watch_harvest and harvest is None:
            print(f"Harvest check is off: no account_id and token in {CREDENTIALS_FILE}")

    @classmethod
    def create(cls, settings):
        warning = insecure_permissions()
        if warning:
            print(warning)
        return cls(settings, HarvestClient.from_file(), seen_path=SEEN_FILE)

    def snooze(self, minutes):
        self.snoozed_until = self.now() + timedelta(minutes=minutes)

    def cancel_snooze(self):
        self.snoozed_until = None

    def snoozed(self):
        return self.snoozed_until is not None and self.now() < self.snoozed_until

    def poll(self):
        """Run the switched-on checks and return the (text, url) popups to show."""
        popups = []
        if self.settings.watch_harvest and self.harvest:
            popups += self.guarded("Harvest", self.check_harvest)
        if self.settings.watch_github:
            popups += self.guarded("GitHub", self.check_github)
        return popups

    def guarded(self, source, check):
        """Run one check. A failure is printed once and gives no popups, and the next round tries again."""
        try:
            result = check()
        except (OSError, ValueError, KeyError, GitHubError, subprocess.SubprocessError) as error:
            problem = f"{type(error).__name__}: {error}"
            if self.last_problem.get(source) != problem:
                print(f"{source} check failed: {problem}")
                self.last_problem[source] = problem
            return []
        self.last_problem.pop(source, None)
        return result

    def check_harvest(self):
        if self.snoozed():
            return []
        entry = self.harvest.running_timer()
        now = self.now()
        if entry is None:
            if not should_remind(now, self.last_reminded):
                return []
            self.last_reminded = now
            return [(NO_TIMER_TEXT, self.harvest.time_url())]
        self.last_reminded = None
        hours = entry.get("hours")
        if isinstance(hours, (int, float)) and should_warn_long(hours, now, self.last_long_warning):
            self.last_long_warning = now
            text = f"Your Harvest timer has run for {hours:.1f} hours. Did you forget to stop it?"
            return [(text, self.harvest.time_url())]
        return []

    def check_github(self):
        notices = self.fetch(self.settings.github_participating)
        keys = {notice.key for notice in notices}
        fresh = [notice for notice in notices if notice.key not in self.seen]
        first_round = not self.seeded
        changed = keys != self.seen
        self.seen, self.seeded = keys, True
        if self.seen_path and (changed or first_round):
            self.remember()
        # The first round with no saved list only records what is already unread
        return [] if first_round else popups_for(fresh)

    def remember(self):
        try:
            save_seen(self.seen, self.seen_path)
        except OSError as error:
            print(f"Could not save the notification list: {error}")
