"""Probe #16 (decisive, log-independent): is the idle-scrubber failure the bottom-edge position?

The failing test drives 50xDPAD_DOWN (cursor to the clamped BOTTOM edge, which maps just BELOW the
CSS viewport per AGENTS.md), idles, then clicks -- the pre-click hover + click both land outside the
page, so the title stays 'ctrl-hidden' (no pointer event reached the page at all).

This probe reproduces that, but before the click moves the cursor back UP into the bar/viewport and
then clicks. Log-independent (title only):
  - click after moving up SEEMS to seek  -> the confirm path WORKS; the failure is purely the
    bottom-edge position (pre-existing geometry, DPI-dependent; NOT the confirm-key yield).
  - still 'ctrl-hidden'                  -> the confirm path itself is dead after the idle.
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

import cursor_tests as ct
from framework import AndroidDevice, keys

SERIAL = "192.168.178.37:5555"
device = AndroidDevice(SERIAL)
ct._ensure_server()
ct._ensure_reverse(device)


def overlay() -> bool:
    return device.find_node(":id/cursorOverlay") is not None


ct._load_page(device, "yt_scrub.html")
ct._toggle(device)
print(f"after enable:   title={device.field_text()!r} overlay={overlay()}")

for _ in range(50):
    device.key(keys.DPAD_DOWN, wait=0.03)
time.sleep(4.0)
print(f"after idle:     title={device.field_text()!r} overlay={overlay()}")

# click at the bottom edge (what the failing test does)
device.key(keys.DPAD_CENTER, wait=1.0)
t1 = device.field_text().strip()
print(f"click@bottom:   title={t1!r}   (expect 'ctrl-hidden' if the edge is below the viewport)")

# now move back UP into the bar/viewport and click again
for _ in range(15):
    device.key(keys.DPAD_UP, wait=0.05)
time.sleep(0.5)
device.key(keys.DPAD_CENTER, wait=1.0)
t2 = device.field_text().strip()
print(f"click@raised:   title={t2!r}   (expect 'seek@' if the confirm path works in-viewport)")
ct._toggle(device)
