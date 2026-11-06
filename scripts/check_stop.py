"""Apply the stop rules of the final run (ledger "Final-run stop rules"). Exit code 3 and the reasons if the run must stop.

Usage: .venv/bin/python scripts/check_stop.py [--stats <json>] [--robustness <json>] [--redraw <json>] [--ambient <json>]
"""

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from synthrgbd.stop_rules import check_ambient, check_primary, check_redraw, check_s58  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    for name in ("stats", "robustness", "redraw", "ambient"):
        ap.add_argument(f"--{name}", type=Path)
    args = ap.parse_args()
    rules = {"stats": check_primary, "robustness": check_s58, "redraw": check_redraw, "ambient": check_ambient}
    why = []
    for name, rule in rules.items():
        path = getattr(args, name)
        if path is not None:
            why += rule(json.loads(path.read_text()))
    if why:
        print("STOP: present the options to the user")
        for w in why:
            print(" -", w)
        sys.exit(3)
    print("STOP_RULES_OK")


if __name__ == "__main__":
    main()
