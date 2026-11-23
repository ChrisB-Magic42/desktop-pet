"""Pet settings and saved position: defaults, validation and the JSON files."""
import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("DESKTOP_PET_CONFIG_DIR") or Path.home() / ".config" / "desktop-pet")
CONFIG_FILE = CONFIG_DIR / "settings.json"
STATE_FILE = CONFIG_DIR / "state.json"
SEEN_FILE = CONFIG_DIR / "seen.json"

BEHAVIOURS = ("wander", "follow", "stay")
NAME_MAX = 20
LIMITS = {
    "scale": (0.5, 4.0),
    "speed": (20, 400),
    "break_minutes": (0, 240),
    "bounciness": (0, 95),
    "gravity": (25, 300),
    "check_minutes": (1, 60),
    "screenshot_hide_seconds": (1, 60),
}
KEY_NAME = re.compile(r"[A-Za-z0-9_]{1,20}")
MAX_KEYS = 10
DEFAULT_SCREENSHOT_KEYS = "Print,F9"


@dataclass
class Settings:
    name: str = "Pika"
    scale: float = 1.5
    speed: int = 90
    behaviour: str = "wander"
    sleepy: bool = True
    always_on_top: bool = True
    hide_fullscreen: bool = True
    break_minutes: int = 50
    bounciness: int = 70
    gravity: int = 100
    speech_bubbles: bool = True
    autostart: bool = False
    watch_harvest: bool = True
    watch_github: bool = True
    github_participating: bool = True
    claude_jump: bool = True
    check_minutes: int = 2
    hide_for_screenshots: bool = True
    screenshot_keys: str = DEFAULT_SCREENSHOT_KEYS
    screenshot_hide_seconds: int = 10


def key_names(text):
    """The valid key names in a comma separated text such as "Print, F9"."""
    if not isinstance(text, str):
        return []
    names = [part.strip() for part in text.split(",")]
    return [name for name in names if KEY_NAME.fullmatch(name)][:MAX_KEYS]


def _number(value, key, default, cast):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    low, high = LIMITS[key]
    return cast(min(max(value, low), high))


def _flag(value, default):
    return value if isinstance(value, bool) else default


def sanitise(data):
    """Build valid settings from untrusted data, keeping defaults for bad values."""
    base = Settings()
    if not isinstance(data, dict):
        return base
    name = data.get("name")
    if isinstance(name, str) and name.strip():
        base.name = name.strip()[:NAME_MAX]
    base.scale = _number(data.get("scale"), "scale", base.scale, float)
    base.speed = _number(data.get("speed"), "speed", base.speed, int)
    base.break_minutes = _number(data.get("break_minutes"), "break_minutes", base.break_minutes, int)
    base.bounciness = _number(data.get("bounciness"), "bounciness", base.bounciness, int)
    base.gravity = _number(data.get("gravity"), "gravity", base.gravity, int)
    base.check_minutes = _number(data.get("check_minutes"), "check_minutes", base.check_minutes, int)
    if data.get("behaviour") in BEHAVIOURS:
        base.behaviour = data["behaviour"]
    base.sleepy = _flag(data.get("sleepy"), base.sleepy)
    base.always_on_top = _flag(data.get("always_on_top"), base.always_on_top)
    base.hide_fullscreen = _flag(data.get("hide_fullscreen"), base.hide_fullscreen)
    base.speech_bubbles = _flag(data.get("speech_bubbles"), base.speech_bubbles)
    base.autostart = _flag(data.get("autostart"), base.autostart)
    base.watch_harvest = _flag(data.get("watch_harvest"), base.watch_harvest)
    base.watch_github = _flag(data.get("watch_github"), base.watch_github)
    base.github_participating = _flag(data.get("github_participating"), base.github_participating)
    base.claude_jump = _flag(data.get("claude_jump"), base.claude_jump)
    base.hide_for_screenshots = _flag(data.get("hide_for_screenshots"), base.hide_for_screenshots)
    base.screenshot_hide_seconds = _number(
        data.get("screenshot_hide_seconds"), "screenshot_hide_seconds", base.screenshot_hide_seconds, int
    )
    names = key_names(data.get("screenshot_keys"))
    if names:
        base.screenshot_keys = ",".join(names)
    return base


def _write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(temp, path)


def load_settings(path=CONFIG_FILE):
    try:
        return sanitise(json.loads(Path(path).read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return Settings()


def save_settings(settings, path=CONFIG_FILE):
    _write_json(path, asdict(settings))


def load_state(path=STATE_FILE):
    """Return the saved {"screen": name, "offset": pixels} or None."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    screen, offset = data.get("screen"), data.get("offset")
    if not isinstance(screen, str) or isinstance(offset, bool) or not isinstance(offset, int):
        return None
    return {"screen": screen, "offset": offset}


def save_state(state, path=STATE_FILE):
    _write_json(path, state)


def load_seen(path=SEEN_FILE):
    """Return the saved set of GitHub notification keys, or None when there is no usable file."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, list) or not all(isinstance(key, str) for key in data):
        return None
    return set(data)


def save_seen(keys, path=SEEN_FILE):
    _write_json(path, sorted(keys))
