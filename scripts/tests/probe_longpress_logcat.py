"""Probe: capture WebView/Chromium logcat during the long-press sequence that induces the
stuck state, to see the NATIVE context-menu lifecycle (does it show? when is it dismissed?)
and anything the renderer logs about the long press / input state.

Sequence: load page, cursor on, clear logcat, long press 1 (works), BACK, long press 2
(starts the stuck state), BACK, then dump logcat and print the WebView/Chromium/context-menu
lines. Comparing press 1 vs press 2 lines is the point.

    python scripts/tests/probe_longpress_logcat.py [--device SERIAL]
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


def main() -> None:
    serial = _arg("--device", SERIAL)
    device = framework.AndroidDevice(serial)
    device.settle()

    cursor_tests._load_page(device, "longpress_log.html")
    cursor_tests._toggle(device)

    adb._adb(serial, ["logcat", "-c"], timeout=60)

    print("long press 1 ...")
    device.key_hold(keys.DPAD_CENTER, 1500)
    time.sleep(1.5)  # dialog appears
    device.key(keys.BACK, wait=1.2)

    print("long press 2 ...")
    device.key_hold(keys.DPAD_CENTER, 1500)
    time.sleep(1.5)
    device.key(keys.BACK, wait=1.2)

    time.sleep(0.5)
    log = adb._adb(serial, ["logcat", "-d"], timeout=60)

    os.makedirs(OUT_DIR, exist_ok=True)
    safe = serial.replace(":", "_")
    path = os.path.join(OUT_DIR, f"longpress_logcat_{safe}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(log)
    print(f"logcat saved: {path} ({len(log)} chars)\n")

    # The lines that matter: WebView/Chromium input, long press, context menu, hit test.
    pat = re.compile(
        r"chromium|AwContents|AwBrowser|WebChromeClient|WebView|LongPress|long.?press|"
        r"ContextMenu|context.?menu|onLongClick|requestFocusNodeHref|cancelLongPress|"
        r"HitTest|hit.?test|onSingleTapUp|onShowPress|GestureDetector|focusNodeHref|"
        r"Cursor:|WebPageTab|WebBrowserActivity",
        re.IGNORECASE,
    )
    print("--- matching lines (long-press / context-menu / input) ---")
    n = 0
    for line in log.splitlines():
        if pat.search(line):
            print(line)
            n += 1
    print(f"\n({n} matching lines)")

    device.key(keys.BACK, wait=0.5)
    cursor_tests._toggle(device)


if __name__ == "__main__":
    main()
