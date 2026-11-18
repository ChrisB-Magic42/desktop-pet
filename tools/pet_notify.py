"""Send a command to the running pet: done, fail, attention, break or demo."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pet.commands import COMMANDS, send  # noqa: E402


def main(argv):
    if len(argv) != 2 or argv[1] not in COMMANDS:
        print(f"Usage: pet_notify.py {{{'|'.join(COMMANDS)}}}", file=sys.stderr)
        return 2
    if not send(argv[1]):
        print("The pet is not running.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
