"""Probe: repeated long presses on the SAME page load (NO reload between them).

Chasing the "stuck touch state" anomaly seen in the real-remote capture: after a couple of
long presses, the page stopped receiving pointerdown (only contextmenu fired). Our probes
until now reloaded the page before every hold, which resets the WebView's touch state and
hides the problem. This probe loads longpress_log.html once, does N synthetic long presses
(dismissing the dialog with BACK between them), and dumps the accumulated DOM event log so
each press's touch sequence is visible.

Healthy: every press logs a fresh `pd` (pointerdown).
Stuck:   presses 2+ miss `pd` (the touch pipeline thinks a pointer is still in flight).

    python scripts/tests/probe_longpress_repeat.py [--device SERIAL] [--count N] [--hold MS]
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import adb  # noqa: E402
import cursor_tests  # noqa: E402
import framework  # noqa: E402
from framework import keys  # noqa: E402

SERIAL = "192.168.178.67:5555"  # default: the RPi TV box


def _arg(name: str, default: str) -> str:
    args = sys.argv[1:]
    if name in args:
        return args[args.index(name) + 1]
    return default


def main() -> None:
    serial = _arg("--device", SERIAL)
    count = int(_arg("--count", "3"))
    hold = int(_arg("--hold", "1500"))
    device = framework.AndroidDevice(serial)
    device.settle()

    cursor_tests._load_page(device, "longpress_log.html")
    print(f"loaded   title={cursor_tests._title(device)!r}")
    cursor_tests._toggle(device)

    adb._adb(serial, ["shell", "logcat", "-c"])
    for i in range(1, count + 1):
        t = time.time()
        device.key_hold(keys.DPAD_CENTER, hold)
        print(f"press {i}: held {hold} ms ({time.time() - t:.2f}s)")
        # Dismiss the context dialog (real href => SRC_ANCHOR_TYPE => dialog shows) so the
        # next press's key events reach the page, not the dialog.
        device.key(keys.BACK, wait=1.2)
        print(f"press {i}: dom log so far = {cursor_tests._title(device).strip()!r}")

    # Is the touch path fully dead, or only the long-press shape? A short press after the
    # long presses: a healthy page logs a CLICK; a stuck one logs nothing.
    device.key(keys.DPAD_CENTER, wait=1.0)
    print(f"short after: dom log = {cursor_tests._title(device).strip()!r}")

    log = adb._adb(serial, ["shell", "logcat", "-d"])
    print("\n=== Cursor: log ===")
    for line in log.splitlines():
        if "Cursor:" in line and "KEY" not in line:
            print("  ", line[-140:])

    device.key(keys.BACK, wait=0.5)
    cursor_tests._toggle(device)


if __name__ == "__main__":
    main()
