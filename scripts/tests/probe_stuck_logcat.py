"""Probe: capture what the WebView/renderer does with input while in the stuck state.

Induces the stuck state (2 synthetic long presses on the link page), then clears logcat,
performs a REAL tap (input tap), and dumps the full logcat around it. The interesting lines
are Chromium/WebView input handling (AwContents, Input, LongPress, context menu, gesture).

    python scripts/tests/probe_stuck_logcat.py [--device SERIAL]
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
OUT_DIR = os.path.join(os.path.dirname(__file__), "out")


def _arg(name: str, default: str) -> str:
    args = sys.argv[1:]
    if name in args:
        return args[args.index(name) + 1]
    return default


def _logcat(serial: str, *args: str) -> str:
    adb._adb(serial, ["logcat"] + list(args), timeout=60)
    r = adb._adb(serial, ["logcat", "-d"], timeout=60)
    return r


def _pd_count(title: str) -> int:
    return len(re.findall(r"\bpd\d*", title))


def main() -> None:
    serial = _arg("--device", SERIAL)
    device = framework.AndroidDevice(serial)
    device.settle()

    cursor_tests._load_page(device, "longpress_log.html")
    cursor_tests._toggle(device)

    # Induce the stuck state: 2 long presses (breaks after press 2 on the link page).
    for i in range(1, 3):
        device.key_hold(keys.DPAD_CENTER, 1500)
        time.sleep(1.2)
        device.key(keys.BACK, wait=1.0)

    before = _pd_count(cursor_tests._title(device).strip())
    adb._adb(serial, ["shell", "input", "tap", "960", "544"], timeout=30)
    time.sleep(1.0)
    after = _pd_count(cursor_tests._title(device).strip())
    print(f"stuck check: pd before tap={before} after={after} "
          f"({'BLOCKED (stuck confirmed)' if after == before else 'works (NOT stuck)'})")

    # Now capture logcat around a fresh real tap.
    _logcat(serial, "-c")
    adb._adb(serial, ["shell", "input", "tap", "960", "544"], timeout=30)
    time.sleep(1.5)
    log = _logcat(serial, "-d")

    os.makedirs(OUT_DIR, exist_ok=True)
    safe = serial.replace(":", "_")
    path = os.path.join(OUT_DIR, f"stuck_logcat_{safe}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(log)
    print(f"logcat saved: {path} ({len(log)} chars)")

    # Print the WebView/Chromium input-related lines.
    print("\n--- WebView / Chromium / input lines around the tap ---")
    pat = re.compile(r"chromium|AwContents|AwBrowserProcess|WebView|Input|LongPress|long.?press|"
                     r"Context|context.?menu|Gesture|touch|Touch|pointer|Pointer|hit.?test|HitTest|"
                     r"InputDispatcher|InputMethod|focus|Focus", re.IGNORECASE)
    for line in log.splitlines():
        if pat.search(line):
            print(line)

    device.key(keys.BACK, wait=0.5)
    cursor_tests._toggle(device)


if __name__ == "__main__":
    main()
