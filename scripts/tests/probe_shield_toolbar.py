"""Probe #4: why is the SHIELD's toolbar hidden?

The screenshot shows a page with NO toolbar. field_text() reads the toolbar label, so a
hidden toolbar makes every cursor test read ''. Read the app prefs for anything
toolbar/visibility related and check view_present('search') now.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

import adb
from framework import AndroidDevice

SERIAL = "192.168.178.37:5555"
PKG = "net.slions.fulguris.full.download.debug"
device = AndroidDevice(SERIAL)

print("view_present('search'):", adb.view_present(SERIAL, "search"))
print("view_present('button_more'):", adb.view_present(SERIAL, "button_more"))
print("field_text:", repr(device.field_text()))

xml = device.read_prefs(f"shared_prefs/{PKG}_preferences.xml")
entries = re.findall(r'<\w+ name="([^"]+)" value="([^"]*)"', xml)
print(f"\n-- toolbar/visibility related prefs ({len(entries)} prefs total) --")
for k, v in sorted(entries):
    if any(s in k.lower() for s in ("toolbar", "hide", "visible", "tool_bar")):
        print(f"  {k} = {v}")
print("\n-- ALL cursor* prefs --")
for k, v in sorted(entries):
    if k.startswith("pref_key_cursor"):
        print(f"  {k} = {v}")
