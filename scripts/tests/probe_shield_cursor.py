"""Probe: does the SHIELD (Android 11) drive the cursor with a stick-less D-pad and read back
click coordinates / scroll? Replicates the cursor-movement test steps but with generous waits,
to separate a logic regression from slow page-load / label-mirror timing over network adb.

    python scripts/tests/probe_shield_cursor.py [--device SERIAL]
"""
from __future__ import annotations

import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import adb  # noqa: E402
import cursor_tests  # noqa: E402
from framework import AndroidDevice, keys  # noqa: E402


def wait_for_title(dev, want, timeout=45.0) -> str:
    """Poll the toolbar label until it matches ``want`` (a predicate) or time out; return last."""
    deadline = time.time() + timeout
    last = ""
    while time.time() < deadline:
        last = cursor_tests._title(dev).strip()
        if want(last):
            return last
        time.sleep(1.0)
    return last


def main() -> None:
    args = sys.argv[1:]
    serial = "192.168.178.37:5555"
    if "--device" in args:
        serial = args[args.index("--device") + 1]
    print(f"device: {serial}")
    dev = AndroidDevice(serial)

    cursor_tests._load_target(dev)
    t = wait_for_title(dev, lambda s: s == "start")
    print(f"page title: {t!r}  ({'OK' if t == 'start' else 'NOT LOADED'})")
    if t != "start":
        cursor_tests._teardown()
        return

    # Toggle via the MAIN MENU (tap menuItemCursor) — an independent path from the long-press
    # hotkey, so this isolates hotkey-specific breakage from cursor-logic problems.
    cursor_tests._open_main_menu(dev)
    item = dev.find_node(":id/menuItemCursor")
    print(f"menuItemCursor found: {item is not None}")
    if item and item.bounds:
        x1, y1, x2, y2 = item.bounds
        dev.tap((x1 + x2) // 2, (y1 + y2) // 2, wait=1.5)
    else:
        dev.key(keys.BACK, wait=0.8)
    time.sleep(1.0)
    print("overlay present (via menu):", cursor_tests._overlay_present(dev))
    t = wait_for_title(dev, lambda s: s == "hover", timeout=20)
    print(f"after menu-toggle hover: {t!r}  ({'OK' if t == 'hover' else 'no hover'})")

    # click at center
    coords = cursor_tests._click_coords(dev)
    if coords is None:
        print("center click: no coords yet, polling...")
        for _ in range(15):
            coords = cursor_tests._click_coords(dev)
            if coords:
                break
            time.sleep(1.0)
    print(f"center click coords: {coords}")

    # move right with a stick-less D-pad and confirm X increases
    for _ in range(8):
        dev.key(keys.DPAD_RIGHT, wait=0.15)
    moved = cursor_tests._click_coords(dev)
    print(f"after 8x DPAD_RIGHT: {moved}")
    if coords and moved:
        ok = moved[0] > coords[0] + 10
        print(f"DPAD_RIGHT moved cursor right: {ok}  ({coords} -> {moved})")
    cursor_tests._teardown()


if __name__ == "__main__":
    main()
