"""Probe whether RB (KEYCODE_BUTTON_R1) reaches the cursor wheel path.

Sequence on the target page with the cursor on:
  1. REW (89)  -> expect scroll down (known-good baseline)
  2. FF  (90)  -> scroll back up
  3. keyevent 43 (RB via the virtual keyboard) -> expect scroll down
  4. keyevent 42 (LB via the virtual keyboard) -> expect scroll up
  5. real Xbox RB via sendevent (if a gamepad node is present) -> expect scroll down

Usage: python scripts/tests/probe_rb_wheel.py [--serial SERIAL]
"""
from __future__ import annotations

import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

from framework import AndroidDevice, keys  # noqa: E402
import adb as adbmod  # noqa: E402

SERIAL = "192.168.178.67:5555"
PORT = 8899
ASSETS = os.path.join(os.path.dirname(__file__), "assets")


def main() -> None:
    serial = SERIAL
    for i, a in enumerate(sys.argv):
        if a == "--serial" and i + 1 < len(sys.argv):
            serial = sys.argv[i + 1]

    device = AndroidDevice(serial)
    print(f"serial={serial} package={device.package}")

    # Gamepad nodes?
    nodes = [(n, d) for n, d in adbmod.input_devices(serial)
             if any(k in d.lower() for k in ("xbox", "gamepad", "dualshock", "dualsense", "steam", "nintendo"))]
    print("gamepad nodes:", nodes)

    from functools import partial
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
    import threading
    handler = partial(SimpleHTTPRequestHandler, directory=ASSETS)
    server = ThreadingHTTPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=lambda: server.serve_forever(), daemon=True).start()
    device.reverse(PORT)
    time.sleep(0.5)

    def title() -> str:
        return device.field_text()

    def load() -> None:
        url = f"http://localhost:{PORT}/cursor_target.html?cb={int(time.time() * 1000)}"
        device.navigate(url, reset=True)
        time.sleep(1.5)

    def show(t: str) -> None:
        print(f"  title: {t!r}")

    load()
    device.key_longpress(keys.MEDIA_PLAY_PAUSE, wait=1.0)  # cursor on
    print("cursor on; initial:")
    show(title())

    def scroll_step(label: str, code: int) -> None:
        device.key(code, wait=1.0)
        print(f"{label}:")
        show(title())

    scroll_step("REW (89)   expect down", 89)
    scroll_step("FF  (90)   expect up", 90)
    scroll_step("FF  (90)   expect up", 90)
    scroll_step("keyevent 43 (RB) expect down", 43)
    scroll_step("keyevent 42 (LB) expect up", 42)
    scroll_step("keyevent 42 (LB) expect up", 42)

    if nodes:
        node, name = nodes[0]
        print(f"\nreal gamepad: {node} ({name})")
        # Button press via sendevent: EV_KEY=0001, RB=43, LB=42
        for label, code in (("real Xbox RB expect down", 43), ("real Xbox LB expect up", 42)):
            adbmod._adb(serial, ["shell", f"sendevent {node} 0001 {code} 1"])
            adbmod._adb(serial, ["shell", f"sendevent {node} 0000 0000 001e"])
            time.sleep(0.15)
            adbmod._adb(serial, ["shell", f"sendevent {node} 0001 {code} 0"])
            adbmod._adb(serial, ["shell", f"sendevent {node} 0000 0000 001e"])
            time.sleep(1.0)
            print(f"{label}:")
            show(title())

    device.reverse_remove(PORT)
    server.shutdown()


if __name__ == "__main__":
    main()
