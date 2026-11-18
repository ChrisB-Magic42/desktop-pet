"""Read your GitHub notifications through the gh command (standard library only)."""
import json
import subprocess
from collections import namedtuple

WEB = "https://github.com"
API_PREFIX = "https://api.github.com/repos/"
TIMEOUT_SECONDS = 30
MAX_POPUPS = 3

# API path word: web path word
PAGE_KINDS = {"issues": "issues", "pulls": "pull", "commits": "commit"}

REASONS = {
    "mention": "mentioned you",
    "team_mention": "mentioned your team",
    "review_requested": "asked for your review",
    "assign": "assigned you",
    "author": "activity on your item",
    "comment": "new comment",
    "state_change": "state changed",
}

Notice = namedtuple("Notice", "key text url")


class GitHubError(Exception):
    pass


def web_url(subject_url, repo_url):
    """The page to open: the issue, pull request or commit, else the repository, else the inbox."""
    if isinstance(subject_url, str) and subject_url.startswith(API_PREFIX):
        parts = subject_url[len(API_PREFIX):].split("/", 3)
        if len(parts) == 4 and parts[2] in PAGE_KINDS:
            owner, repo, kind, rest = parts
            return f"{WEB}/{owner}/{repo}/{PAGE_KINDS[kind]}/{rest}"
    if isinstance(repo_url, str) and repo_url.startswith(WEB + "/"):
        return repo_url
    return f"{WEB}/notifications"


def parse_notifications(items):
    """Turn the API list into Notice tuples, skipping entries that are not shaped as expected."""
    notices = []
    for item in items if isinstance(items, list) else []:
        try:
            repo, subject, reason = item["repository"], item["subject"], item["reason"]
            key = f"{item['id']}:{item['updated_at']}"
            text = f"{repo['full_name']}: {subject['title']} ({REASONS.get(reason, reason.replace('_', ' '))})"
            url = web_url(subject.get("url"), repo.get("html_url"))
        except (KeyError, TypeError, AttributeError):
            continue
        notices.append(Notice(key, text, url))
    return notices


def fetch_notifications(participating=True, run=subprocess.run):
    """Unread notifications, newest first. Raises GitHubError, OSError, ValueError or SubprocessError."""
    query = "notifications?per_page=50" + ("&participating=true" if participating else "")
    result = run(["gh", "api", query], capture_output=True, text=True, timeout=TIMEOUT_SECONDS)
    if result.returncode != 0:
        raise GitHubError(result.stderr.strip() or "gh api failed")
    return parse_notifications(json.loads(result.stdout))


def popups_for(notices, limit=MAX_POPUPS):
    """(text, url) pairs to show. A burst becomes one summary so the screen is not flooded."""
    if len(notices) <= limit:
        return [(notice.text, notice.url) for notice in notices]
    return [(f"{len(notices)} new GitHub notifications", f"{WEB}/notifications")]
