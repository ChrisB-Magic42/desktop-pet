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
- `xinput` (package `xinput`), optional. Without it the pet cannot hide itself for screenshots.

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
  "autostart": false,
  "watch_harvest": true,
  "watch_github": true,
  "github_participating": true,
  "claude_jump": true,
  "check_minutes": 2,
  "hide_for_screenshots": true,
  "screenshot_keys": "Print,F9",
  "screenshot_hide_seconds": 10
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
| `watch_harvest` | true or false | `true` | | Popup when no Harvest timer is running. Needs the credentials file, see below |
| `watch_github` | true or false | `true` | | Popup for each new GitHub notification. Needs the `gh` command, logged in |
| `github_participating` | true or false | `true` | | Only notifications where you are involved: mentions, assignments, review requests, replies |
| `claude_jump` | true or false | `true` | | Claude messages (answered, failed, needs you) also teleport the pet to the main screen and make it hop. When off, they only change its face |
| `check_minutes` | whole number | `2` | 1 to 60 | How often Harvest and GitHub are checked |
| `hide_for_screenshots` | true or false | `true` | | Hide the pet when a screenshot key is pressed. Needs `xinput` |
| `screenshot_keys` | text | `"Print,F9"` | up to 10 key names, separated by commas | The keys that start a screenshot. Any press of them counts, with or without Shift, Alt or Ctrl |
| `screenshot_hide_seconds` | whole number | `10` | 1 to 60 | How long the pet stays hidden after the key press |

Warning about `autostart`: it is only a record of your choice. The setting that really starts
the pet at login is a file in `~/.config/autostart/`, and only the settings window creates or
removes it. Change this option in the settings window, not in the JSON file.

### Other files the pet writes

| File | What it holds | Safe to delete? |
| --- | --- | --- |
| `~/.config/desktop-pet/state.json` | Which screen the pet is on and where, so it starts there next time | Yes. It then starts at a random place |
| `~/.config/autostart/desktop-pet.desktop` | The "start when I log in" entry | Yes. Or untick the option in the settings window |
| `~/.config/desktop-pet/seen.json` | The GitHub notifications already announced, so a restart does not repeat them | Yes. The pet then only records what is unread and shows nothing |
| `~/.config/desktop-pet/harvest.json` | Your Harvest account ID and token, made by you. See the Harvest setup | Yes. The Harvest check then switches itself off |
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
| `done` | Teleports to the main screen and hops happily | Pika pika! Claude answered! |
| `fail` | Teleports to the main screen and hops with a sad face | Pika... something failed. |
| `attention` | Teleports to the main screen and hops with a surprised face | Pika? Claude needs you! |
| `break` | Teleports to the main screen, runs to the middle and uses Thunder Shock | Pika! Time for a break! |
| `demo` | Hops and shows an example GitHub message. Click it to open your GitHub notifications | Pika! example/demo: Example pull request (mentioned you) |

For example:

```bash
python3 ~/projects/desktop-pet/tools/pet_notify.py done
```

It exits with 0 when the pet got the command, 1 when the pet is not running, and 2 when the
word is not one of the five commands.

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

## Harvest and GitHub popups

Every `check_minutes` minutes (default 2) the pet checks two things in the background. When
there is something to tell you, the pet teleports to the middle of your main screen (the one
set as primary in your display settings, if it was on another screen), hops twice and says it
in a speech bubble above its head for 10 seconds. It stays on the main screen afterwards. Click the bubble to open its link. Messages wait in a queue if several
arrive together.

- Harvest: "Pika! No Harvest timer is running", linking to your Harvest time page. When it
  repeats, and during which hours, is decided by `should_remind` in `pet/reminders.py`
  (weekdays, 09:00 to 17:30, every 10 minutes).
- Harvest, forgotten timer: if a timer has run for 8 hours or more, Pika says so, and repeats
  every hour until you stop it. This works at any day and hour. The limits are in
  `pet/reminders.py` too.
- Snooze: right-click Pika (or use the tray menu) and choose "Snooze Harvest for 1 hour" when
  you are at lunch or in a meeting. It silences both Harvest messages. The same item cancels it.
- GitHub: one message for each new notification, linking to the issue or pull request. The
  first check after the pet starts only records what is already unread, so old notifications
  are not announced. If more than 3 arrive at once, you get one message that links to your
  inbox.

Messages are not lost. The list of unread GitHub notifications is saved, so ones that arrive
while the pet is switched off are announced when it starts. Messages that arrive while a
full-screen app is open wait, and are shown when the app closes. The last 10 messages are kept
under "Recent messages" in the right-click menu and the tray menu, and you can click one to open
its link. The tray icon shows a red dot while there are messages you have not looked at.

These bubbles show even when "Show speech bubbles" is off, because that option is only for the
Claude messages. If you hide the pet from the menu, the message comes as a tray notification
instead, without a link.

### GitHub setup

Install the GitHub command line tool (`gh`) and log in with `gh auth login`. The login needs
the `repo` or `notifications` permission. Nothing else is needed.

### Harvest setup

The pet cannot use your Claude Code connection to Harvest, so it needs its own key.

1. Go to https://id.getharvest.com/developers and create a personal access token.
2. Note the token and the account ID shown next to it.
3. Make the file `~/.config/desktop-pet/harvest.json` with both values:

```json
{
  "account_id": "123456",
  "token": "your-token-here"
}
```

4. Make the file private, because the token works like a password:

```bash
chmod 600 ~/.config/desktop-pet/harvest.json
```

Instead of putting the token in the file, you can keep it in the system keyring. Install the
tool once, then store the token (it asks you to type it, so it never appears in a file). Leave
`token` out of `harvest.json` and keep only the `account_id`:

```bash
sudo apt install libsecret-tools
```

```bash
secret-tool store --label="desktop-pet Harvest token" application desktop-pet service harvest
```

The pet prints a warning at start if other users can read `harvest.json`.

Without this file, the pet prints "Harvest check is off" when it starts, and the GitHub check
still works. Never commit this file.

## Hiding while you take screenshots

Pika hides when you press a screenshot key, so he is not in the picture. The default keys are
Print and F9. That covers the GNOME screenshot tool (Print, F9, Alt+Print) and a Flameshot
shortcut such as Shift+F9, because any press of the key counts, with or without Shift, Alt or
Ctrl. He comes back after `screenshot_hide_seconds` (10 by default). A message that arrives
meanwhile waits, and is shown when he returns.

How it works: the pet watches key presses with `xinput`, a tool that reports keyboard events.
It hides within about 10 milliseconds of the key press. Screenshot tools take the picture a
little after the key press, so this is fast but not guaranteed.

Limits:

- Only the keys in `screenshot_keys` count. If you use another shortcut, add its key name, for
  example `"Print,F9,F10"`. The names are the ones the `xev` tool shows.
- Any other use of those keys also hides him. F9 in another program does the same.
- Screen recordings are not covered, because the pet cannot know when they end.
- It works on X11 only, and needs `xinput`. Without it the pet prints a message at start and
  carries on.

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

The tests cover settings checks, saving and loading, the command socket, and the Harvest and
GitHub checks (with fake answers, so they need no network). They do not show any windows. The
pet window tests need the frames from `tools/slice_sheet.py`, and are skipped without them.

## Project layout

```
main.py                 starts the pet
pet/pet_window.py       the pet window: movement, drawing, mouse, reminders
pet/sprites.py          frames and animations
pet/settings_dialog.py  the settings window
pet/config.py           settings and position files, with checks
pet/bubble.py           the speech bubble, and the clickable one for Harvest and GitHub messages
pet/tray.py             the tray icon, its menu and the unread dot
pet/commands.py         commands and socket client (no PyQt5 needed)
pet/control.py          the socket the pet listens on
pet/fullscreen.py       full-screen check using xprop
pet/autostart.py        the start-at-login file
pet/watcher.py          runs the checks on a background thread every few minutes
pet/checks.py           one round of checks (Harvest timer, GitHub notifications)
pet/harvest.py          asks Harvest if a timer is running
pet/github.py           reads GitHub notifications through gh
pet/screenshot.py       watches the screenshot keys so the pet can hide
pet/reminders.py        the rules for when to say that no timer is running, or one ran too long
tools/slice_sheet.py    cuts the sprite sheet into frames and makes the icon
tools/pet_notify.py     sends commands to the running pet
tests/                  unit tests
```

## About the pictures

Pikachu and the pictures of it belong to their owners. The sprite sheet is included here only
so that the project runs. It is not licensed for reuse, and you should not use it outside
your own computer. If you own the pictures and want the sheet removed, please open an issue
on this repository.
