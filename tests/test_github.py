import json
import unittest
from types import SimpleNamespace

from pet.github import GitHubError, Notice, fetch_notifications, parse_notifications, popups_for, web_url


def item(thread_id="1", updated="2026-11-18T10:00:00Z", subject_url="https://api.github.com/repos/o/r/pulls/5", reason="mention"):
    return {
        "id": thread_id,
        "updated_at": updated,
        "reason": reason,
        "subject": {"title": "Fix the thing", "url": subject_url},
        "repository": {"full_name": "o/r", "html_url": "https://github.com/o/r"},
    }


class WebUrlTest(unittest.TestCase):
    def test_pull_request(self):
        self.assertEqual(web_url("https://api.github.com/repos/o/r/pulls/5", None), "https://github.com/o/r/pull/5")

    def test_issue_and_commit(self):
        self.assertEqual(web_url("https://api.github.com/repos/o/r/issues/9", None), "https://github.com/o/r/issues/9")
        self.assertEqual(web_url("https://api.github.com/repos/o/r/commits/abc", None), "https://github.com/o/r/commit/abc")

    def test_other_kinds_use_the_repository(self):
        self.assertEqual(web_url("https://api.github.com/repos/o/r/releases/3", "https://github.com/o/r"), "https://github.com/o/r")

    def test_missing_or_foreign_urls_use_the_inbox(self):
        self.assertEqual(web_url(None, None), "https://github.com/notifications")
        self.assertEqual(web_url("https://evil.example/x", "https://evil.example/o/r"), "https://github.com/notifications")


class ParseTest(unittest.TestCase):
    def test_builds_notice(self):
        [notice] = parse_notifications([item()])
        self.assertEqual(notice.key, "1:2026-11-18T10:00:00Z")
        self.assertEqual(notice.text, "o/r: Fix the thing (mentioned you)")
        self.assertEqual(notice.url, "https://github.com/o/r/pull/5")

    def test_unknown_reason_is_made_readable(self):
        [notice] = parse_notifications([item(reason="security_alert")])
        self.assertTrue(notice.text.endswith("(security alert)"))

    def test_bad_entries_are_skipped(self):
        self.assertEqual(parse_notifications([{"id": "1"}, None, "x"]), [])
        self.assertEqual(parse_notifications({"message": "Bad credentials"}), [])


class FetchTest(unittest.TestCase):
    def test_participating_flag_is_sent_to_gh(self):
        calls = []

        def run(command, **_):
            calls.append(command)
            return SimpleNamespace(returncode=0, stdout=json.dumps([item()]), stderr="")

        self.assertEqual(len(fetch_notifications(True, run)), 1)
        fetch_notifications(False, run)
        self.assertIn("participating=true", calls[0][2])
        self.assertNotIn("participating", calls[1][2])

    def test_failure_raises(self):
        def run(command, **_):
            return SimpleNamespace(returncode=1, stdout="", stderr="not logged in")

        with self.assertRaises(GitHubError):
            fetch_notifications(True, run)


class PopupsTest(unittest.TestCase):
    def test_few_notices_show_one_each(self):
        notices = [Notice("a", "A", "https://github.com/a"), Notice("b", "B", "https://github.com/b")]
        self.assertEqual(popups_for(notices), [("A", "https://github.com/a"), ("B", "https://github.com/b")])

    def test_burst_becomes_one_summary(self):
        notices = [Notice(str(n), "x", "https://github.com/x") for n in range(5)]
        self.assertEqual(popups_for(notices), [("5 new GitHub notifications", "https://github.com/notifications")])


if __name__ == "__main__":
    unittest.main()
