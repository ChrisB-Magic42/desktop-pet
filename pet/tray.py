"""Tray icon with the pet's main actions."""
from PyQt5.QtWidgets import QApplication, QMenu, QSystemTrayIcon


class PetTray(QSystemTrayIcon):
    def __init__(self, pet):
        super().__init__(pet.sprites.icon(), pet)
        self.pet = pet
        self.menu = QMenu()
        self.toggle_action = self.menu.addAction("Hide pet", pet.toggle_user_hidden)
        self.menu.addAction("Settings...", pet.open_settings)
        self.menu.addSeparator()
        self.menu.addAction("Quit", QApplication.quit)
        self.setContextMenu(self.menu)
        self.setToolTip(pet.settings.name)
        self.activated.connect(self.on_activated)
        pet.visibility_changed.connect(self.on_visibility_changed)

    def on_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.pet.toggle_user_hidden()

    def on_visibility_changed(self, hidden):
        self.toggle_action.setText("Show pet" if hidden else "Hide pet")
