"""
Probe: after each synthetic action-key long press, dump the FULL DOM event-log title
so we can see whether the page receives our late ACTION_CANCEL (tc at ~850ms) the way
a real touch receives the input-pipeline cancel (tc at ~564ms).

Usage:
    python -u scripts/tests/probe_late_cancel_domlog.py --device 192.168.178.67:5555 [--presses 3]
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import cursor_tests  # noqa: E402
import framework  # noqa: E402
from framework import keys  # noqa: E402

SERIAL = "192.168.178.67:5555"


def _arg(name: str, default: str) -> str:
    args = sys.argv[1:]
    if name in args:
        return args[args.index(name) + 1]
    return default


def main() -> None:
    serial = _arg("--device", SERIAL)
    presses = int(_arg("--presses", "3"))
    device = framework.AndroidDevice(serial)
    device.settle()

    cursor_tests._ensure_server()
    cursor_tests._load_page(device, "longpress_log.html")
    cursor_tests._toggle(device)

    for i in range(1, presses + 1):
        device.key_hold(keys.DPAD_CENTER, 1500)
        time.sleep(1.2)
        title = cursor_tests._title(device).strip()
        print(f"press {i}  DOM log: {title}")
        device.key(keys.BACK, wait=1.0)

    device.key(keys.BACK, wait=0.5)
    cursor_tests._toggle(device)


if __name__ == "__main__":
    main()
