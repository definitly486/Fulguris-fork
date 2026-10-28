"""Probe: read the on-device pref_key_cursor_action_hold value (and other cursor prefs).

Standalone; run:  python scripts/tests/probe_action_hold.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from framework import AndroidDevice  # noqa: E402

SERIAL = "192.168.178.67:5555"


def main():
    device = AndroidDevice(SERIAL)
    path = f"shared_prefs/{device.package}_preferences.xml"
    xml = device.read_prefs(path)
    for line in xml.splitlines():
        if "cursor" in line.lower():
            print(line.strip())


if __name__ == "__main__":
    main()
