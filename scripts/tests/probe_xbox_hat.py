"""Probe: does the Xbox controller's D-pad drive the Fulguris TV cursor?

The Xbox Wireless Controller has no KEY_* D-pad codes; Android's input reader
maps its hat (ABS_HAT0X/ABS_HAT0Y) to a virtual D-pad. The probe loads the
cursor target page (whose title mirrors into the toolbar label), turns the
cursor ON, and injects hat presses via sendevent — a cursor move is visible as
the label changing away from 'hover'.

    python scripts/tests/probe_xbox_hat.py [--device SERIAL]
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import adb  # noqa: E402
import cursor_tests  # noqa: E402

TV_SERIAL = "192.168.178.67:5555"

ABS_HAT0X, ABS_HAT0Y = 0x16, 0x17


def key_state_while_hat(serial: str, node: str, x: int, y: int) -> str:
    """Hold the hat pushed and dump the Xbox device's input-reader section (KeyDowns)."""
    def ev(code: int, val: int) -> str:
        return f"sendevent {node} 0003 {code:04x} {val & 0xffff:04x}; sendevent {node} 0001 0000 0000"
    hold = (
        f"{ev(ABS_HAT0X, x)}; {ev(ABS_HAT0Y, y)}; sleep 1.2; dumpsys input"
    )
    out = adb._adb(serial, ["shell", hold], timeout=60)
    adb._adb(serial, ["shell", f"{ev(ABS_HAT0X, 0)}; {ev(ABS_HAT0Y, 0)}"], timeout=20)
    # Grab the Xbox device block and print the lines around any key-state info.
    lines = out.splitlines()
    for i, line in enumerate(lines):
        if "Device" in line and "Xbox" in line:
            block = lines[i:i + 70]
            for b in block:
                s = b.strip()
                if any(k in s for k in ("KeyDowns", "Keyboard", "Orientation", "MetaState",
                                         "HandlesKeyRepeat", "DPAD", "KEY_UP", "KEY_DOWN",
                                         "KEY_LEFT", "KEY_RIGHT", "Button", "Joystick")):
                    print(f"  {s[:120]}")
            break
    else:
        print("  (Xbox device block not found in dumpsys)")
    return ""


def main() -> None:
    args = sys.argv[1:]
    serial = TV_SERIAL
    if "--device" in args:
        serial = args[args.index("--device") + 1]
    print(f"device: {serial}")

    node = adb.find_input_node(serial, "xbox")
    if not node:
        print("Xbox controller node not found (is it connected?)")
        print("devices:", adb.input_devices(serial))
        return
    print(f"Xbox node: {node}")

    from framework import AndroidDevice
    dev = AndroidDevice(serial)

    cursor_tests._load_target(dev)      # page loaded, cursor OFF

    # (a) Verify the injection produces D-pad keys at all: with the cursor OFF the
    # hat must move focus through the app UI (toolbar buttons / menu).
    focus0 = cursor_tests._focused_resource_id(dev)
    adb.inject_hat_press(serial, node, 1, 0, wait=0.5)   # right
    adb.inject_hat_press(serial, node, 0, 1, wait=0.5)   # down
    focus1 = cursor_tests._focused_resource_id(dev)
    print(f"cursor OFF, focus: {focus0!r} -> {focus1!r}  "
          f"({'INJECTION WORKS' if focus1 != focus0 else 'no focus change — injection dead?'})")

    # (b) The actual repro: cursor ON (centered); if the gamepad D-pad drives the
    # cursor, holding it down to the bottom edge scrolls the page -> title 'sy<n>'.
    cursor_tests._toggle(dev)           # cursor ON, centered
    print(f"cursor on, label: {adb.field_text(serial)!r}")
    adb.inject_hat_hold(serial, node, 0, 1, hold=3.5)          # hat DOWN, held
    title = adb.field_text(serial)
    print(f"after hat DOWN held 3.5 s: label {title!r}  "
          f"({'BUG: gamepad D-pad moved the cursor' if title.startswith('sy') else 'cursor did not move'})")

    cursor_tests._toggle(dev)           # leave the cursor off

    print("\n=== key state while hat DOWN is held ===")
    print(key_state_while_hat(serial, node, 0, 1))


if __name__ == "__main__":
    main()
