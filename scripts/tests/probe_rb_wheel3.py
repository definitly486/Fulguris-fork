"""Controlled comparison: does the app receive virtual REW (89) but not RB (43)?

- Prints the FULL raw getevent -p for the gamepad node (see the real KEY set).
- Confirms the foreground activity.
- With the cursor on, alternates REW (known-good wheel) and RB, then dumps the
  FULL 'Cursor:' logcat so we can see exactly which keyevents reached the
  controller's wheel branch.

Usage: python scripts/tests/probe_rb_wheel3.py [--serial SERIAL]
"""
from __future__ import annotations

import os
import sys
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

from framework import AndroidDevice, keys  # noqa: E402
import adb as adbmod  # noqa: E402

SERIAL = "192.168.178.67:5555"
PORT = 8899
ASSETS = os.path.join(os.path.dirname(__file__), "assets")
REW, FF, RB, LB = 89, 90, 43, 42


def main() -> None:
    serial = SERIAL
    for i, a in enumerate(sys.argv):
        if a == "--serial" and i + 1 < len(sys.argv):
            serial = sys.argv[i + 1]

    device = AndroidDevice(serial)
    print(f"serial={serial} package={device.package}")

    nodes = [(n, d) for n, d in adbmod.input_devices(serial)
             if any(k in d.lower() for k in ("xbox", "gamepad", "dualshock", "dualsense", "steam", "nintendo"))]
    print("gamepad nodes:", nodes)
    node = nodes[0][0] if nodes else None

    # FULL raw key mapping (do not filter)
    if node:
        print(f"\n--- getevent -p {node} (raw) ---")
        print(adbmod._adb(serial, ["shell", f"getevent -p {node}"], timeout=30))

    # Foreground activity
    fg = adbmod._adb(serial, ["shell", "dumpsys", "activity", "activities"], timeout=30)
    for line in fg.splitlines():
        if "topResumedActivity" in line or "ResumedActivity" in line:
            print("FG:", line.strip())

    handler = partial(SimpleHTTPRequestHandler, directory=ASSETS)
    server = ThreadingHTTPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    device.reverse(PORT)
    time.sleep(0.5)

    adbmod.logcat(serial, "Cursor:", clear=True)

    url = f"http://localhost:{PORT}/cursor_target.html?cb={int(time.time() * 1000)}"
    device.navigate(url, reset=True)
    time.sleep(2.0)
    device.key_longpress(keys.MEDIA_PLAY_PAUSE, wait=1.0)
    print("\ncursor on; initial title:", repr(device.field_text()))

    def press(code: int, label: str) -> None:
        device.key(code, wait=0.9)
        print(f"{label} ({code}): title={device.field_text()!r}")

    # Alternating known-good (REW) and target (RB) to prove the app is receiving keys
    press(REW, "REW")
    press(RB,  "RB")
    press(REW, "REW")
    press(FF,  "FF")
    press(LB,  "LB")
    press(FF,  "FF")

    log = adbmod.logcat(serial, grep="Cursor:")
    print("\n--- logcat 'Cursor:' ---")
    for line in log.splitlines():
        print(line)
    if not log.strip():
        print("(no Cursor: lines at all — app not receiving these keys)")

    device.reverse_remove(PORT)
    server.shutdown()


if __name__ == "__main__":
    main()
