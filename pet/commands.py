"""Commands other programs can send to the running pet (standard library only)."""
import os
import socket
from pathlib import Path

COMMANDS = ("done", "fail", "attention", "break", "demo")


def socket_path():
    override = os.environ.get("DESKTOP_PET_SOCKET")
    if override:
        return Path(override)
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    base = Path(runtime) if runtime else Path.home() / ".config" / "desktop-pet"
    return base / "desktop-pet.sock"


def send(command, path=None):
    """Send one command to the pet, or only connect when command is None."""
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.settimeout(0.5)
    try:
        client.connect(str(path or socket_path()))
        if command:
            client.sendall(command.encode() + b"\n")
    except OSError:
        return False
    finally:
        client.close()
    return True


def is_running(path=None):
    return send(None, path)
