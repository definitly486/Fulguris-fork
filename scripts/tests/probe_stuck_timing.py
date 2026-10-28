"""Probe: characterize the stuck-touch state after repeated long presses.

Questions answered:
  1. ONSET: after how many long presses does a REAL tap (input tap) start failing?
     (one real tap between every long press; the tap's 'pd' in the title = works.)
  2. DECAY: once stuck, does a real tap start working again after some seconds,
     or only after a reload/navigation? (probe taps at fixed offsets after the
     press that broke it)

    python scripts/tests/probe_stuck_timing.py [--device SERIAL] [--presses N] [--page NAME]
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


def _tap(device, serial: str) -> bool:
    """Real hardware tap at the cursor point; True if the page got a fresh pointerdown."""
    before = _pd_count(cursor_tests._title(device).strip())
    adb._adb(serial, ["shell", "input", "tap", "960", "544"], timeout=30)
    time.sleep(0.8)
    after = _pd_count(cursor_tests._title(device).strip())
    return after > before


def main() -> None:
    serial = _arg("--device", SERIAL)
    presses = int(_arg("--presses", "4"))
    page = _arg("--page", "longpress_log.html")
    device = framework.AndroidDevice(serial)
    device.settle()

    print(f"page: {page}")
    cursor_tests._load_page(device, page)
    cursor_tests._toggle(device)

    print("=== ONSET: real tap after each long press ===")
    broke_at = 0
    for i in range(1, presses + 1):
        device.key_hold(keys.DPAD_CENTER, 1500)
        time.sleep(1.2)  # let the dialog appear
        device.key(keys.BACK, wait=1.0)  # dismiss the dialog
        ok = _tap(device, serial)
        print(f"press {i}: real tap after -> {'WORKS' if ok else 'BLOCKED'}")
        if not ok:
            broke_at = i
            # DECAY: keep probing the stuck state at fixed offsets (dialog is closed).
            t0 = time.time()
            for offset in (3, 6, 9, 12, 15):
                now = time.time()
                if now - t0 < offset:
                    time.sleep(offset - (now - t0))
                ok2 = _tap(device, serial)
                print(f"  stuck +{offset:2d}s: real tap -> {'WORKS' if ok2 else 'BLOCKED'}")
                if ok2:
                    break
            break

    print(f"=== summary: real tap breaks after press {broke_at if broke_at else '>=' + str(presses)} ===")
    device.key(keys.BACK, wait=0.5)
    cursor_tests._toggle(device)


if __name__ == "__main__":
    main()
