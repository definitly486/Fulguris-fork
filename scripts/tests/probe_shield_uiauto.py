"""Probe #5: inspect the SHIELD uiautomator dump for the search field node.

field_text() reads the text of the node with id :id/search. Confirm the node exists in the
dump and print its attributes (text, focused, bounds, content-desc) to see why text is ''.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

import adb

SERIAL = "192.168.178.37:5555"
xml = adb.dump_ui(SERIAL)
print("dump length:", len(xml))

# print every node that mentions 'search' or 'toolbar' or has non-empty text
for m in re.finditer(r"<node [^>]*?/?>", xml):
    attrs = m.group(0)
    if "search" in attrs or "toolbar" in attrs.lower() or "button_more" in attrs:
        # tidy up
        d = dict(re.findall(r'(\w[\w-]*)="([^"]*)"', attrs))
        print("\nNODE:", d.get("resource-id") or d.get("class"))
        for k in ("text", "content-desc", "focused", "focusable", "bounds", "enabled", "class"):
            print(f"   {k} = {d.get(k)!r}")
