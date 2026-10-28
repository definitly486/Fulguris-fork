"""Probe: does the tab's WebView hold Android input focus during HTML5 fullscreen?

The confirm-key yield (CursorController) defers to the focused control whenever
`currentTabView?.hasFocus()` is false. In fullscreen the visible view is a separate
custom-view hierarchy, so we must confirm the WebView still reports focused there --
otherwise the yield swallows the fullscreen click.

Standalone; run:  python scripts/tests/probe_fullscreen_focus.py
"""
import atexit
import os
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
            return f"{n.cls} id={n.resource_id!r} text={n.text!r}"
    return "<none>"


def main():
    device = AndroidDevice(SERIAL)
    device.restart()
    device.reverse(PORT)
    url = f"http://localhost:{PORT}/fullscreen_target.html?cb={int(time.time() * 1000)}"
    device.navigate(url, reset=False)
    time.sleep(1.0)
    print("A) normal page   focus:", _focused(device), "| title:", device.field_text())

    w, h = device.screen_size()
    device.tap(w // 2, h // 2, wait=1.5)
    print("B) after tap     focus:", _focused(device), "| title:", device.field_text())

    # cursor on while fullscreen
    device.key_longpress(keys.MEDIA_PLAY_PAUSE, wait=1.0)
    print("C) fullscreen+cursor focus:", _focused(device), "| title:", device.field_text())
    for _ in range(3):
        device.key(keys.DPAD_RIGHT, wait=0.15)
    adb.logcat(SERIAL, "", clear=True)
    device.key(keys.DPAD_CENTER, wait=0.8)
    print("D) after confirm focus:", _focused(device), "| title:", device.field_text())
    log = adb.logcat(SERIAL, "Cursor:")
    print("E) cursor logcat lines around the fullscreen confirm press:")
    for l in log.splitlines()[-15:]:
        print("   ", l)

    device.key_longpress(keys.MEDIA_PLAY_PAUSE, wait=1.0)  # cursor off
    device.key(keys.BACK, wait=1.0)  # exit fullscreen
    device.reverse_remove(PORT)
    print("done")


if __name__ == "__main__":
    main()
