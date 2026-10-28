"""Probe: does a 'real' touch long press (adb input swipe = full InputManager pipeline)
induce the same stuck state as our synthetic long press?

This is the decisive experiment:
  - if a real touch ALSO wedges the page  -> it is a WebView/renderer-level bug (affects real
    touch too; the fix belongs at the WebView/long-press handling level).
  - if it does NOT                        -> the wedge is specific to how our cursor controller
    synthesizes the touch (the fix belongs in CursorController).

The cursor is OFF for the whole probe (no overlay, no controller touch involvement): only
'in input swipe/tap' touch events and BACK keys are used. A screenshot is taken while a long
press is held, to see whether the native WebView context menu shows on screen.

    python scripts/tests/probe_real_swipe_stuck.py [--device SERIAL] [--swipes N]
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


def _pd_count(title: str) -> int:
    return len(re.findall(r"\bpd\d*", title))


def _ctx_count(title: str) -> int:
    return len(re.findall(r"\bctx\d*", title))


def main() -> None:
    serial = _arg("--device", SERIAL)
    swipes = int(_arg("--swipes", "4"))
    device = framework.AndroidDevice(serial)
    device.settle()

    cursor_tests._load_page(device, "longpress_log.html")
    # Ensure the cursor is OFF (the loader leaves it off; assert anyway).
    if cursor_tests._overlay_present(device):
        cursor_tests._toggle(device)

    os.makedirs(OUT_DIR, exist_ok=True)
    safe = serial.replace(":", "_")

    print("=== REAL touch (input swipe) long presses, cursor OFF ===")
    for i in range(1, swipes + 1):
        title_before = cursor_tests._title(device).strip()
        pd_b, ctx_b = _pd_count(title_before), _ctx_count(title_before)

        # A genuine 1500 ms hold at the center, through the full input pipeline.
        adb._adb(serial, ["shell", "input", "swipe", "960", "544", "960", "544", "1500"], timeout=30)
        time.sleep(0.8)
        # Screenshot while the (native?) menu may be up.
        adb._adb(serial, ["shell", "screencap", "-p", "/sdcard/real_swipe_hold.png"], timeout=30)
        adb._adb(serial, ["pull", "/sdcard/real_swipe_hold.png",
                          os.path.join(OUT_DIR, f"real_swipe_hold_{safe}_press{i}.png")], timeout=60)

        time.sleep(0.5)
        device.key(keys.BACK, wait=1.2)  # dismiss whatever the long press raised

        # Real tap: does the page get a fresh pointerdown?
        before = _pd_count(cursor_tests._title(device).strip())
        adb._adb(serial, ["shell", "input", "tap", "960", "544"], timeout=30)
        time.sleep(0.8)
        after = _pd_count(cursor_tests._title(device).strip())
        title = cursor_tests._title(device).strip()
        new_ctx = _ctx_count(title) - ctx_b
        print(f"press {i}: swipe -> new ctx events={new_ctx}; real tap -> "
              f"{'WORKS' if after > before else 'BLOCKED'}")
        if after == before:
            print(f"  STUCK after real-touch press {i}; title={title!r}")
            break

    print("=== done ===")
    device.key(keys.BACK, wait=0.5)
    if cursor_tests._overlay_present(device):
        cursor_tests._toggle(device)


if __name__ == "__main__":
    main()
