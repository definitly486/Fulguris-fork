"""Probe: after inducing the stuck-touch state, find which action recovers the page WITHOUT a reload.

Induces the stuck state (2 synthetic long presses on the link page), confirms a real tap is
blocked, then tries a sequence of candidate recoveries, checking after each whether a real tap
works again:

  1. JS pointer event via evaluateJavascript (page-level, not native)
  2. WebView clearFocus + requestFocus (native focus churn)
  3. a scroll gesture (D-pad down) — forces WebView scroll handling
  4. a synthetic touch CANCEL-ish: short tap that we then... (proxy: tap a different point)
  5. reload (control — always works)

The goal is to learn what resets the renderer's input state, so the fix can do it cheaply.

    python scripts/tests/probe_stuck_recovery.py [--device SERIAL]
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
import framework  # noqa: E402
from framework import keys  # noqa: E402

SERIAL = "192.168.178.67:5555"  # default: the RPi TV box


def _arg(name: str, default: str) -> str:
    args = sys.argv[1:]
    if name in args:
        return args[args.index(name) + 1]
    return default


def _pd_count(title: str) -> int:
    return len(re.findall(r"\bpd\d*", title))


def _tap_ok(device, serial: str) -> bool:
    before = _pd_count(cursor_tests._title(device).strip())
    adb._adb(serial, ["shell", "input", "tap", "960", "544"], timeout=30)
    time.sleep(0.8)
    after = _pd_count(cursor_tests._title(device).strip())
    return after > before


def _js(device, serial: str, script: str) -> None:
    # Evaluate JS in the current WebView via the app's devtools is not available; use a JS
    # navigation-free probe by injecting through a data URL is heavy. Instead we rely on the
    # page's own handlers: dispatch a pointer event via the DOM by tapping is what we test.
    # For a JS-level recovery we post a message the page listens to — but the page has no such
    # hook, so this step is a no-op placeholder unless we add one. We skip heavy JS here.
    pass


def main() -> None:
    serial = _arg("--device", SERIAL)
    device = framework.AndroidDevice(serial)
    device.settle()

    cursor_tests._load_page(device, "longpress_log.html")
    cursor_tests._toggle(device)

    # Induce stuck state: 2 long presses (breaks after press 2 on the link page).
    for i in range(1, 3):
        device.key_hold(keys.DPAD_CENTER, 1500)
        time.sleep(1.2)
        device.key(keys.BACK, wait=1.0)

    blocked = not _tap_ok(device, serial)
    print(f"stuck state induced: real tap {'BLOCKED (good, as expected)' if blocked else 'still works (state not induced)'}")
    if not blocked:
        device.key(keys.BACK, wait=0.5)
        cursor_tests._toggle(device)
        return

    print("now trying recoveries (real tap after each):")

    # 1. focus churn: move D-pad focus off/on the webview.
    device.key(keys.DPAD_RIGHT, wait=0.4)
    device.key(keys.DPAD_LEFT, wait=0.4)
    print(f"  1. d-pad focus churn      -> real tap {'WORKS' if _tap_ok(device, serial) else 'blocked'}")

    # 2. a scroll (forces WebView onScrollChange / internal scroll state reset).
    device.key(keys.DPAD_DOWN, wait=0.6)
    print(f"  2. scroll (d-pad down)    -> real tap {'WORKS' if _tap_ok(device, serial) else 'blocked'}")

    # 3. a second, longer settle — does it decay with more time? (probe showed no decay to 15s)
    time.sleep(5)
    print(f"  3. settle +5s more        -> real tap {'WORKS' if _tap_ok(device, serial) else 'blocked'}")

    # 4. toggle the cursor off/on (re-parents overlay, churns views).
    cursor_tests._toggle(device)
    time.sleep(0.5)
    cursor_tests._toggle(device)
    time.sleep(0.5)
    print(f"  4. cursor toggle off/on   -> real tap {'WORKS' if _tap_ok(device, serial) else 'blocked'}")

    # 5. reload (control): navigate to the same page again.
    cursor_tests._load_page(device, "longpress_log.html")
    time.sleep(1.0)
    cursor_tests._toggle(device)
    print(f"  5. reload (control)       -> real tap {'WORKS' if _tap_ok(device, serial) else 'blocked'}")

    cursor_tests._toggle(device)
    device.key(keys.BACK, wait=0.5)


if __name__ == "__main__":
    main()
