"""Watch for screenshot keys so the pet can hide before the picture is taken (X11 only)."""
import ctypes
import ctypes.util
import shutil

from PyQt5.QtCore import QObject, QProcess, pyqtSignal

KEY_PRESS_HEADER = "EVENT type 2 (KeyPress)"
TOOLS = ("stdbuf", "xinput", "grep")


def keycodes_for(names):
    """Map key names to this keyboard's key numbers. Names the keyboard does not have are left out."""
    try:
        x11 = ctypes.CDLL(ctypes.util.find_library("X11"))
        x11.XOpenDisplay.restype = ctypes.c_void_p
        x11.XStringToKeysym.restype = ctypes.c_ulong
        x11.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        x11.XKeysymToKeycode.restype = ctypes.c_ubyte
        x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
    except (OSError, TypeError, AttributeError):
        return {}
    display = x11.XOpenDisplay(None)
    if not display:
        return {}
    codes = {}
    try:
        for name in names:
            keysym = x11.XStringToKeysym(name.encode())
            # An unknown name gives symbol 0, which would match a random unused key, so skip it
            if keysym:
                codes[name] = x11.XKeysymToKeycode(display, keysym)
    finally:
        x11.XCloseDisplay(display)
    return {name: code for name, code in codes.items() if code}


class KeyParser:
    """Reads the lines xinput prints and returns the key number each time a key goes down."""

    def __init__(self):
        self.waiting = False

    def feed(self, line):
        line = line.strip()
        if line == KEY_PRESS_HEADER:
            self.waiting = True
        elif self.waiting and line.startswith("detail:"):
            self.waiting = False
            try:
                return int(line.split(":", 1)[1])
            except ValueError:
                return None
        return None


class ScreenshotKeys(QObject):
    pressed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.codes = set()
        self.parser = KeyParser()
        self.xinput = None
        self.grep = None

    def start(self, names):
        """Start watching the given keys. Returns False, with a message, when it cannot."""
        self.stop()
        missing = [tool for tool in TOOLS if not shutil.which(tool)]
        if missing:
            print(f"Screenshot hiding is off: {', '.join(missing)} not found (sudo apt install x11-utils xinput)")
            return False
        self.codes = set(keycodes_for(names).values())
        if not self.codes:
            print(f"Screenshot hiding is off: none of the keys {', '.join(names) or '(none)'} exist on this keyboard")
            return False
        # xinput prints a lot for every mouse move, so grep keeps only the key presses
        self.grep = QProcess(self)
        self.grep.setProgram("grep")
        self.grep.setArguments(["--line-buffered", "-F", "-A3", KEY_PRESS_HEADER])
        self.grep.readyReadStandardOutput.connect(self.read)
        self.xinput = QProcess(self)
        self.xinput.setProgram("stdbuf")
        self.xinput.setArguments(["-oL", "xinput", "test-xi2", "--root"])
        self.xinput.setStandardOutputProcess(self.grep)
        self.grep.start()
        self.xinput.start()
        return True

    def read(self):
        text = bytes(self.grep.readAllStandardOutput()).decode("utf-8", "ignore")
        for line in text.splitlines():
            if self.parser.feed(line) in self.codes:
                self.pressed.emit()

    def stop(self):
        for process in (self.xinput, self.grep):
            if process is not None:
                process.kill()
                process.waitForFinished(500)
        self.xinput = self.grep = None
        self.parser = KeyParser()
