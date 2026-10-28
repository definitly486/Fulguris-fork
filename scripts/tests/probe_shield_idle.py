"""Probe #12: is the SHIELD scrubber_seek_after_idle failure the confirm-key yield or timing?

Replicate test_cursor_youtube_scrubber_seek_after_idle exactly, capturing logcat around the
final short DPAD_CENTER press:
  - "yielding confirm key" present  -> MY webContentFocusedProvider yield fired (my change involved)
  - "action-key press resolved"     -> the controller's confirm branch ran (no yield)
Also sample the title right after the press to see hover re-show timing.
"""
import os
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

ct._load_page(device, "yt_scrub.html")
ct._toggle(device)
print("after enable:", repr(device.field_text()))
for _ in range(50):
    device.key(keys.DPAD_DOWN, wait=0.03)
print("after move:", repr(device.field_text()))
time.sleep(4.0)
print("after 4s idle:", repr(device.field_text()))

adb._adb(SERIAL, ["logcat", "-c"])
device.key(keys.DPAD_CENTER, wait=1.0)
print("after press:", repr(device.field_text()))
time.sleep(1.0)
print("after press (+1s):", repr(device.field_text()))

log = adb._adb(SERIAL, ["logcat", "-d"])
print("\nyield fired? ", "yielding confirm key" in log)
print("action-key resolved:", [l for l in log.splitlines() if "action-key press resolved" in l])
cursor_lines = [l for l in log.splitlines() if "Cursor:" in l]
print(f"-- {len(cursor_lines)} Cursor lines --")
for l in cursor_lines[:20]:
    print("  ", l)
ct._toggle(device)
