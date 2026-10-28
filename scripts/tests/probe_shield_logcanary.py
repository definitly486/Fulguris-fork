"""Probe #15: canary -- are Timber 'Cursor:' logs visible on the SHIELD at all?

The cursor toggle logs 'Cursor: enable'/'Cursor: disable' unconditionally. If a clean logcat
window around a toggle shows NO such line, then Timber debug logging is invisible on this build
and every earlier '0 Cursor lines' observation on the SHIELD is meaningless (not evidence that
the branch didn't run).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

import adb
import cursor_tests as ct
from framework import AndroidDevice

SERIAL = "192.168.178.37:5555"
device = AndroidDevice(SERIAL)
ct._ensure_server()
ct._ensure_reverse(device)

ct._load_page(device, "yt_scrub.html")

adb._adb(SERIAL, ["logcat", "-c"])
ct._toggle(device)   # on  -> logs 'Cursor: enable'
log_on = adb._adb(SERIAL, ["logcat", "-d"])
ct._toggle(device)   # off -> logs 'Cursor: disable'
log_off = adb._adb(SERIAL, ["logcat", "-d"])

for label, log in (("toggle ON", log_on), ("toggle OFF", log_off)):
    lines = [l for l in log.splitlines() if "Cursor:" in l]
    print(f"{label}: {len(lines)} 'Cursor:' line(s)")
    for l in lines[:5]:
        print("   ", l)
    if not lines:
        print(f"    (TIMBER LOGS INVISIBLE ON THIS BUILD -- '0 Cursor lines' is meaningless here)")
