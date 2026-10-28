"""Probe: confirm-key (A / DPAD center) vs focus, with the cursor ON.

User report: "When the cursor is enabled the gamepad A button does not work as it should
when focus is on a toolbar widget. If focus is not on the WebView, A should go to the
focused control."

The cursor controller consumes the confirm key whenever the cursor is on screen, so it
always clicks the WebView under the cursor -- even when Android focus is on a toolbar
widget. This probe captures ground truth before the fix (no gamepad needed; adb's
DPAD_CENTER is consumed by the cursor exactly like BUTTON_A):

  B. Reproduce: load page (cursor off) -> move focus to a toolbar widget with the D-pad
     (focus nav, cursor off) -> enable the cursor (focus stays on the widget) -> press
     confirm. BUG: the page title becomes 'x,y' (the WebView under the cursor was
     clicked) instead of the widget being activated.
  C. Fullscreen: in HTML5 fullscreen with the cursor on, where is currentFocus? (The fix
     must not make the confirm key yield here -- the fullscreen click test depends on it.)

Run:  python scripts/tests/probe_a_focus.py
"""
from __future__ import annotations

import atexit
import os
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from framework import AndroidDevice, keys, adb  # noqa: E402

SERIAL = "192.168.178.67:5555"
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
PORT = 8899

_server: ThreadingHTTPServer | None = None
_reversed: set[str] = set()


class _NoCacheHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ASSETS_DIR, **kwargs)

    def send_header(self, key, value):
        if key.lower() == "last-modified":
            return
        super().send_header(key, value)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()

    def log_message(self, *args):
        pass


def _ensure_server() -> None:
    global _server
    if _server is None:
        _server = ThreadingHTTPServer(("127.0.0.1", PORT), _NoCacheHandler)
        threading.Thread(target=_server.serve_forever, daemon=True).start()
        atexit.register(_teardown)


def _teardown() -> None:
    for serial in _reversed:
        try:
            adb.reverse_remove(serial, PORT)
        except Exception:
            pass
    if _server is not None:
        _server.shutdown()


def _load(device, page: str) -> None:
    _ensure_server()
    if device.id not in _reversed:
        device.reverse(PORT)
        _reversed.add(device.id)
    url = f"http://localhost:{PORT}/{page}?cb={int(time.time() * 1000)}"
    device.navigate(url, reset=True)


def _toggle(device) -> None:
    device.key_longpress(keys.MEDIA_PLAY_PAUSE, wait=1.0)


def _overlay(device) -> bool:
    return device.find_node(":id/cursorOverlay") is not None


def _focused(device) -> str:
    for n in device.nodes():
        if n.focused:
            return f"{n.resource_id or n.cls} text={n.text!r}"
    return "<none>"


def _is_webview_focus(f: str) -> bool:
    return f.startswith(("android.webkit.WebView", ":id/web_view"))


def _title(device) -> str:
    return device.field_text()


def main() -> None:
    device = AndroidDevice(SERIAL)
    package = adb.detect_package(SERIAL)
    print(f"serial={SERIAL} package={package}")

    # ------------------------------------------------------------------ B
    print("\n=== B: repro -- focus a toolbar widget (cursor off), then enable cursor, press A ===")
    _load(device, "cursor_target.html")
    print(f"B0 focus: {_focused(device)}  title={_title(device)!r} overlay={_overlay(device)}")
    # Cursor is OFF here, so the D-pad does normal focus navigation. Try each direction and
    # report where focus lands, so we can see which reaches a toolbar widget.
    found = ""
    for label, code in (("up", keys.DPAD_UP), ("down", keys.DPAD_DOWN),
                        ("left", keys.DPAD_LEFT), ("right", keys.DPAD_RIGHT)):
        device.key(code, wait=0.7)
        f = _focused(device)
        print(f"B  dpad {label} -> focus: {f}")
        if not _is_webview_focus(f):
            found = f
            break
    if not found:
        print("B: could not move focus off the web view with one press per direction; trying more")
        for _ in range(4):
            device.key(keys.DPAD_UP, wait=0.5)
            found = _focused(device)
            print(f"B  dpad up -> focus: {found}")
            if not _is_webview_focus(found):
                break
    if not found or found == "<none>" or _is_webview_focus(found):
        print("B: could not land focus on a toolbar widget -- cannot reproduce; aborting")
        return
    print(f"B1 focus now on widget: {found}")
    # Now enable the cursor. Enabling does NOT move focus, so focus stays on the widget.
    _toggle(device)
    print(f"B2 after enable: overlay={_overlay(device)} focus: {_focused(device)} title={_title(device)!r}")
    before = _title(device)
    device.key(keys.DPAD_CENTER, wait=1.2)  # the confirm key (A / DPAD center)
    after = _title(device)
    print(f"B3 before A: {before!r}   after A: {after!r}")
    print("   --> BUG if after A is 'x,y' (WebView clicked); FIXED if it stays unchanged (widget activated)")
    device.key(keys.BACK, wait=0.8)  # dismiss any menu the widget may have opened
    _toggle(device)

    # ------------------------------------------------------------------ C
    print("\n=== C: fullscreen -- where is focus with the cursor on? ===")
    _load(device, "fullscreen_target.html")
    w, h = device.screen_size()
    device.tap(w // 2, h // 2, wait=1.5)
    print(f"C0 after tap: title={_title(device)!r} focus: {_focused(device)}")
    _toggle(device)
    print(f"C1 after enable: overlay={_overlay(device)} focus: {_focused(device)} title={_title(device)!r}")
    device.key(keys.DPAD_CENTER, wait=0.8)
    print(f"C2 after confirm: title={_title(device)!r}  (expect 'fsclick@...' = fullscreen click works)")
    _toggle(device)
    device.key(keys.BACK, wait=1.0)


if __name__ == "__main__":
    main()
