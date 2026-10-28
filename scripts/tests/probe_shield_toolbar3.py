"""Probe #8: is the post-nav missing toolbar a timing artifact or a stuck state?

After navigating, sample uiautomator for :id/search over ~12s (is it just slow?), check
ime_shown / field_focused (is the field stuck in edit mode with a fullscreen leanback IME
covering the toolbar?), then try BACK to exit edit mode and re-check.
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


def search_present() -> bool:
    xml = adb.dump_ui(SERIAL)
    return any(x.endswith(":id/search") for x in re.findall(r'resource-id="([^"]+)"', xml))


ct._ensure_server()
ct._ensure_reverse(device)
url = f"http://localhost:{ct.PORT}/cursor_target.html?cb={int(time.time() * 1000)}"
print("navigate:", url)
device.navigate(url, reset=True)

print("\n== sampling :id/search over 12s ==")
for i in range(12):
    time.sleep(1.0)
    print(f"  t+{i + 1:2d}s  search={search_present()}  ime_shown={adb.ime_shown(SERIAL)}  "
          f"field_focused={adb.field_focused(SERIAL)}  field_text={device.field_text()!r}")

print("\n== press BACK once (exit edit mode / dismiss IME) ==")
adb.key(SERIAL, 4, wait=1.5)
time.sleep(1.0)
print("  search present:", search_present(), " field_text:", repr(device.field_text()))

print("\n== press MENU (82) to wake toolbar ==")
adb.key(SERIAL, 82, wait=1.5)
time.sleep(1.0)
print("  search present:", search_present(), " field_text:", repr(device.field_text()))
