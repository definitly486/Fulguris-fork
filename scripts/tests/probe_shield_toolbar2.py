"""Probe #6: is the SHIELD toolbar auto-hiding (recoverable) or actually gone?

- Dump the full uiautomator hierarchy (all resource-ids).
- List windows via dumpsys window windows.
- Send a key (MENU / DPAD_CENTER) and re-dump to see if the toolbar appears.
"""
import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

import adb

SERIAL = "192.168.178.37:5555"


def dump_ids() -> list[str]:
    xml = adb.dump_ui(SERIAL)
    return re.findall(r'resource-id="([^"]+)"', xml)


def search_present() -> bool:
    return any(x.endswith(":id/search") for x in dump_ids())


print("== initial: search node present in uiautomator? ", search_present())
print("   all resource-ids:", [x.split('/')[-1] for x in dump_ids()])

print("\n== window list (dumpsys window windows) ==")
for l in adb._adb(SERIAL, ["shell", "dumpsys", "window", "windows"]).splitlines():
    if "Window #" in l or "mCurrentFocus" in l or "mFocusedApp" in l:
        print("  ", l.strip())

# Try to wake the toolbar with a key press.
for label, code in (("MENU(82)", 82), ("DPAD_CENTER(23)", 23)):
    adb.key(SERIAL, code, wait=1.2)
    time.sleep(0.5)
    print(f"\n== after {label}: search present? ", search_present(),
          " field_text:", repr(adb.field_text(SERIAL)))
