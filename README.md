# Desktop pet

A small Pikachu that lives on your screen. It walks along the bottom, sits, sleeps, follows
your mouse, bounces when you throw it, and says "Claude answered!" when Claude Code finishes
a reply.

Built and tested on Ubuntu with GNOME on X11, using Python 3 and PyQt5.

## What you need

- A Linux desktop that uses X11. Wayland is not tested. Always-on-top and window position
  may not work there.
- Python 3.10 or newer.
- PyQt5, the library that draws the windows.
- Pillow and numpy, used once to cut the sprite sheet into frames.
- `xprop` (package `x11-utils`), optional. Without it the pet cannot hide itself for
  full-screen apps.

On Ubuntu:

```bash
sudo apt install python3-pyqt5 python3-pil python3-numpy x11-utils
```

## First run

The sprite sheet is in the repository: `assets/pikachu-sheet.jpg`. The program needs it cut
into single frames first. This is done once, and it also makes the icon for the desktop
launcher.

```bash
git clone https://github.com/ChrisB-Magic42/desktop-pet.git ~/projects/desktop-pet
```

```bash
cd ~/projects/desktop-pet
```

```bash
python3 tools/slice_sheet.py
```

```bash
python3 main.py
```

`slice_sheet.py` writes `assets/frames/` (36 small pictures) and `assets/icon.png`. Both are
generated, so git ignores them. Only the sheet itself is stored in the repository.

If you start `main.py` while the pet is already running, it prints "The pet is already
running" and stops. There is never more than one pet.

## Controls

| Action | What happens |
| --- | --- |
| Click | Happy dance |
| Double-click | Thunder Shock |
| Drag | Picks the pet up |
| Drag and let go while moving | Throws it. It bounces off the screen edges and the corners |
| Right-click | Menu with Settings, Hide pet and Quit |
| Tray icon | The same actions, in the top bar |

Clicks only count on the drawn Pikachu. The empty space around it passes clicks to the
windows behind.

## Settings

You can change settings in two ways. The settings window is the easy one.

### Using the settings window (recommended)

Right-click the pet (or use the tray icon) and choose Settings.

- Apply: changes the pet at once and saves the file.
- OK: the same as Apply, then closes the window.
- Restore Defaults: puts the default values in the window. Press Apply or OK to keep them.
- Cancel: closes the window and keeps the old values.

### Editing `settings.json` by hand

The file is here:

```
~/.config/desktop-pet/settings.json
```

It does not exist until you press Apply or OK in the settings window for the first time. Until
then the pet uses the defaults. To make it, open the settings window once and press OK.

Rules for editing it:

1. Stop the pet first (right-click, Quit). The pet reads the file only when it starts, and it
   writes the file when you press Apply or OK, which would overwrite your edit.
2. Keep it valid JSON. Use `true` and `false` in lower case, put text in double quotes, and
   leave no comma after the last line.
3. Start the pet again.

You cannot break it with a wrong value. A value that is missing, has the wrong type, or is out
of range is replaced with the default for that one setting (numbers outside the range are
moved to the nearest allowed number). If the whole file is not valid JSON, the pet starts with
all defaults. To reset everything, delete the file.

The default file looks like this:

```json
{
  "name": "Pika",
  "scale": 1.5,
  "speed": 90,
  "behaviour": "wander",
  "sleepy": true,
  "always_on_top": true,
  "hide_fullscreen": true,
  "break_minutes": 50,
  "bounciness": 70,
  "gravity": 100,
  "speech_bubbles": true,
  "autostart": false
}
```

| Key | Type | Default | Allowed values | What it does |
| --- | --- | --- | --- | --- |
| `name` | text | `"Pika"` | up to 20 characters | Shown when you hover over the pet and in the menus |
| `scale` | number | `1.5` | 0.5 to 4.0 | Size of the pet. 1.0 is the size of the sprite sheet |
| `speed` | whole number | `90` | 20 to 400 | Walking speed in pixels per second |
| `behaviour` | text | `"wander"` | `"wander"`, `"follow"`, `"stay"` | Wander walks around by itself. Follow walks toward your mouse. Stay never walks |
| `sleepy` | true or false | `true` | | Lets the pet fall asleep when nothing happens |
| `always_on_top` | true or false | `true` | | Keeps the pet above other windows |
| `hide_fullscreen` | true or false | `true` | | Hides the pet while a full-screen app is open (needs `xprop`) |
| `break_minutes` | whole number | `50` | 0 to 240 | Break reminder every N minutes. 0 turns it off |
| `bounciness` | whole number | `70` | 0 to 95 | Percent of speed kept after each bounce when thrown. 0 means no bounce |
| `gravity` | whole number | `100` | 25 to 300 | Pull when thrown, in percent of normal. Low is floaty, high is heavy |
| `speech_bubbles` | true or false | `true` | | Shows the speech bubble ("Claude answered!") |
| `autostart` | true or false | `false` | | Start the pet when you log in. See the warning below |

Warning about `autostart`: it is only a record of your choice. The setting that really starts
the pet at login is a file in `~/.config/autostart/`, and only the settings window creates or
removes it. Change this option in the settings window, not in the JSON file.

### Other files the pet writes

| File | What it holds | Safe to delete? |
| --- | --- | --- |
| `~/.config/desktop-pet/state.json` | Which screen the pet is on and where, so it starts there next time | Yes. It then starts at a random place |
| `~/.config/autostart/desktop-pet.desktop` | The "start when I log in" entry | Yes. Or untick the option in the settings window |
| `$XDG_RUNTIME_DIR/desktop-pet.sock` | A private socket for commands from other programs. Only your user can use it | Not needed. It is made again at each start |

To keep the files somewhere else (for example for a test), set the `DESKTOP_PET_CONFIG_DIR`
environment variable to another folder before starting the pet.

## Desktop icon

After the first run (so `assets/icon.png` exists), this makes an icon on your Desktop. It uses
the folder you run it from.

```bash
cd ~/projects/desktop-pet && printf '[Desktop Entry]\nType=Application\nName=Desktop Pet\nComment=Pikachu that walks on your screen\nExec=python3 %s/main.py\nPath=%s\nIcon=%s/assets/icon.png\nTerminal=false\nCategories=Utility;\n' "$PWD" "$PWD" "$PWD" > ~/Desktop/desktop-pet.desktop && chmod +x ~/Desktop/desktop-pet.desktop && gio set ~/Desktop/desktop-pet.desktop metadata::trusted true
```

If the icon shows a gear or a grey page, right-click it and choose Allow Launching. If you
move the project folder, make the icon again.

## Speech bubbles and commands from other programs

The pet listens for short commands. Send one with `tools/pet_notify.py`:

| Command | What the pet does | Bubble text |
| --- | --- | --- |
| `done` | Happy dance | Pika pika! Claude answered! |
| `fail` | Sad face | Pika... something failed. |
| `attention` | Surprised face | Pika? Claude needs you! |
| `break` | Runs to the middle of the screen and uses Thunder Shock | Pika! Time for a break! |

For example:

```bash
python3 ~/projects/desktop-pet/tools/pet_notify.py done
```

It exits with 0 when the pet got the command, 1 when the pet is not running, and 2 when the
word is not one of the four commands.

### Claude Code hooks

A hook is a command that Claude Code runs by itself when something happens. To make the pet
react to Claude, add these to the `hooks` section of `~/.claude/settings.json`. If you
already have a `Stop` or `Notification` entry, add these next to it. Do not replace it.

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/projects/desktop-pet/tools/pet_notify.py done || true",
            "timeout": 5
          }
        ]
      }
    ],
    "Notification": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/projects/desktop-pet/tools/pet_notify.py attention || true",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

- Change `~/projects/desktop-pet` if you cloned the project somewhere else.
- `|| true` means nothing breaks when the pet is not running.
- These hooks apply to every Claude Code session on your computer. The Stop hook runs after
  every reply, so the bubble appears often. Turn off "Show speech bubbles" in the settings if
  that is too much. The dance still happens.

## Troubleshooting

- Nothing appears: check that the pet is running (`pgrep -af main.py`) and that you are on
  X11 (`echo $XDG_SESSION_TYPE` should print `x11`).
- No tray icon: GNOME needs the AppIndicator extension for tray icons. Ubuntu has it on by
  default. The right-click menu on the pet always works.
- The pet disappears: it hides itself while a full-screen app is open. Turn off "Hide when a
  full-screen app is open" if you do not want that.
- "Missing frames" when starting: run `python3 tools/slice_sheet.py` first.
- Settings look wrong after a hand edit: delete `~/.config/desktop-pet/settings.json`.

## Tests

```bash
python3 -m unittest discover -s tests -t .
```

The tests cover settings checks, saving and loading, and the command socket. They do not open
any windows.

## Project layout

```
main.py                 starts the pet
pet/pet_window.py       the pet window: movement, drawing, mouse, reminders
pet/sprites.py          frames and animations
pet/settings_dialog.py  the settings window
pet/config.py           settings and position files, with checks
pet/bubble.py           the speech bubble
pet/tray.py             the tray icon
pet/commands.py         commands and socket client (no PyQt5 needed)
pet/control.py          the socket the pet listens on
pet/fullscreen.py       full-screen check using xprop
pet/autostart.py        the start-at-login file
tools/slice_sheet.py    cuts the sprite sheet into frames and makes the icon
tools/pet_notify.py     sends commands to the running pet
tests/                  unit tests
```

## About the pictures

Pikachu and the pictures of it belong to their owners. The sprite sheet is included here only
so that the project runs. It is not licensed for reuse, and you should not use it outside
your own computer. If you own the pictures and want the sheet removed, please open an issue
on this repository.
