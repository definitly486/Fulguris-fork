"""Disable the SHIELD's per-config "Hide tool bar after" auto-hide timeout.

The SHIELD's landscape config-scoped prefs file (shared_prefs/<pkg>_preferences_landscape.xml)
carries pref_key_hide_tool_bar_timeout = 5.0, so the toolbar auto-hides 5s after every page
load -- which breaks every cursor test (they read page state from the toolbar label). The
cursor harness resets only the *cursor* prefs in the *main* prefs file, so this config-scoped
timeout survives. This script force-stops the app, sets the timeout to 0 in the config file,
and restarts it, so the toolbar stays visible.

Usage:  python scripts/tests/disable_shield_toolbar_hide.py [SERIAL]
"""
import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

from framework import AndroidDevice

SERIAL = sys.argv[1] if len(sys.argv) > 1 else "192.168.178.37:5555"
device = AndroidDevice(SERIAL)
PKG = device.package
# The per-config file: orientation suffix only (portrait/landscape) -- see ContextExtensions.configId.
CONFIG_PREFS = f"shared_prefs/{PKG}_preferences_landscape.xml"


def set_timeout(value: float) -> None:
    device.force_stop()
    time.sleep(0.5)
    xml = device.read_prefs(CONFIG_PREFS)
    if "<map" not in xml:
        print(f"  {CONFIG_PREFS} not present; nothing to do")
        return
    entry = f'<float name="pref_key_hide_tool_bar_timeout" value="{value}" />'
    pat = re.compile(r'<(int|float) name="pref_key_hide_tool_bar_timeout" value="-?\d+(?:\.\d+)?" />')
    xml = pat.sub(entry, xml) if pat.search(xml) else xml.replace("</map>", f"    {entry}\n</map>")
    device.write_prefs(CONFIG_PREFS, xml)
    print(f"  set pref_key_hide_tool_bar_timeout = {value}")
    device.launch(wait=5.0)


def show() -> None:
    xml = device.read_prefs(CONFIG_PREFS)
    m = re.search(r'name="pref_key_hide_tool_bar_timeout" value="([^"]*)"', xml)
    print("  current pref_key_hide_tool_bar_timeout =", m.group(1) if m else "(not set)")


if __name__ == "__main__":
    print(f"== {SERIAL} ({PKG}) ==")
    print("before:")
    show()
    print("disabling (timeout -> 0):")
    set_timeout(0.0)
    time.sleep(1.0)
    print("after:")
    show()
    import adb
    xml = adb.dump_ui(SERIAL)
    print("  :id/search in uiautomator now:",
          any(x.endswith(":id/search") for x in re.findall(r'resource-id="([^"]+)"', xml)))
    print("  field_text:", repr(adb.field_text(SERIAL)))
