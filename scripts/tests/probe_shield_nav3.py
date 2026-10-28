"""Probe #3: capture the SHIELD's actual on-screen + process state after navigation.

The previous probe showed even example.com -> empty field_text, so general navigation is
broken. Capture: screenshot, foreground package, app pid, WebView process, and the full
dumpsys activity top to see what activity is really on top.
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

import adb
from framework import AndroidDevice

SERIAL = "192.168.178.37:5555"
PKG = "net.slions.fulguris.full.download.debug"
device = AndroidDevice(SERIAL)

print("== wake display ==")
adb.key(SERIAL, 224, wait=0.5)  # WAKEUP
adb.key(SERIAL, 82, wait=0.8)   # MENU
time.sleep(1.0)

print("\n== current state ==")
print("foreground_package:", adb.foreground_package(SERIAL))
print("pidof app:", adb._adb(SERIAL, ["shell", "pidof", PKG]).strip())
print("field_text:", repr(device.field_text()))

print("\n== screenshot ==")
adb._adb(SERIAL, ["shell", "screencap", "-p", "/sdcard/shield_probe.png"])
adb._adb(SERIAL, ["pull", "/sdcard/shield_probe.png",
                  os.path.join(os.path.dirname(__file__), "..", "tools", "out", "shield_probe.png")])
print("pulled to scripts/tools/out/shield_probe.png")

print("\n== dumpsys activity top (first 30 lines) ==")
top = adb._adb(SERIAL, ["shell", "dumpsys", "activity", "top"])
for l in top.splitlines()[:30]:
    print("  ", l)

print("\n== wakefulness ==")
pw = adb._adb(SERIAL, ["shell", "dumpsys", "power"])
for l in pw.splitlines():
    if "mWakefulness=" in l or "Display Power" in l:
        print("  ", l)
