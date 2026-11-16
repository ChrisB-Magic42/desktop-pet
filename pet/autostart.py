"""Turn "start when I log in" on or off with a desktop autostart file."""
import sys
from pathlib import Path

AUTOSTART_FILE = Path.home() / ".config" / "autostart" / "desktop-pet.desktop"
MAIN_SCRIPT = Path(__file__).resolve().parent.parent / "main.py"

ENTRY = """[Desktop Entry]
Type=Application
Name=Desktop Pet
Exec="{python}" "{script}"
X-GNOME-Autostart-enabled=true
"""


def set_autostart(enabled):
    if enabled:
        AUTOSTART_FILE.parent.mkdir(parents=True, exist_ok=True)
        AUTOSTART_FILE.write_text(ENTRY.format(python=sys.executable, script=MAIN_SCRIPT), encoding="utf-8")
    else:
        AUTOSTART_FILE.unlink(missing_ok=True)
