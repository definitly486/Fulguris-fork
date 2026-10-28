"""Probe: after inducing the stuck-touch state (synthetic long presses on the same page),
determine EXACTLY what blocks input and what clears it.

Checks the context DIALOG's presence (via uiautomator nodes) at each step, so we can tell
apart:
  (A) the dialog is still open and intercepts taps (early-BACK race), vs
  (B) the renderer blocks all input (context-menu-pending) until BACK clears it.

    python scripts/tests/probe_stuck_real_tap.py [--device SERIAL]
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import adb  # noqa: E402
import cursor_tests  # noqa: E402
import framework  # noqa: E402
from framework import keys  # noqa: E402

SERIAL = "192.168.178.67:5555"  # default: the RPi TV box


def _arg(name: str, default: str) -> str:
    args = sys.argv[1:]
    if name in args:
        return args[args.index(name) + 1]
    return default


def _dialog_open(device) -> bool:
    """The link context dialog's 'Copy link' row carries the example.com URL as secondary text."""
    return any("example.com" in (n.text or "") for n in device.nodes())


def main() -> None:
    serial = _arg("--device", SERIAL)
    device = framework.AndroidDevice(serial)
    device.settle()

    cursor_tests._load_page(device, "longpress_log.html")
    cursor_tests._toggle(device)

    def report(tag: str) -> str:
        title = cursor_tests._title(device).strip()
        dlg = _dialog_open(device)
        print(f"{tag:14} dialog={dlg}  title={title!r}")
        return title

    # Induce the stuck state: 3 synthetic long presses. Wait long enough after each hold that
    # the (async) dialog is definitely shown BEFORE pressing BACK, so the BACK race is removed.
    for i in range(1, 4):
        device.key_hold(keys.DPAD_CENTER, 1500)
        time.sleep(1.5)  # dialog is shown by now (appears ~0.5-1 s after the hold ends)
        report(f"press {i} pre-BACK")
        device.key(keys.BACK, wait=1.2)
        report(f"press {i} post-BACK")

    # Now the stuck state should exist (press 3 lost its 'pd'). Is the dialog open?
    # A REAL touch through the normal input pipeline:
    adb._adb(serial, ["shell", "input", "tap", "960", "544"], timeout=30)
    time.sleep(1.0)
    report("real tap")

    # Another BACK + real tap:
    device.key(keys.BACK, wait=1.0)
    report("back2")
    adb._adb(serial, ["shell", "input", "tap", "960", "544"], timeout=30)
    time.sleep(1.0)
    report("back2+tap")

    device.key(keys.BACK, wait=0.5)
    cursor_tests._toggle(device)


if __name__ == "__main__":
    main()
