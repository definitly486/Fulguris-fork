"""Probe #10: why a center tap doesn't enter fullscreen on the SHIELD.

Load fullscreen_target.html, then tap the screen center up to 3 times, reading the title
after each. If the title goes fs-init -> fs-on on the 2nd/3rd tap, the first tap is being
consumed by focus (a device/WebView behaviour), which is unrelated to the confirm-key change.
Also log whether the WebView has focus after the page load and after each tap.
"""
import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

import adb
import cursor_tests as ct
from framework import AndroidDevice

SERIAL = "192.168.178.37:5555"
device = AndroidDevice(SERIAL)
ct._ensure_server()
ct._ensure_reverse(device)
ct._load_page(device, "fullscreen_target.html")

w, h = device.screen_size()
print(f"screen_size: {w}x{h}; tapping center ({w // 2},{h // 2})")


def web_focused() -> bool:
    return any(n.cls == "android.webkit.WebView" and n.focused for n in device.nodes())


print("title after load:", repr(device.field_text()), " webview focused:", web_focused())

for i in range(1, 4):
    device.tap(w // 2, h // 2, wait=1.5)
    t = device.field_text()
    print(f"tap {i}: title={t!r}  webview focused={web_focused()}")
    if t == "fs-on":
        print("entered fullscreen on tap", i)
        device.key(4, wait=1.0)  # exit fullscreen
        break
