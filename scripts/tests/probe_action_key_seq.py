"""Probe: capture the REAL remote's action-key event sequence for a long press.

The "long press also fires a click, so the page navigates" bug is intermittent and only happens
with the physical remote (a synthetic `adb --duration` hold is clean). The instrumented
CursorController logs the raw action-key event sequence of each press
("d23(r0) u23 ..." = DOWN keycode 23 repeat 0, UP keycode 23 ...). This probe:
  1. loads assets/longpress_log.html (a full-screen link that records the DOM pointer/click
     sequence into the toolbar title, with click's preventDefault so the page never navigates
     away and we can still read it),
  2. turns the cursor on,
  3. clears logcat,
  4. waits a fixed window while the USER does a real long press on the remote,
  5. dumps the Cursor: log lines (the event sequence) + the DOM event log + a screenshot.

Run it, then on the remote HOLD the OK/select button for ~1.5 s (a deliberate long press).
Repeat a couple of times during the window if the first is clean (the bug is intermittent).

    python scripts/tests/probe_action_key_seq.py --device 192.168.178.67:5555 --wait 45
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


def _ensure_cursor_on(device, serial: str) -> None:
    """Toggle the cursor ON, verifying via logcat (a faded overlay can't be seen over adb, so a
    previous run may have left it on — a plain _toggle would then turn it OFF)."""
    for attempt in (1, 2):
        adb._adb(serial, ["shell", "logcat", "-c"])
        cursor_tests._toggle(device)
        log = adb._adb(serial, ["shell", "logcat", "-d"])
        if "Cursor: enable" in log:
            print(f"cursor confirmed ON (attempt {attempt})")
            return
        print(f"attempt {attempt} did not enable the cursor, retrying...")
    raise AssertionError("could not confirm the cursor is ON")


def main() -> None:
    serial = _arg("--device", SERIAL)
    wait_s = float(_arg("--wait", "45"))
    device = framework.AndroidDevice(serial)
    device.settle()

    cursor_tests._load_page(device, "longpress_log.html")
    _ensure_cursor_on(device, serial)
    adb._adb(serial, ["shell", "logcat", "-c"])

    print(f"\nREADY on {serial}: cursor is ON over the link target.")
    print("Now, on the REMOTE, HOLD the OK/select button for ~1.5 s (a deliberate long press).")
    print("Do it 2-3 times (the bug is intermittent); I keep listening until the window ends.")
    def _dispatch_count(log: str) -> int:
        # Count any action-key dispatch. Note a press whose UP is stolen by the context dialog
        # logs ONLY the "long press (context menu)" line (no "press resolved"), so counting only
        # "press resolved" would under-report.
        return log.count("press resolved") + log.count("long press (context menu)")

    deadline = time.time() + wait_s
    seen = 0
    while time.time() < deadline:
        time.sleep(5)
        log = adb._adb(serial, ["shell", "logcat", "-d"])
        n = _dispatch_count(log)
        if n > seen:
            print(f"  caught {n - seen} dispatch event(s) so far, {n} total ({int(deadline - time.time())}s left)")
            seen = n
        else:
            print(f"  ...still listening ({int(deadline - time.time())}s left)")
    print(f"window over — {seen} dispatch event(s) captured")

    print("\n=== Cursor: log (action-key event sequences + dispatches) ===")
    log = adb._adb(serial, ["shell", "logcat", "-d"])
    seq = False
    for line in log.splitlines():
        if "Cursor:" in line and "KEY" not in line:
            print("  ", line[-130:])
            if "press resolved" in line or "long press" in line or "click at" in line:
                seq = True
    if not seq:
        print("  (no Cursor: dispatch lines — the action key may not have been pressed, "
              "or the cursor wasn't over the target)")

    title = cursor_tests._title(device).strip()
    print(f"\nDOM event log (last press): {title!r}")
    print("  (a 'CLICK' token alongside a long-press sequence = the bug reproduced)")

    out = os.path.join(os.path.dirname(__file__), "out", "action_key_seq.png")
    device.screenshot(out)
    print(f"screenshot -> {os.path.relpath(out)}")
    device.key(keys.BACK, wait=0.5)
    cursor_tests._toggle(device)


if __name__ == "__main__":
    main()
