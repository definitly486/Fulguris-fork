"""Probe: diagnose the SHIELD's app/foreground/screen state after a wedged test run.

Standalone; run:  python scripts/tests/probe_shield_state.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import adb  # noqa: E402

SERIAL = "192.168.178.37:5555"


def lines(grep, out):
    return [l for l in out.splitlines() if grep in l]


def main():
    pkg = adb.detect_package(SERIAL)
    print("package:", pkg)

    act = adb._adb(SERIAL, ["shell", "dumpsys", "activity", "activities"], timeout=30)
    print("\n-- resumed/top activity lines --")
    for l in lines("esumed", act):
        print("  ", l.strip()[:160])
    for l in lines("mFocusedApp", act):
        print("  ", l.strip()[:160])

    print("\n-- foreground_package() ->", adb.foreground_package(SERIAL))
    print("-- view_present('search') ->", adb.view_present(SERIAL, "search"))

    top = adb._adb(SERIAL, ["shell", "dumpsys", "activity", "top"], timeout=30)
    print("\n-- top activity line --")
    for l in lines("ACTIVITY", top[:top.find("View Hierarchy") if "View Hierarchy" in top else 2000]):
        print("  ", l.strip()[:160])
        break

    pid = adb._adb(SERIAL, ["shell", "pidof", pkg], timeout=15).strip()
    print("\n-- pidof ->", pid or "<not running>")

    power = adb._adb(SERIAL, ["shell", "dumpsys", "power"], timeout=30)
    print("\n-- power / wakefulness --")
    for l in lines("mWakefulness", power):
        print("  ", l.strip()[:120])
    for l in lines("Display Power", power):
        print("  ", l.strip()[:120])

    print("\ndone")


if __name__ == "__main__":
    main()
