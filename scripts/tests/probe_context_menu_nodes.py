"""Probe: during a cursor long-press (dialog open), dump the FULL node tree.

Goal: determine whether the native WebView context menu is showing ALONGSIDE Fulguris's
custom dialog, or only the custom one. This decides the fix:
  - if a native menu is up, the renderer is waiting for it to be dismissed (pending state).
  - if only the custom dialog is up, the native menu was suppressed but the renderer was
    never told the long press resolved.

    python scripts/tests/probe_context_menu_nodes.py [--device SERIAL]
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import cursor_tests  # noqa: E402
import framework  # noqa: E402
from framework import keys  # noqa: E402

SERIAL = "192.168.178.67:5555"  # default: the RPi TV box


def _arg(name: str, default: str) -> str:
    args = sys.argv[1:]
    if name in args:
        return args[args.index(name) + 1]
    return default


def _dump(device, label: str) -> None:
    print(f"--- {label} ---")
    for n in device.nodes():
        text = (n.text or "").strip()
        if text:
            print(f"  [{n.cls}] text={text!r}")
    print()


def main() -> None:
    serial = _arg("--device", SERIAL)
    device = framework.AndroidDevice(serial)
    device.settle()

    cursor_tests._load_page(device, "longpress_log.html")
    cursor_tests._toggle(device)

    _dump(device, "BEFORE long press (no dialog)")

    device.key_hold(keys.DPAD_CENTER, 1500)
    time.sleep(1.5)  # let the dialog appear
    _dump(device, "DIALOG OPEN (after long press)")

    device.key(keys.BACK, wait=1.0)
    _dump(device, "AFTER BACK (dialog dismissed)")

    device.key(keys.BACK, wait=0.5)
    cursor_tests._toggle(device)


if __name__ == "__main__":
    main()
