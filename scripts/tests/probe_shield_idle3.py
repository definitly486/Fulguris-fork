"""Probe #14 (decisive): after the idle, is the cursor still enabled?

Check the overlay (GONE while faded) BEFORE and AFTER a DPAD_RIGHT press. A live cursor wakes on
movement (overlay -> VISIBLE). So:
  - overlay wakes on DPAD_RIGHT  -> cursor is ON, events ARE arriving; problem is click-specific.
  - overlay stays GONE           -> cursor is OFF or events aren't reaching it (device / pre-existing,
                                    NOT the confirm-key yield, which only gates the confirm branch).
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
print(f"after enable: title={device.field_text()!r} overlay={overlay()}")

for _ in range(50):
    device.key(keys.DPAD_DOWN, wait=0.03)
time.sleep(4.0)
print(f"after idle:   title={device.field_text()!r} overlay={overlay()}  (faded => GONE expected)")

print("\n-- DPAD_RIGHT (should wake a live cursor) --")
device.key(keys.DPAD_RIGHT, wait=1.2)
print(f"  after DPAD_RIGHT: overlay={overlay()}  title={device.field_text()!r}")

print("\n-- DPAD_RIGHT again --")
device.key(keys.DPAD_RIGHT, wait=1.2)
print(f"  after 2nd DPAD_RIGHT: overlay={overlay()}  title={device.field_text()!r}")
ct._toggle(device)
