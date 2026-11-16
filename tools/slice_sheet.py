"""Slice the Pikachu sprite sheet into transparent PNG frames named rRcC.png."""
import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SHEET = ROOT / "assets" / "pikachu-sheet.jpg"
OUT = ROOT / "assets" / "frames"

# Cell edges measured from the gaps between sprites on the sheet
COL_EDGES = [0, 84, 171, 257, 341, 424, 512]
ROW_EDGES = [40, 108, 180, 267, 350, 430, 512]
MIN_AREA = 12


def flood(mask, seeds):
    """Return every True pixel of mask reachable from the seed pixels."""
    h, w = mask.shape
    seen = np.zeros_like(mask)
    queue = deque(s for s in seeds if mask[s])
    for y, x in queue:
        seen[y, x] = True
    while queue:
        y, x = queue.popleft()
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True
                queue.append((ny, nx))
    return seen


def remove_specks(alpha):
    """Drop tiny foreground blobs left by JPEG noise."""
    h, w = alpha.shape
    todo = alpha.copy()
    for y in range(h):
        for x in range(w):
            if todo[y, x]:
                blob = flood(todo, [(y, x)])
                todo &= ~blob
                if blob.sum() < MIN_AREA:
                    alpha &= ~blob
    return alpha


def trim_fringe(alpha, light_grey):
    """Remove pale halo pixels that touch the background."""
    h, w = alpha.shape
    padded = np.pad(~alpha, 1, constant_values=True)
    touches = np.zeros_like(alpha)
    for dy in range(3):
        for dx in range(3):
            touches |= padded[dy:dy + h, dx:dx + w]
    return alpha & ~(touches & light_grey)


def cut_cell(cell):
    rgb = cell.astype(int)
    spread = rgb.max(axis=2) - rgb.min(axis=2)
    light_grey = (spread < 25) & (rgb.mean(axis=2) > 110)
    h, w = light_grey.shape
    border = [(0, x) for x in range(w)] + [(h - 1, x) for x in range(w)]
    border += [(y, 0) for y in range(h)] + [(y, w - 1) for y in range(h)]
    background = flood(light_grey, border)
    alpha = trim_fringe(remove_specks(~background), light_grey)
    ys, xs = np.where(alpha)
    if not len(ys):
        return None
    rgba = np.dstack([cell, (alpha * 255).astype(np.uint8)])
    return Image.fromarray(rgba[ys.min():ys.max() + 1, xs.min():xs.max() + 1], "RGBA")


def slice_sheet():
    sheet = np.asarray(Image.open(SHEET).convert("RGB"))
    OUT.mkdir(parents=True, exist_ok=True)
    frames = {}
    for r in range(6):
        for c in range(6):
            cell = sheet[ROW_EDGES[r]:ROW_EDGES[r + 1], COL_EDGES[c]:COL_EDGES[c + 1]]
            frame = cut_cell(cell)
            if frame:
                frame.save(OUT / f"r{r}c{c}.png")
                frames[(r, c)] = frame
    return frames


def make_icon(frame):
    """Write a 128 pixel icon for the desktop launcher from one frame."""
    scale = 112 / max(frame.size)
    art = frame.resize((round(frame.width * scale), round(frame.height * scale)), Image.NEAREST)
    icon = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    icon.paste(art, ((128 - art.width) // 2, (128 - art.height) // 2), art)
    icon.save(OUT.parent / "icon.png")


def contact_sheet(frames, target):
    """Write a labelled, enlarged overview so frames can be picked by eye."""
    size = 150
    sheet = Image.new("RGB", (size * 6, size * 6), (60, 90, 140))
    draw = ImageDraw.Draw(sheet)
    for (r, c), frame in frames.items():
        scale = min((size - 20) / frame.width, (size - 20) / frame.height)
        shown = frame.resize((max(1, int(frame.width * scale)), max(1, int(frame.height * scale))), Image.NEAREST)
        sheet.paste(shown, (c * size + (size - shown.width) // 2, r * size + 16 + (size - 16 - shown.height) // 2), shown)
        draw.text((c * size + 4, r * size + 3), f"r{r}c{c}", fill=(255, 255, 255))
        draw.rectangle([c * size, r * size, (c + 1) * size - 1, (r + 1) * size - 1], outline=(255, 255, 255))
    sheet.save(target)


if __name__ == "__main__":
    result = slice_sheet()
    print(f"saved {len(result)} frames to {OUT}")
    make_icon(result[(0, 0)])
    print(f"saved icon to {OUT.parent / 'icon.png'}")
    if len(sys.argv) > 1:
        contact_sheet(result, Path(sys.argv[1]))
