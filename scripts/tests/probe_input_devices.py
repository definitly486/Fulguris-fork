"""Probe: list the connected input devices and their key mappings (to see how the remote's
OK/action button is reported — a single physical button reported as two key codes, e.g. both
KEYCODE_DPAD_CENTER and KEYCODE_BUTTON_A, is the prime suspect for the "long press also
fires a click" bug).

    python scripts/tests/probe_input_devices.py [--device SERIAL]
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import adb  # noqa: E402

SERIAL = "192.168.178.67:5555"


def main() -> None:
    serial = SERIAL
    args = sys.argv[1:]
    if "--device" in args:
        serial = args[args.index("--device") + 1]

    print("=== dumpsys input (Input device / classes lines) ===")
    out = adb._adb(serial, ["shell", "dumpsys", "input"], timeout=60)
    for line in out.splitlines():
        s = line.strip()
        if s.startswith(("Input device", "classes:")):
            print("  ", s[:160])

    print()
    print("=== getevent -pl (per-device key mappings, confirm keys highlighted) ===")
    try:
        out = adb._adb(serial, ["shell", "getevent", "-pl"], timeout=20)
        for line in out.splitlines():
            s = line.strip()
            if not s:
                continue
            if s.startswith("/dev/input/"):
                print(f"--- {s}")
            elif "KEY_" in s:
                for code in ("KEY_DPAD_CENTER", "KEY_ENTER", "KEY_BUTTON_A", "KEY_NUMPAD"):
                    if code in s:
                        print(f"    * {code:16} {s[:140]}")
    except Exception as e:  # noqa: BLE001
        print("getevent -pl failed:", e)


if __name__ == "__main__":
    main()
