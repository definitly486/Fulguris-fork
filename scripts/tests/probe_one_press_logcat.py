"""
Probe: one action-key long press, with logcat capture, to see what the app does
when the page's DOM log stays empty.

Usage:
    python -u scripts/tests/probe_one_press_logcat.py --device 192.168.178.67:5555
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import adb  # noqa: E402
import cursor_tests  # noqa: E402
import framework  # noqa: E402
from framework import keys  # noqa: E402

SERIAL = "192.168.178.67:5555"


def _arg(name: str, default: str) -> str:
    args = sys.argv[1:]
    if name in args:
        return args[args.index(name) + 1]
    return default


def main() -> None:
    serial = _arg("--device", SERIAL)
    device = framework.AndroidDevice(serial)
    device.settle()

    cursor_tests._ensure_server()
    cursor_tests._load_page(device, "longpress_log.html")
    time.sleep(1.0)
    print("before: cursor overlay =", cursor_tests._overlay_present(device))
    print("before: title =", repr(cursor_tests._title(device).strip()))
    cursor_tests._toggle(device)
    time.sleep(1.0)
    print("after toggle: cursor overlay =", cursor_tests._overlay_present(device))

    adb._adb(serial, ["logcat", "-c"], timeout=30)
    device.key_hold(keys.DPAD_CENTER, 1500)
    time.sleep(1.5)
    print("after press: title =", repr(cursor_tests._title(device).strip()))

    log = adb._adb(serial, ["logcat", "-d"], timeout=60)
    for line in log.splitlines():
        if re.search(r"Cursor:|long press|CANCEL|context|onLongPress|dispatchTouch", line, re.I):
            print(line)

    device.key(keys.BACK, wait=0.5)
    cursor_tests._toggle(device)


if __name__ == "__main__":
    main()
