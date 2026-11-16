# Desktop pet

A Pikachu that walks on the bottom of your screen (Linux, X11, PyQt5).

## Run

```bash
sudo apt install python3-pyqt5
python3 tools/slice_sheet.py   # once, cuts assets/pikachu-sheet.jpg into frames
python3 main.py
```

## Controls

- Click: happy dance. Double-click: Thunder Shock. Drag: pick it up and drop it.
- Right-click the pet or use the tray icon: Settings, Hide pet, Quit.

## Settings

Saved in `~/.config/desktop-pet/settings.json` (position in `state.json`).
Size, speed, behaviour (wander, follow the mouse, stay), sleeping, stay on top,
hide for full-screen apps, break reminder interval (0 is off), bounciness and
gravity when thrown (percent), start at login.

## Commands from other programs

```bash
python3 tools/pet_notify.py done       # happy dance and a speech bubble
python3 tools/pet_notify.py fail       # sad
python3 tools/pet_notify.py attention  # surprised
python3 tools/pet_notify.py break      # break reminder now
```

Claude Code hooks (add to `~/.claude/settings.json`):

```json
{
  "hooks": {
    "Stop": [{"hooks": [{"type": "command", "command": "python3 ~/projects/desktop-pet/tools/pet_notify.py done || true"}]}],
    "Notification": [{"hooks": [{"type": "command", "command": "python3 ~/projects/desktop-pet/tools/pet_notify.py attention || true"}]}]
  }
}
```

## Tests

```bash
python3 -m unittest discover -s tests -t .
```
