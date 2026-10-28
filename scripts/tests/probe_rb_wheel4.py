"""Key-delivery probe for the RB/LB wheel investigation.

The app logs every KeyEvent that reaches WebBrowserActivity.dispatchKeyEvent
("dispatchKeyEvent: code=... action=... src=... dev=..."). This script:

  1. Clears logcat, loads the target page, turns the cursor on.
  2. Sends virtual `input keyevent` for RB(43), LB(42), REW(89), FF(90).
  3. Waits 25 s, prompting the user to press the PHYSICAL Xbox RB / LB (and A,
     as a control) during that window.
  4. Dumps the dispatchKeyEvent + Cursor log lines, so we can see exactly
     which keycodes reached the app and from which device.

Usage: python scripts/tests/probe_rb_wheel4.py [--serial SERIAL]
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
REW, FF, RB, LB, BTN_A = 89, 90, 43, 42, 96


def main() -> None:
    serial = SERIAL
    for i, a in enumerate(sys.argv):
        if a == "--serial" and i + 1 < len(sys.argv):
            serial = sys.argv[i + 1]

    device = AndroidDevice(serial)
    print(f"serial={serial} package={device.package}")

    handler = partial(SimpleHTTPRequestHandler, directory=ASSETS)
    server = ThreadingHTTPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    device.reverse(PORT)
    time.sleep(0.5)

    adbmod.logcat(serial, "Cursor:", clear=True)  # clears the whole log

    url = f"http://localhost:{PORT}/cursor_target.html?cb={int(time.time() * 1000)}"
    device.navigate(url, reset=True)
    time.sleep(2.0)
    device.key_longpress(keys.MEDIA_PLAY_PAUSE, wait=1.0)
    print("cursor on; initial title:", repr(device.field_text()))
    time.sleep(1.0)  # let the toggle's log lines settle

    for code, label in ((RB, "RB"), (LB, "LB"), (REW, "REW"), (FF, "FF"), (BTN_A, "A")):
        device.key(code, wait=0.8)
        print(f"vk {label} ({code}) sent; title={device.field_text()!r}")

    print("\n>>> Now press the PHYSICAL Xbox buttons: RB a few times, LB a few times,")
    print(">>> and A once as a control. Waiting 25 s...")
    time.sleep(25)

    log = adbmod.logcat(serial, grep="dispatchKeyEvent")
    print("\n--- dispatchKeyEvent log (virtual + physical) ---")
    for line in log.splitlines():
        print(line)

    log2 = adbmod.logcat(serial, grep="Cursor:")
    print("\n--- Cursor: log ---")
    for line in log2.splitlines():
        print(line)

    device.reverse_remove(PORT)
    server.shutdown()


if __name__ == "__main__":
    main()
