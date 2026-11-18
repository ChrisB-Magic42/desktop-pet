"""Load the sliced frames, group them into animations and scale them."""
from dataclasses import dataclass
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPixmap, QRegion, QTransform

FRAMES_DIR = Path(__file__).resolve().parent.parent / "assets" / "frames"


@dataclass(frozen=True)
class Animation:
    frames: tuple
    fps: float
    loop: bool = True


# Frame names are rRcC: row R, column C of the sprite sheet (facing right)
ANIMATIONS = {
    "idle": Animation(("r0c0", "r0c5"), 1.0),
    "walk": Animation(("r2c0", "r2c1", "r2c2", "r2c1"), 6),
    "dash": Animation(("r3c5",), 1),
    "sit": Animation(("r5c0",), 1),
    "sleep": Animation(("r5c2",), 1),
    "eat": Animation(("r5c3", "r5c0"), 1.5),
    "happy": Animation(("r4c5", "r5c5", "r4c5", "r5c1") * 2, 5, loop=False),
    "hop": Animation(("r4c5", "r5c5", "r4c5", "r5c1") * 2, 6, loop=False),
    "hop_sad": Animation(("r4c3",), 1),
    "hop_alert": Animation(("r4c4", "r4c1"), 6),
    "attack": Animation(("r3c0", "r3c1", "r3c2", "r3c1"), 3, loop=False),
    "grabbed": Animation(("r4c4",), 1),
    "fall": Animation(("r2c3",), 1),
    "dizzy": Animation(("r5c4",), 1),
    "sad": Animation(("r4c3",), 1),
    "alert": Animation(("r4c4", "r4c1"), 3),
    "remind_walk": Animation(("r3c5",), 1),
    "remind": Animation(("r3c0", "r3c1", "r3c2", "r3c1"), 3),
}


class SpriteSet:
    def __init__(self, scale):
        names = {name for animation in ANIMATIONS.values() for name in animation.frames}
        missing = sorted(name for name in names if not (FRAMES_DIR / f"{name}.png").exists())
        if missing:
            raise FileNotFoundError(f"Missing frames {missing}. Run tools/slice_sheet.py first.")
        self._originals = {name: QPixmap(str(FRAMES_DIR / f"{name}.png")) for name in names}
        self.canvas = (0, 0)
        self.scale = None
        self.rebuild(scale)

    def rebuild(self, scale):
        """Scale every frame (and its mirror image) with sharp pixel edges."""
        mirror = QTransform().scale(-1, 1)
        self._right, self._left, self._regions = {}, {}, {}
        for name, pixmap in self._originals.items():
            size = (max(1, round(pixmap.width() * scale)), max(1, round(pixmap.height() * scale)))
            scaled = pixmap.scaled(size[0], size[1], Qt.IgnoreAspectRatio, Qt.FastTransformation)
            self._right[name] = scaled
            self._left[name] = scaled.transformed(mirror)
            self._regions[(name, True)] = QRegion(self._right[name].mask())
            self._regions[(name, False)] = QRegion(self._left[name].mask())
        self.canvas = (
            max(p.width() for p in self._right.values()),
            max(p.height() for p in self._right.values()),
        )
        self.scale = scale

    def pixmap(self, name, facing_right):
        return (self._right if facing_right else self._left)[name]

    def region(self, name, facing_right):
        """The drawn pixels of a frame, used so clicks pass through empty areas."""
        return self._regions[(name, facing_right)]

    def icon(self):
        return QIcon(self._originals["r0c0"].scaled(64, 64, Qt.KeepAspectRatio, Qt.FastTransformation))
