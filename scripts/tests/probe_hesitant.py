"""Probe: the 'hesitant press' click path (600 ms hold) with CursorController logcat.

Replicates test_cursor_click_hesitant_press_still_clicks exactly, but captures the
controller's log around the confirm press so we can see whether the NEW confirm-key
yield ('yielding confirm key ... web content not focused') is firing when it should
NOT (i.e. the WebView should be focused after load + toggle-on).

Standalone; run:  python scripts/tests/probe_hesitant.py
"""
import atexit
import os
import re
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from framework import AndroidDevice, keys, adb  # noqa: E402

SERIAL = "192.168.178.67:5555"
PORT = 8899
ASSETS = os.path.join(os.path.dirname(__file__), "assets")


class _NoCache(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ASSETS, **kw)

    def send_header(self, k, v):
        if k.lower() == "last-modified":
            return
        super().send_header(k, v)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, *a):
        pass


_srv = ThreadingHTTPServer(("127.0.0.1", PORT), _NoCache)
threading.Thread(target=_srv.serve_forever, daemon=True).start()
atexit.register(_srv.shutdown)


def _focused(device):
    for n in device.nodes():
        if n.focused:
            return f"{n.cls} id={n.resource_id!r}"
    return "<none>"


def _title(device):
    return device.field_text()


def _toggle(device):
    device.key_longpress(keys.MEDIA_PLAY_PAUSE, wait=1.0)


def main():
    device = AndroidDevice(SERIAL)
    device.restart()
    device.reverse(PORT)
    url = f"http://localhost:{PORT}/cursor_target.html?cb={int(time.time() * 1000)}"
    device.navigate(url, reset=False)
    time.sleep(1.0)
    print("A) after load     focus:", _focused(device), "| title:", _title(device))

    _toggle(device)  # cursor on
    print("B) after toggle   focus:", _focused(device), "| title:", _title(device))

    adb.logcat(SERIAL, "", clear=True)
    device.key_hold(keys.DPAD_CENTER, 600)  # the hesitant press
    title = _title(device).strip()
    print("C) after 600ms hold title:", repr(title),
          "| looks-like-click:", bool(re.fullmatch(r"\d+,\d+", title)))
    log = adb.logcat(SERIAL, "Cursor:")
    print("D) Cursor: log around the press:")
    for l in log.splitlines():
        print("   ", l)
    yield_lines = [l for l in log.splitlines() if "yielding confirm" in l]
    print("E) yield fired?", bool(yield_lines), f"({len(yield_lines)} lines)")
    device.reverse_remove(PORT)
    print("done")


if __name__ == "__main__":
    main()
