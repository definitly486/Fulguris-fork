"""Probe #13: deep-dive the SHIELD idle-scrubber failure.

After the idle, check:
  - is the cursor overlay present (enabled?) / what node is focused?
  - does a DPAD_RIGHT (movement) work after the idle (does it wake/hover the cursor)?
  - does DPAD_CENTER then dispatch anything?
Capture the FULL logcat around each press: exceptions (a throwing provider lambda would show
here), any Cursor: lines, and input dispatch lines. This distinguishes
"event never reaches the app" vs "branch not entered" vs "click dispatched but page ignored it".
"""
import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

import adb
import cursor_tests as ct
from framework import AndroidDevice, keys

SERIAL = "192.168.178.37:5555"
device = AndroidDevice(SERIAL)
ct._ensure_server()
ct._ensure_reverse(device)


def focused() -> str:
    for n in device.nodes():
        if n.focused:
            return n.resource_id or n.cls
    return "(none)"


def overlay() -> bool:
    return device.find_node(":id/cursorOverlay") is not None


ct._load_page(device, "yt_scrub.html")
ct._toggle(device)
print(f"after enable: title={device.field_text()!r} overlay={overlay()} focused={focused()}")

for _ in range(50):
    device.key(keys.DPAD_DOWN, wait=0.03)
print(f"after move:  title={device.field_text()!r}")
time.sleep(4.0)
print(f"after idle:  title={device.field_text()!r} overlay={overlay()} focused={focused()}")

adb._adb(SERIAL, ["logcat", "-c"])
print("\n-- press DPAD_RIGHT (movement) --")
device.key(keys.DPAD_RIGHT, wait=1.2)
print(f"  title={device.field_text()!r}")
log_right = adb._adb(SERIAL, ["logcat", "-d"])

adb._adb(SERIAL, ["logcat", "-c"])
print("-- press DPAD_CENTER (confirm) --")
device.key(keys.DPAD_CENTER, wait=1.5)
print(f"  title={device.field_text()!r}")
log_center = adb._adb(SERIAL, ["logcat", "-d"])


def report(label: str, log: str) -> None:
    exc = [l for l in log.splitlines() if "Exception" in l or "FATAL" in l or "AndroidRuntime" in l]
    cursor = [l for l in log.splitlines() if "Cursor:" in l or "fulguris" in l.lower()]
    print(f"\n== {label}: {len(exc)} exception lines, {len(cursor)} fulguris/Cursor lines ==")
    for l in exc[:10]:
        print("   EXC:", l)
    for l in cursor[:25]:
        print("   ", l)


report("DPAD_RIGHT", log_right)
report("DPAD_CENTER", log_center)
ct._toggle(device)
