"""List connected adb devices (helper; adb.py has no CLI entry point)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import adb  # noqa: E402


def main() -> None:
    for d in adb.list_devices():
        print(d)


if __name__ == "__main__":
    main()
