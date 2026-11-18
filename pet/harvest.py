"""Ask Harvest whether a timer is running (standard library only)."""
import json
import re
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

from pet.config import CONFIG_DIR

CREDENTIALS_FILE = CONFIG_DIR / "harvest.json"
API = "https://api.harvestapp.com/v2"
TIMEOUT_SECONDS = 15
DOMAIN_PATTERN = re.compile(r"[a-z0-9-]+\.harvestapp\.com")
KEYRING_COMMAND = ["secret-tool", "lookup", "application", "desktop-pet", "service", "harvest"]


def keyring_token(run=subprocess.run):
    """The token saved in the system keyring with secret-tool, or "" when there is none."""
    try:
        result = run(KEYRING_COMMAND, capture_output=True, text=True, timeout=TIMEOUT_SECONDS)
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def load_credentials(path=CREDENTIALS_FILE, run=subprocess.run):
    """Return (account_id, token) from the file, or None. A missing token is looked up in the keyring."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    account_id = str(data.get("account_id") or "").strip()
    token = str(data.get("token") or "").strip()
    if account_id and not token:
        token = keyring_token(run)
    return (account_id, token) if account_id and token else None


def insecure_permissions(path=CREDENTIALS_FILE):
    """A warning when other users can read the credentials file, else None."""
    try:
        mode = Path(path).stat().st_mode
    except OSError:
        return None
    if mode & 0o077:
        return f"Warning: other users can read {path}. Run: chmod 600 {path}"
    return None


class HarvestClient:
    def __init__(self, account_id, token, opener=urllib.request.urlopen):
        self.account_id = account_id
        self.token = token
        self.opener = opener
        self.user_id = None
        self.domain = None

    @classmethod
    def from_file(cls, path=CREDENTIALS_FILE, run=subprocess.run):
        credentials = load_credentials(path, run)
        return cls(*credentials) if credentials else None

    def get(self, path, **query):
        url = f"{API}/{path}"
        if query:
            url += "?" + urllib.parse.urlencode(query)
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Harvest-Account-Id": self.account_id,
            "User-Agent": "desktop-pet",
        }
        with self.opener(urllib.request.Request(url, headers=headers), timeout=TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))

    def running_timer(self):
        """Your running time entry as a dict, or None. Raises OSError or ValueError on failure."""
        if self.user_id is None:
            self.user_id = self.get("users/me")["id"]
        data = self.get("time_entries", user_id=self.user_id, is_running="true", per_page=1)
        entries = data["time_entries"]
        return entries[0] if entries else None

    def time_url(self):
        """The Harvest time page of this account, or None when it cannot be found."""
        if self.domain is None:
            try:
                domain = self.get("company").get("full_domain")
            except (OSError, ValueError, AttributeError):
                return None
            self.domain = domain if isinstance(domain, str) and DOMAIN_PATTERN.fullmatch(domain) else ""
        return f"https://{self.domain}/time" if self.domain else None
