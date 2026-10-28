"""Probe #11: determine the input-tap coordinate space on the SHIELD (logical vs physical).

The SHIELD is a 3840x2160 panel with a 1920x1080 override. If `input tap` uses LOGICAL
(override) coordinates, the true center is (960,540); if PHYSICAL, it's (1920,1080).
Load fullscreen_target.html and tap each candidate center (with a reload between) to see
which one enters fullscreen (fs-init -> fs-on). That tells us what screen_size() must return.
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


def try_tap(x: int, y: int) -> str:
    ct._load_page(device, "fullscreen_target.html")
    time.sleep(0.5)
    device.tap(x, y, wait=1.8)
    t = device.field_text()
    if t == "fs-on":
        device.key(4, wait=1.0)  # exit fullscreen
    return t


for label, (x, y) in (("logical center (960,540)", (960, 540)),
                      ("physical center (1920,1080)", (1920, 1080)),
                      ("a bit inside (900,500)", (900, 500))):
    t = try_tap(x, y)
    print(f"tap {label}: title={t!r}  {'<== ENTERED FULLSCREEN' if t == 'fs-on' else ''}")
