"""Tray icon with the pet's main actions."""
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QIcon, QPainter, QPen
from PyQt5.QtWidgets import QApplication, QMenu, QSystemTrayIcon

ICON_SIZE = 64
DOT_SIZE = 26


def icon_with_dot(icon):
    """The icon with a red dot in the corner, shown while there are unread messages."""
    pixmap = icon.pixmap(ICON_SIZE, ICON_SIZE)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(QPen(QColor("#ffffff"), 3))
    painter.setBrush(QColor("#e02424"))
    painter.drawEllipse(ICON_SIZE - DOT_SIZE - 2, 2, DOT_SIZE, DOT_SIZE)
    painter.end()
    return QIcon(pixmap)


class PetTray(QSystemTrayIcon):
    def __init__(self, pet):
        self.normal_icon = pet.sprites.icon()
        self.unread_icon = icon_with_dot(self.normal_icon)
        super().__init__(self.normal_icon, pet)
        self.pet = pet
        self.menu = QMenu()
        self.menu.aboutToShow.connect(self.refresh_menu)
        self.setContextMenu(self.menu)
        self.setToolTip(pet.settings.name)
        self.activated.connect(self.on_activated)
        pet.unread_changed.connect(self.set_unread)
        self.refresh_menu()

    def refresh_menu(self):
        """Build the menu again each time it opens, so the snooze and recent messages are current."""
        self.pet.mark_read()
        self.menu.clear()
        self.menu.addAction("Show pet" if self.pet.user_hidden else "Hide pet", self.pet.toggle_user_hidden)
        self.menu.addAction("Settings...", self.pet.open_settings)
        self.pet.add_notice_actions(self.menu)
        self.menu.addSeparator()
        self.menu.addAction("Quit", QApplication.quit)

    def set_unread(self, unread):
        self.setIcon(self.unread_icon if unread else self.normal_icon)

    def on_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.pet.toggle_user_hidden()
