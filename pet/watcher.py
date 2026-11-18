"""Run the checks every few minutes on a background thread, so the pet never freezes."""
import threading

from PyQt5.QtCore import QObject, QTimer, pyqtSignal

from pet.checks import Checker


class Watcher(QObject):
    popup = pyqtSignal(str, object)
    finished = pyqtSignal()

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.checker = Checker.create(settings)
        self.running = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check)
        self.finished.connect(self.on_finished)
        self.apply_settings(settings)

    def apply_settings(self, settings):
        self.checker.settings = settings
        self.timer.start(settings.check_minutes * 60 * 1000)

    def start(self):
        QTimer.singleShot(0, self.check)

    def check(self):
        if self.running:
            return
        self.running = True
        threading.Thread(target=self.work, daemon=True).start()

    def work(self):
        try:
            for text, url in self.checker.poll():
                self.popup.emit(text, url)
        finally:
            self.finished.emit()

    def on_finished(self):
        self.running = False
