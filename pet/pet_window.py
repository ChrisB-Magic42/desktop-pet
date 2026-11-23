"""The see-through window that shows, moves and animates the pet."""
import math
import random
import time
from collections import deque
from datetime import datetime

from PyQt5.QtCore import QElapsedTimer, QPoint, Qt, QTimer, QUrl, pyqtSignal
from PyQt5.QtGui import QCursor, QDesktopServices, QPainter
from PyQt5.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QWidget

from pet.autostart import set_autostart
from pet.bubble import LinkBubble, SpeechBubble
from pet.config import key_names, load_state, save_settings, save_state
from pet.fullscreen import active_window_is_fullscreen
from pet.screenshot import ScreenshotKeys
from pet.settings_dialog import SettingsDialog
from pet.sprites import ANIMATIONS
from pet.watcher import Watcher

TICK_MS = 33
GRAVITY = 2400
FLOOR_FRICTION = 0.8
STOP_SPEED = 250
MAX_THROW_SPEED = 3500
THROW_WINDOW = 0.1
THROW_IDLE_LIMIT = 0.05
DRAG_THRESHOLD = 4
ONE_SHOTS = ("happy", "attack", "dizzy", "sad", "alert")
REMINDER_STATES = ("remind_walk", "remind")
REMINDER_SECONDS = 45
FULLSCREEN_CHECK_MS = 2000
SAVE_POSITION_MS = 30000

# name: (weight, shortest seconds, longest seconds)
ACTIVITIES = {
    "idle": (3, 2, 5),
    "walk": (5, 2, 6),
    "sit": (2, 4, 9),
    "eat": (1, 3, 4),
    "sleep": (1.5, 10, 25),
}

# command from another program: (state, seconds), used when claude_jump is off
COMMAND_STATES = {
    "done": ("happy", 1.6),
    "fail": ("sad", 3.0),
    "attention": ("alert", 3.0),
}

# command from another program: the hop that matches its mood
COMMAND_HOPS = {"done": "hop", "fail": "hop_sad", "attention": "hop_alert"}

COMMAND_MESSAGES = {
    "done": "Pika pika! Claude answered!",
    "fail": "Pika... something failed.",
    "attention": "Pika? Claude needs you!",
    "break": "Pika! Time for a break!",
}
BUBBLE_SECONDS = 4.0
BREAK_BUBBLE_SECONDS = 8.0
DEMO_NOTICE = "example/demo: Example pull request (mentioned you)"
DEMO_URL = "https://github.com/notifications"
HOP_SPEED = 700
HOPS = 2
HOP_STATES = ("hop", "hop_sad", "hop_alert")
NOTICE_MAX_CHARS = 140
HISTORY_SIZE = 10
MENU_LABEL_CHARS = 60
SNOOZE_MINUTES = 60


class PetWindow(QWidget):
    visibility_changed = pyqtSignal(bool)
    unread_changed = pyqtSignal(bool)

    def __init__(self, settings, sprites):
        super().__init__()
        self.settings = settings
        self.sprites = sprites
        self.dialog = None
        self.tray = None
        self.state = "idle"
        self.state_left = 2.0
        self.anim_time = 0.0
        self.shown = None
        self.facing_right = True
        self.pos_x = self.pos_y = 0.0
        self.vx = self.vy = 0.0
        self.hops_left = 0
        self.history = deque(maxlen=HISTORY_SIZE)
        self.pending = deque(maxlen=HISTORY_SIZE)
        self.unread = 0
        self.drag_samples = deque(maxlen=8)
        self.rest_time = 0.0
        self.press_global = None
        self.grab_offset = QPoint()
        self.dragged = False
        self.window_flags = None
        self.user_hidden = False
        self.auto_hidden = False
        self.shot_hidden = False

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.bubble = SpeechBubble()
        self.link_bubble = LinkBubble()
        self.apply_settings(settings)
        self.pos_x, self.pos_y = self.start_position()
        self.move(round(self.pos_x), round(self.pos_y))

        self.clock = QElapsedTimer()
        self.clock.start()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(TICK_MS)

        self.break_timer = QTimer(self)
        self.break_timer.timeout.connect(self.start_reminder)
        self.restart_break_timer()

        self.save_timer = QTimer(self)
        self.save_timer.timeout.connect(self.save_position)
        self.save_timer.start(SAVE_POSITION_MS)

        self.fullscreen_timer = QTimer(self)
        self.fullscreen_timer.timeout.connect(self.check_fullscreen)
        if QApplication.platformName() == "xcb":
            self.fullscreen_timer.start(FULLSCREEN_CHECK_MS)

        self.shot_timer = QTimer(self)
        self.shot_timer.setSingleShot(True)
        self.shot_timer.timeout.connect(self.end_screenshot_hide)
        self.shots = ScreenshotKeys(self)
        self.shots.pressed.connect(self.begin_screenshot_hide)
        self.restart_screenshot_watch()
        QApplication.instance().aboutToQuit.connect(self.shots.stop)

        self.watcher = Watcher(settings, self)
        self.watcher.popup.connect(self.receive_notice)
        self.watcher.start()

    # Settings

    def apply_settings(self, settings):
        self.settings = settings
        if self.sprites.scale != settings.scale:
            self.sprites.rebuild(settings.scale)
        self.setFixedSize(*self.sprites.canvas)
        self.setToolTip(settings.name)
        if not settings.speech_bubbles:
            self.bubble.hide()
        if self.tray:
            self.tray.setToolTip(settings.name)
        flags = Qt.FramelessWindowHint | Qt.Tool
        if settings.always_on_top:
            flags |= Qt.WindowStaysOnTopHint
        if flags != self.window_flags:
            was_visible = self.isVisible()
            self.window_flags = flags
            self.setWindowFlags(flags)
            if was_visible:
                self.show()
        self.shown = None

    def change_settings(self, settings):
        old = self.settings
        self.apply_settings(settings)
        self.restart_break_timer()
        self.watcher.apply_settings(settings)
        self.restart_screenshot_watch()
        self.check_fullscreen()
        try:
            save_settings(settings)
            if settings.autostart != old.autostart:
                set_autostart(settings.autostart)
        except OSError as error:
            print(f"Could not save settings: {error}")

    def open_settings(self):
        if self.dialog is None:
            self.dialog = SettingsDialog(self.settings)
            self.dialog.applied.connect(self.change_settings)
        else:
            self.dialog.load(self.settings)
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()

    # Screens and position

    def current_screen(self):
        """The screen the pet is standing on, or the nearest one."""
        centre = QPoint(round(self.pos_x + self.width() / 2), round(self.pos_y + self.height() / 2))
        screen = QApplication.screenAt(centre)
        if screen:
            return screen
        return min(QApplication.screens(), key=lambda s: (s.geometry().center() - centre).manhattanLength())

    def row_screens(self):
        """The screens that share a horizontal band with the screen the pet is on."""
        span = self.current_screen().geometry()
        return [s for s in QApplication.screens() if s.geometry().top() <= span.bottom() and s.geometry().bottom() >= span.top()]

    def walk_range(self):
        """Leftmost and rightmost x across the screens in the same row as the pet."""
        row = self.row_screens()
        low = min(s.availableGeometry().left() for s in row)
        high = max(s.availableGeometry().right() + 1 for s in row) - self.width()
        return low, max(low, high)

    def top_limit(self):
        return float(min(s.availableGeometry().top() for s in self.row_screens()))

    def floor_y(self):
        return float(self.current_screen().availableGeometry().bottom() + 1 - self.height())

    def clamp_x(self):
        low, high = self.walk_range()
        self.pos_x = min(max(self.pos_x, low), high)

    def step(self, distance, bounce):
        """Move sideways in the facing direction, turning round at the edge of the screens."""
        low, high = self.walk_range()
        self.pos_x += distance if self.facing_right else -distance
        if self.pos_x <= low or self.pos_x >= high:
            self.pos_x = min(max(self.pos_x, low), high)
            if bounce:
                self.facing_right = self.pos_x <= low

    def start_position(self):
        saved = load_state()
        screen = next((s for s in QApplication.screens() if saved and s.name() == saved["screen"]), None)
        screen = screen or QApplication.primaryScreen()
        area = screen.availableGeometry()
        if saved and screen.name() == saved["screen"]:
            x = screen.geometry().left() + saved["offset"]
        else:
            x = random.randint(area.left(), max(area.left(), area.right() - self.width()))
        x = min(max(x, area.left()), max(area.left(), area.right() + 1 - self.width()))
        return float(x), float(area.bottom() + 1 - self.height())

    def save_position(self):
        screen = self.current_screen()
        try:
            save_state({"screen": screen.name(), "offset": round(self.pos_x - screen.geometry().left())})
        except OSError as error:
            print(f"Could not save position: {error}")

    # Visibility

    def refresh_visibility(self):
        wanted = not (self.user_hidden or self.auto_hidden or self.shot_hidden)
        if wanted != self.isVisible():
            self.setVisible(wanted)
        if not wanted:
            self.bubble.hide()
            self.link_bubble.suspend()

    def suppressed(self):
        """True while a full-screen app is open or a screenshot is being taken."""
        return self.auto_hidden or self.shot_hidden

    def toggle_user_hidden(self):
        self.user_hidden = not self.user_hidden
        if self.user_hidden:
            self.link_bubble.clear()
        self.refresh_visibility()
        self.visibility_changed.emit(self.user_hidden)

    def check_fullscreen(self):
        hide = self.settings.hide_fullscreen and self.fullscreen_timer.isActive() and active_window_is_fullscreen()
        if hide != self.auto_hidden:
            self.auto_hidden = hide
            self.refresh_visibility()
            if not hide:
                self.resume_messages()

    # Screenshots

    def restart_screenshot_watch(self):
        """Watch the screenshot keys again, or stop watching when hiding is switched off."""
        self.shots.stop()
        if self.settings.hide_for_screenshots and QApplication.platformName() == "xcb":
            self.shots.start(key_names(self.settings.screenshot_keys))

    def begin_screenshot_hide(self):
        """A screenshot key went down. Hide at once, because the picture is taken a few milliseconds later."""
        if not self.settings.hide_for_screenshots:
            return
        self.shot_hidden = True
        self.refresh_visibility()
        self.shot_timer.start(self.settings.screenshot_hide_seconds * 1000)

    def end_screenshot_hide(self):
        self.shot_hidden = False
        self.refresh_visibility()
        self.resume_messages()

    def resume_messages(self):
        """Show the messages that waited while the pet was hidden by a full-screen app or a screenshot."""
        if self.suppressed() or self.user_hidden:
            return
        self.flush_pending()
        self.link_bubble.resume()

    # Break reminder and commands from other programs

    def restart_break_timer(self):
        self.break_timer.stop()
        if self.settings.break_minutes > 0:
            self.break_timer.start(self.settings.break_minutes * 60 * 1000)

    def notify(self, title, text):
        if self.tray:
            self.tray.showMessage(title, text, QSystemTrayIcon.Information, 10000)

    def start_reminder(self):
        if self.suppressed():
            return
        self.notify("Time for a break", "Stand up, stretch and rest your eyes.")
        self.say(COMMAND_MESSAGES["break"], BREAK_BUBBLE_SECONDS)
        if not self.user_hidden and self.state not in ("grabbed", "fall"):
            self.teleport_to_main_screen()
            self.set_state("remind_walk", REMINDER_SECONDS, restart=True)

    def handle_command(self, name):
        if name == "break":
            self.start_reminder()
            return
        if name == "demo":
            self.receive_notice(DEMO_NOTICE, DEMO_URL)
            return
        if self.settings.claude_jump:
            self.jump_to_main_screen(COMMAND_HOPS[name])
        elif self.state not in ("grabbed", "fall") + REMINDER_STATES:
            state, seconds = COMMAND_STATES[name]
            self.set_state(state, seconds, restart=True)
        self.say(COMMAND_MESSAGES[name], BUBBLE_SECONDS)

    def receive_notice(self, text, url):
        """A Harvest or GitHub message arrived. Keep it in the history, and show it unless a full-screen app is open."""
        self.history.append((datetime.now(), text, url))
        self.unread += 1
        self.unread_changed.emit(True)
        if self.suppressed():
            self.pending.append((text, url))
        else:
            self.show_notice(text, url)

    def flush_pending(self):
        """Show the messages that arrived while a full-screen app was open."""
        while self.pending:
            self.show_notice(*self.pending.popleft())

    def mark_read(self):
        if self.unread:
            self.unread = 0
            self.unread_changed.emit(False)

    def add_notice_actions(self, menu):
        """Add the Harvest snooze item and the list of recent messages to a menu."""
        checker = self.watcher.checker
        if self.settings.watch_harvest and checker.harvest:
            if checker.snoozed():
                until = checker.snoozed_until.strftime("%H:%M")
                menu.addAction(f"Harvest snoozed until {until} (click to cancel)", checker.cancel_snooze)
            else:
                menu.addAction(f"Snooze Harvest for {SNOOZE_MINUTES // 60} hour", lambda: checker.snooze(SNOOZE_MINUTES))
        recent = menu.addMenu("Recent messages")
        if not self.history:
            recent.addAction("No messages yet").setEnabled(False)
        for stamp, text, url in reversed(self.history):
            short = text if len(text) <= MENU_LABEL_CHARS else text[: MENU_LABEL_CHARS - 3].rstrip() + "..."
            action = recent.addAction(f"{stamp:%H:%M}  {short}")
            action.setEnabled(bool(url))
            action.triggered.connect(lambda _checked=False, link=url: QDesktopServices.openUrl(QUrl(link)))

    def show_notice(self, text, url):
        """The pet says a Harvest or GitHub notice in a clickable bubble and hops. A hidden pet uses the tray."""
        if len(text) > NOTICE_MAX_CHARS:
            text = text[: NOTICE_MAX_CHARS - 3].rstrip() + "..."
        text = f"Pika! {text}"
        if self.user_hidden:
            self.notify(self.settings.name, text)
            return
        self.jump_to_main_screen()
        self.link_bubble.pop_up(text, url)
        self.follow_bubble()

    def jump_to_main_screen(self, hop="hop"):
        """Teleport to the main screen and hop, so a message is not missed. Not while held or running to a break."""
        if self.user_hidden or self.suppressed() or self.state == "grabbed":
            return
        self.teleport_to_main_screen()
        if self.state not in REMINDER_STATES:
            self.start_hop(hop)

    def teleport_to_main_screen(self):
        """Move to the middle of the main screen at once, so the notice is not missed on another screen."""
        main = QApplication.primaryScreen()
        if self.current_screen() == main:
            return
        area = main.availableGeometry()
        self.pos_x = area.center().x() - self.width() / 2
        self.pos_y = float(area.bottom() + 1 - self.height())
        self.vx = self.vy = 0.0
        self.move(round(self.pos_x), round(self.pos_y))
        self.save_position()

    # Speech bubble

    def say(self, text, seconds):
        if not self.settings.speech_bubbles or self.user_hidden or self.suppressed():
            return
        self.bubble.say(text, seconds)
        self.follow_bubble()

    def follow_bubble(self):
        """Keep the bubbles just above the top of the drawn pet, the link bubble first and the other above it."""
        if not (self.bubble.isVisible() or self.link_bubble.isVisible()):
            return
        pixmap = self.sprites.pixmap(self.current_frame(), self.facing_right)
        anchor_x = self.pos_x + self.width() / 2
        bottom = self.pos_y + self.height() - pixmap.height() - 2
        area = self.current_screen().availableGeometry()
        if self.link_bubble.isVisible():
            self.link_bubble.place(anchor_x, bottom, area)
            bottom = self.link_bubble.y() - 4
        if self.bubble.isVisible():
            self.bubble.place(anchor_x, bottom, area)

    # Hop

    def start_hop(self, kind="hop"):
        self.vy = -HOP_SPEED
        self.hops_left = HOPS
        self.set_state(kind, restart=True)

    def hop(self, dt):
        """Jump up and down on the spot, HOPS times."""
        self.vy += GRAVITY * self.settings.gravity / 100 * dt
        self.pos_y += self.vy * dt
        floor = self.floor_y()
        if self.pos_y >= floor and self.vy > 0:
            self.pos_y = floor
            self.hops_left -= 1
            if self.hops_left > 0:
                self.vy = -HOP_SPEED
            else:
                self.vy = 0.0
                self.set_state("idle", 1.0)

    # State machine

    def set_state(self, name, seconds=0.0, restart=False):
        self.state_left = seconds
        if name != self.state or restart:
            self.state = name
            self.anim_time = 0.0

    def allowed(self, name):
        if name == "walk":
            return self.settings.behaviour == "wander"
        if name == "sleep":
            return self.settings.sleepy
        return True

    def pick_activity(self):
        names = [name for name in ACTIVITIES if self.allowed(name)]
        name = random.choices(names, [ACTIVITIES[n][0] for n in names])[0]
        _, low, high = ACTIVITIES[name]
        if name == "walk":
            self.facing_right = random.random() < 0.5
        self.set_state(name, random.uniform(low, high))

    def wander(self, dt):
        self.state_left -= dt
        if self.state == "walk":
            self.step(self.settings.speed * dt, bounce=True)
        if self.state_left <= 0:
            self.pick_activity()

    def follow(self, dt):
        gap = QCursor.pos().x() - self.width() / 2 - self.pos_x
        if abs(gap) < self.width() * 0.6:
            self.rest_time += dt
            if self.settings.sleepy and self.rest_time > 20:
                self.set_state("sleep")
            elif self.rest_time > 4:
                self.set_state("sit")
            else:
                self.set_state("idle")
            return
        self.rest_time = 0.0
        self.facing_right = gap > 0
        fast = abs(gap) > 500
        self.set_state("dash" if fast else "walk")
        self.step(self.settings.speed * (2 if fast else 1) * dt, bounce=False)

    def remind(self, dt):
        """Run to the middle of the screen, then shock until clicked or timed out."""
        self.state_left -= dt
        if self.state_left <= 0:
            self.set_state("idle", 1.0)
            return
        gap = self.current_screen().availableGeometry().center().x() - self.width() / 2 - self.pos_x
        if abs(gap) > 8:
            self.facing_right = gap > 0
            self.step(self.settings.speed * 2 * dt, bounce=False)
            self.set_state("remind_walk", self.state_left)
        else:
            self.set_state("remind", self.state_left)

    def throw_velocity(self):
        """Speed of the window over the last moments of the drag, in pixels per second."""
        now = time.monotonic()
        recent = [s for s in self.drag_samples if now - s[0] <= THROW_WINDOW]
        if len(recent) < 2 or now - recent[-1][0] > THROW_IDLE_LIMIT:
            return 0.0, 0.0
        (t0, x0, y0), (t1, x1, y1) = recent[0], recent[-1]
        if t1 <= t0:
            return 0.0, 0.0
        vx, vy = (x1 - x0) / (t1 - t0), (y1 - y0) / (t1 - t0)
        speed = math.hypot(vx, vy)
        if speed > MAX_THROW_SPEED:
            vx, vy = vx * MAX_THROW_SPEED / speed, vy * MAX_THROW_SPEED / speed
        return vx, vy

    def land(self):
        self.vx = self.vy = 0.0
        self.set_state("dizzy", 0.8)
        self.save_position()

    def fall(self, dt):
        """Thrown flight: gravity, bouncing off the screen edges, then landing."""
        bounce = self.settings.bounciness / 100
        self.vy += GRAVITY * self.settings.gravity / 100 * dt
        self.pos_x += self.vx * dt
        self.pos_y += self.vy * dt
        low, high = self.walk_range()
        if self.pos_x < low:
            self.pos_x, self.vx = low, abs(self.vx) * bounce
        elif self.pos_x > high:
            self.pos_x, self.vx = high, -abs(self.vx) * bounce
        top = self.top_limit()
        if self.pos_y < top:
            self.pos_y, self.vy = top, abs(self.vy) * bounce
        floor = self.floor_y()
        if self.pos_y >= floor and self.vy >= 0:
            self.pos_y = floor
            if self.vy > STOP_SPEED:
                self.vy *= -bounce
                self.vx *= FLOOR_FRICTION
            else:
                self.land()
        if abs(self.vx) > 50:
            self.facing_right = self.vx > 0

    def tick(self):
        dt = min(self.clock.restart() / 1000.0, 0.1)
        if self.state == "grabbed":
            self.advance_animation(dt)
            self.follow_bubble()
            return
        if self.state == "fall":
            self.fall(dt)
        elif self.state in HOP_STATES:
            self.hop(dt)
        elif self.state in ONE_SHOTS:
            self.state_left -= dt
            if self.state_left <= 0:
                self.set_state("idle", 1.0)
        elif self.state in REMINDER_STATES:
            self.remind(dt)
        elif self.settings.behaviour == "follow":
            self.follow(dt)
        else:
            self.wander(dt)
        self.clamp_x()
        if self.state != "fall" and self.state not in HOP_STATES:
            self.pos_y = self.floor_y()
        self.move(round(self.pos_x), round(self.pos_y))
        self.advance_animation(dt)
        self.follow_bubble()

    # Drawing

    def current_frame(self):
        animation = ANIMATIONS[self.state]
        index = int(self.anim_time * animation.fps)
        if animation.loop:
            index %= len(animation.frames)
        else:
            index = min(index, len(animation.frames) - 1)
        return animation.frames[index]

    def draw_offset(self, pixmap):
        return QPoint((self.width() - pixmap.width()) // 2, self.height() - pixmap.height())

    def advance_animation(self, dt):
        self.anim_time += dt
        shown = (self.current_frame(), self.facing_right)
        if shown != self.shown:
            self.shown = shown
            pixmap = self.sprites.pixmap(*shown)
            self.setMask(self.sprites.region(*shown).translated(self.draw_offset(pixmap)))
            self.update()

    def paintEvent(self, _event):
        pixmap = self.sprites.pixmap(self.current_frame(), self.facing_right)
        painter = QPainter(self)
        painter.drawPixmap(self.draw_offset(pixmap), pixmap)

    # Mouse

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        self.press_global = event.globalPos()
        self.grab_offset = event.globalPos() - self.frameGeometry().topLeft()
        self.dragged = False
        self.drag_samples.clear()

    def mouseMoveEvent(self, event):
        if self.press_global is None or not event.buttons() & Qt.LeftButton:
            return
        if not self.dragged:
            if (event.globalPos() - self.press_global).manhattanLength() < DRAG_THRESHOLD:
                return
            self.dragged = True
            self.set_state("grabbed")
        top_left = event.globalPos() - self.grab_offset
        self.pos_x, self.pos_y = float(top_left.x()), float(top_left.y())
        self.drag_samples.append((time.monotonic(), self.pos_x, self.pos_y))
        self.move(top_left)

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton or self.press_global is None:
            return
        self.press_global = None
        if self.dragged:
            self.dragged = False
            self.vx, self.vy = self.throw_velocity()
            self.set_state("fall")
        else:
            self.set_state("happy", 1.6, restart=True)

    def mouseDoubleClickEvent(self, event):
        self.press_global = None
        self.set_state("attack", 1.4, restart=True)

    def contextMenuEvent(self, event):
        menu = QMenu()
        menu.addAction(self.settings.name).setEnabled(False)
        menu.addSeparator()
        self.mark_read()
        menu.addAction("Settings...", self.open_settings)
        self.add_notice_actions(menu)
        menu.addAction("Hide pet", self.toggle_user_hidden)
        menu.addAction("Quit", QApplication.quit)
        menu.exec_(event.globalPos())
