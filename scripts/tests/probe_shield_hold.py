"""Probe #9: prove the SHIELD hesitant/context failures are NOT the confirm-key yield.

Load target, turn cursor on, then do a 600ms key_hold (the API<34 keycombination path on the
SHIELD). Capture logcat and check for:
  - "yielding confirm key"   -> my webContentFocusedProvider yield firing (would prove my change involved)
  - "action-key press resolved" -> how the controller resolved the press (longPress true/false)
  - "long press (context menu)" -> whether the context menu was triggered
This isolates whether the hold is even reaching the controller's confirm-key branch.
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
ct._reset_cursor_prefs(device)

ct._load_target(device)
ct._toggle(device)  # cursor on
time.sleep(0.5)

adb._adb(SERIAL, ["logcat", "-c"])
print("sending key_hold(DPAD_CENTER, 600) [API<34 => keycombination -t 600 113 23]")
device.key_hold(keys.DPAD_CENTER, 600, wait=1.5)
time.sleep(1.0)
print("title after hold:", repr(device.field_text()))

log = adb._adb(SERIAL, ["logcat", "-d"])
cursor_lines = [l for l in log.splitlines() if "Cursor:" in l or "cursor" in l.lower() and "fulguris" in l.lower()]
print(f"\n-- {len(cursor_lines)} Cursor log lines --")
for l in cursor_lines[:60]:
    print("  ", l)

print("\nyield fired? ", "yielding confirm key" in log)
print("action-key resolved line:", [l for l in log.splitlines() if "action-key press resolved" in l])
print("long press (context menu) line:", [l for l in log.splitlines() if "long press (context menu)" in l])
ct._toggle(device)
