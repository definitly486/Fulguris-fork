"""Probe: is the SHIELD 'did not settle' a foreground_package false-negative (Android 11
colon format) and is the cursor page actually reachable? Manual one-off check.

    python scripts/tests/probe_shield_settle.py [--device SERIAL]
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import adb  # noqa: E402
import cursor_tests  # noqa: E402

from framework import AndroidDevice  # noqa: E402


def main() -> None:
    args = sys.argv[1:]
    serial = "192.168.178.37:5555"
    if "--device" in args:
        serial = args[args.index("--device") + 1]
    print(f"device: {serial}")

    # The raw activity line vs what foreground_package() reports.
    out = adb._adb(serial, ["shell", "dumpsys", "activity", "activities"])
    for line in out.splitlines():
        if "mResumedActivity" in line:
            print(f"raw: {line.strip()[:110]}")
            break
    print(f"foreground_package(): {adb.foreground_package(serial)!r}")

    dev = AndroidDevice(serial)
    cursor_tests._load_target(dev)  # server + reverse + navigate (cursor off)
    for i in range(20):
        t = cursor_tests._title(dev)
        if t:
            break
        time.sleep(1)
    print(f"label after navigate: {t!r}")
    if t == "start":
        print("PAGE OK — SHIELD is functional; failures are settle-detection, not the app")
    else:
        print("PAGE NOT REACHABLE — SHIELD infra problem")
    cursor_tests._teardown()


if __name__ == "__main__":
    main()
