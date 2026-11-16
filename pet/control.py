"""Listen for commands from other programs on a private local socket."""
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtNetwork import QLocalServer

from pet.commands import COMMANDS, socket_path

MAX_BYTES = 64


class ControlServer(QObject):
    command = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        path = socket_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        self.server = QLocalServer(self)
        self.server.setSocketOptions(QLocalServer.UserAccessOption)
        QLocalServer.removeServer(str(path))
        if not self.server.listen(str(path)):
            print(f"Could not listen on {path}: {self.server.errorString()}")
        self.server.newConnection.connect(self.accept)

    def accept(self):
        while self.server.hasPendingConnections():
            connection = self.server.nextPendingConnection()
            connection.readyRead.connect(lambda c=connection: self.read(c))
            connection.disconnected.connect(connection.deleteLater)
            if connection.bytesAvailable():
                self.read(connection)

    def read(self, connection):
        text = bytes(connection.read(MAX_BYTES)).decode("utf-8", "ignore")
        for line in text.splitlines():
            if line.strip() in COMMANDS:
                self.command.emit(line.strip())
        connection.disconnectFromServer()
