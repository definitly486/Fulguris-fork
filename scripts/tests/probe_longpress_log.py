"""Probe: what DOM event sequence does a deliberate action-key hold (context-menu long press)
actually produce on the page?

Loads assets/longpress_log.html (a full-screen link that records pointerdown/up/cancel,
mousedown/up, touchstart/end/cancel, contextmenu and click with relative timing into
document.title — mirrored into the toolbar label), turns the cursor on, sends a deliberate
1.5 s hold of the action key (DPAD center), and prints:
  - the page event log (the toolbar title),
  - whether the link context dialog is on screen (window list + node texts),
  - the Cursor: logcat lines.

This isolates the "long press also fires a click, so the page navigates" symptom: a CLICK in
the log (and a contextmenu/dialog at the same time) is the repro.

    python scripts/tests/probe_longpress_log.py --device 192.168.178.67:5555
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


def _serial() -> str:
    args = sys.argv[1:]
    if "--device" in args:
        return args[args.index("--device") + 1]
    return SERIAL


def _page() -> str:
    args = sys.argv[1:]
    if "--page" in args:
        return args[args.index("--page") + 1]
    return "longpress_log.html"


def _hold_ms() -> int:
    args = sys.argv[1:]
    if "--hold" in args:
        return int(args[args.index("--hold") + 1])
    return 1500


def one_run(device, hold_ms: int, label: str, page: str = "longpress_log.html") -> None:
    cursor_tests._load_page(device, page)
    print(f"loaded   title={cursor_tests._title(device)!r}")
    cursor_tests._toggle(device)

    adb._adb(device.id, ["shell", "logcat", "-c"])  # fresh logcat window
    t = time.time()
    device.key_hold(keys.DPAD_CENTER, hold_ms)
    print(f"{label}: held action key {hold_ms} ms ({time.time() - t:.2f}s)")

    title = cursor_tests._title(device).strip()
    print(f"{label}: page event log title={title!r}")

    log = adb._adb(device.id, ["shell", "logcat", "-d"])
    for line in log.splitlines():
        if "Cursor:" in line and "KEY" not in line:
            print(f"{label} log: {line[-110:]}")

    # Is the link context dialog on screen? Its "Copy link" row carries the link href.
    nodes = device.nodes()
    texts = [n.text for n in nodes if n.text.strip()]
    print(f"{label}: dialog present={any('javascript:void' in t or 'Copy' in t or '開く' in t for t in texts)}")
    print(f"{label}: node texts={texts[:12]}")
    device.key(keys.BACK, wait=0.8)  # dismiss the dialog (if any) so the next run starts clean


def main() -> None:
    device = framework.AndroidDevice(_serial())
    device.settle()
    print(f"fg={device.foreground_package()!r}")
    page = _page()
    hold = _hold_ms()
    print(f"page: {page}  hold: {hold} ms")

    # Deliberate hold (past the 1 s action-key threshold) — must open the context menu.
    one_run(device, hold, f"hold-{hold}", page)
    # A couple more holds to gauge frequency ("often get a simple click too" => not 100%).
    for i in (2, 3, 4):
        one_run(device, hold, f"hold-{hold}-r{i}", page)
    # Reference: a plain short click must log a clean click and NO contextmenu/dialog.
    cursor_tests._load_page(device, page)
    cursor_tests._toggle(device)
    device.key(keys.DPAD_CENTER, wait=1.0)
    print(f"short    : page event log title={cursor_tests._title(device).strip()!r}")
    cursor_tests._toggle(device)


if __name__ == "__main__":
    main()
