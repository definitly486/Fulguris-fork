"""Probe why local-asset navigation yields an empty field_text on the SHIELD.

Replicates the test harness's _load_page setup (server + adb reverse + navigate) and prints
diagnostics at each step: does the reverse tunnel work (curl from the device), what does
field_text() read after navigation, and is the page's title ever set.
"""
import os
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
ct._ensure_server()
ct._ensure_reverse(device)
print("reverse list:", adb._adb(SERIAL, ["reverse", "--list"]))

# 1. Can the device reach the host server through the tunnel?
print("\n-- curl from device --")
out = adb._adb(SERIAL, ["shell", "curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                        f"http://localhost:{ct.PORT}/cursor_target.html"])
print("http status from device:", out)

# 2. Navigate like the test does.
ct._reset_cursor_prefs(device)
url = f"http://localhost:{ct.PORT}/cursor_target.html?cb={int(time.time() * 1000)}"
print("\nnavigating to:", url)
device.navigate(url, reset=True)

for i in range(6):
    time.sleep(1.0)
    print(f"  t+{i + 1}s field_text: {device.field_text()!r}")

print("\n-- focused node --")
for n in device.nodes():
    if n.focused:
        print("  focused:", n.resource_id or n.class_name, repr(n.text)[:40])
print("done")
