"""Probe #7 (decisive): is the SHIELD toolbar missing ALWAYS or only AFTER navigation?

Sequence:
  1. force_stop + launch (clean).
  2. Immediately check uiautomator for :id/search (BEFORE any navigation).
  3. Navigate to a local asset.
  4. Re-check :id/search (AFTER navigation).
Also reports the InputMethod window's mShowing state at each step.
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
PKG = "net.slions.fulguris.full.download.debug"
device = AndroidDevice(SERIAL)


def search_in_uiauto() -> bool:
    xml = adb.dump_ui(SERIAL)
    return any(x.endswith(":id/search") for x in re.findall(r'resource-id="([^"]+)"', xml))


def ime_state() -> str:
    out = adb._adb(SERIAL, ["shell", "dumpsys", "window", "windows"])
    for i, l in enumerate(out.splitlines()):
        if "InputMethod" in l and "Window #" in l:
            block = "\n".join(out.splitlines()[i:i + 12])
            m = re.search(r"mShowing=(\w+)", block)
            return f"InputMethod mShowing={m.group(1) if m else '?'}"
    return "InputMethod window: not present"


ct._ensure_server()
ct._ensure_reverse(device)

print("== step 1: force_stop + launch ==")
device.force_stop()
time.sleep(1.0)
device.launch(wait=6.0)
print("  fg:", adb.foreground_package(SERIAL))
print("  search in uiautomator (BEFORE nav):", search_in_uiauto())
print("  ", ime_state())
print("  field_text:", repr(device.field_text()))

print("\n== step 2: navigate to local asset ==")
url = f"http://localhost:{ct.PORT}/cursor_target.html?cb={int(time.time() * 1000)}"
device.navigate(url, reset=True)
time.sleep(2.0)
print("  search in uiautomator (AFTER nav):", search_in_uiauto())
print("  ", ime_state())
print("  field_text:", repr(device.field_text()))
