import socket
import tempfile
import threading
import unittest
from pathlib import Path

from pet.commands import COMMANDS, is_running, send


class Listener:
    """A tiny stand-in for the pet that records what it receives."""

    def __init__(self, path):
        self.received = b""
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server.bind(str(path))
        self.server.listen(1)
        self.thread = threading.Thread(target=self.serve)
        self.thread.start()

    def serve(self):
        connection, _ = self.server.accept()
        with connection:
            connection.settimeout(1)
            try:
                self.received = connection.recv(64)
            except socket.timeout:
                pass

    def close(self):
        self.thread.join()
        self.server.close()


class CommandsTest(unittest.TestCase):
    def test_nothing_listening(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "pet.sock"
            self.assertFalse(is_running(path))
            self.assertFalse(send("done", path))

    def test_command_reaches_listener(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "pet.sock"
            listener = Listener(path)
            self.assertTrue(send("done", path))
            listener.close()
            self.assertEqual(listener.received, b"done\n")

    def test_running_check_sends_nothing(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "pet.sock"
            listener = Listener(path)
            self.assertTrue(is_running(path))
            listener.close()
            self.assertEqual(listener.received, b"")

    def test_known_commands(self):
        self.assertEqual(set(COMMANDS), {"done", "fail", "attention", "break"})


if __name__ == "__main__":
    unittest.main()
