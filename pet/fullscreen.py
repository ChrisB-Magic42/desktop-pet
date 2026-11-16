"""Find out whether the active window is full screen (X11 only, using xprop)."""
import re
import shutil
import subprocess

XPROP = shutil.which("xprop")
ACTIVE_WINDOW = re.compile(r"window id # (0x[0-9a-fA-F]+)")


def _xprop(*args):
    result = subprocess.run([XPROP, *args], capture_output=True, text=True, timeout=1)
    return result.stdout


def active_window_is_fullscreen():
    """Return True when the active window is full screen, False when not or unknown."""
    if not XPROP:
        return False
    try:
        match = ACTIVE_WINDOW.search(_xprop("-root", "_NET_ACTIVE_WINDOW"))
        if not match or match.group(1) == "0x0":
            return False
        return "_NET_WM_STATE_FULLSCREEN" in _xprop("-id", match.group(1), "_NET_WM_STATE")
    except (OSError, subprocess.SubprocessError):
        return False
