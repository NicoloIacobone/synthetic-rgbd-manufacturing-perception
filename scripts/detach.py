"""Start a long job fully detached from this session, so it survives the end of the session, with the Mac kept awake.

Usage: .venv/bin/python scripts/detach.py <log> -- <command> [args...]
New session, stdin closed, output to <log> (appended), pid written to <log>.pid. Uses caffeinate where it exists (macOS): it stops
idle and system sleep on AC power, but not sleep on closing the lid.
"""

import shutil
import subprocess
import sys
from pathlib import Path


def main():
    log, cmd = Path(sys.argv[1]), sys.argv[3:]
    if sys.argv[2] != "--" or not cmd:
        raise SystemExit(__doc__)
    log.parent.mkdir(parents=True, exist_ok=True)
    prefix = ["caffeinate", "-ims"] if shutil.which("caffeinate") else []
    with open(log, "ab") as out:
        p = subprocess.Popen([*prefix, *cmd], stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
    Path(f"{log}.pid").write_text(str(p.pid))
    print(p.pid)


if __name__ == "__main__":
    main()
