"""Start the desktop pet."""
import signal
import sys

from PyQt5.QtWidgets import QApplication, QSystemTrayIcon

from pet.commands import is_running
from pet.config import load_settings
from pet.control import ControlServer
from pet.pet_window import PetWindow
from pet.sprites import SpriteSet
from pet.tray import PetTray


def main():
    if is_running():
        print("The pet is already running.")
        return 0
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    settings = load_settings()
    try:
        sprites = SpriteSet(settings.scale)
    except FileNotFoundError as error:
        print(error)
        return 1
    pet = PetWindow(settings, sprites)
    control = ControlServer(pet)
    control.command.connect(pet.handle_command)
    if QSystemTrayIcon.isSystemTrayAvailable():
        pet.tray = PetTray(pet)
        pet.tray.show()
    app.aboutToQuit.connect(pet.save_position)
    pet.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
