"""Restore the SHIELD's "Hide tool bar after" timeout to 5.0 (re-create the broken condition).

Used to verify that _reset_cursor_prefs now disables it automatically: after running this,
a cursor test should still PASS because the harness resets the timeout to 0 on first load.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

from framework import AndroidDevice

SERIAL = "192.168.178.37:5555"
PKG = "net.slions.fulguris.full.download.debug"
PATH = f"shared_prefs/{PKG}_preferences_landscape.xml"

device = AndroidDevice(SERIAL)
device.force_stop()
xml = device.read_prefs(PATH)
xml = re.sub(
    r'<float name="pref_key_hide_tool_bar_timeout" value="[^"]*" />',
    '<float name="pref_key_hide_tool_bar_timeout" value="5.0" />',
    xml,
)
device.write_prefs(PATH, xml)
m = re.search(r'pref_key_hide_tool_bar_timeout" value="([^"]*)"', device.read_prefs(PATH))
print("restored timeout =", m.group(1) if m else "(not set)")
