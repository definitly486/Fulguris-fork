"""Diagnose why RB/LB wheel scroll is flaky/absent.

1. Print the Xbox node's full KEY mapping (getevent -p).
2. Load the target page, turn the cursor on.
3. Press the REAL Xbox RB (sendevent) several times; after each, print title.
4. Press virtual-keyboard 43 (input keyevent) several times; after each, print title.
5. Dump every "Cursor:" log line from the run, so we can see whether the key
   reached dispatchKeyEvent and whether the wheel branch fired.

Usage: python scripts/tests/probe_rb_wheel2.py [--serial SERIAL]
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
RB = 43  # KEYCODE_BUTTON_R1
LB = 42  # KEYCODE_BUTTON_L1


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
    if not nodes:
        print("no gamepad connected — cannot test the real button; virtual-keyboard part only")

    # 1. full KEY mapping of the gamepad node
    if nodes:
        node = nodes[0][0]
        print(f"\n--- getevent -p {node} ---")
        out = adbmod._adb(serial, ["shell", f"getevent -p {node}"], timeout=30)
        for line in out.splitlines():
            if "KEY" in line or "name" in line or "ABS" in line:
                print(line)
    else:
        node = None

    # HTTP server + reverse
    handler = partial(SimpleHTTPRequestHandler, directory=ASSETS)
    server = ThreadingHTTPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    device.reverse(PORT)
    time.sleep(0.5)

    adbmod.logcat(serial, "Cursor:", clear=True)

    # 2. load + cursor on
    url = f"http://localhost:{PORT}/cursor_target.html?cb={int(time.time() * 1000)}"
    device.navigate(url, reset=True)
    time.sleep(1.5)
    device.key_longpress(keys.MEDIA_PLAY_PAUSE, wait=1.0)
    print("\ncursor on; initial title:", repr(device.field_text()))

    def real_press(code: int) -> None:
        adbmod._adb(serial, ["shell", f"sendevent {node} 0001 {code} 1"])
        adbmod._adb(serial, ["shell", "sendevent %s 0000 0000 001e" % node])
        time.sleep(0.1)
        adbmod._adb(serial, ["shell", f"sendevent {node} 0001 {code} 0"])
        adbmod._adb(serial, ["shell", f"sendevent {node} 0000 0000 001e"])
        time.sleep(0.8)

    # 3. real RB presses
    if node:
        for i in range(5):
            real_press(RB)
            print(f"real RB  #{i+1}: title={device.field_text()!r}")

    # 4. virtual keyboard 43
    for i in range(4):
        device.key(RB, wait=0.8)
        print(f"vk RB    #{i+1}: title={device.field_text()!r}")

    # 5. logcat
    log = adbmod.logcat(serial, grep="Cursor:")
    print("\n--- logcat 'Cursor:' ---")
    for line in log.splitlines():
        print(line)
    if not log.strip():
        print("(no Cursor: log lines — the keys never reached the wheel branch)")

    device.reverse_remove(PORT)
    server.shutdown()


if __name__ == "__main__":
    main()
