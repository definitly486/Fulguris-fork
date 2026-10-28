"""One-off: disable the toolbar auto-hide on the SHIELD (landscape config) so the cursor
tests can read the page title from the toolbar label. The cursor suite depends on the toolbar
being visible (it reads document.title via the toolbar label / field_text).

    python scripts/tests/reset_shield_toolbar_hide.py [--device SERIAL]
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import adb  # noqa: E402

LOCAL_TMP = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".temp", "tb_hide.xml"))


def _set_bool(xml: str, key: str, value: str) -> str:
    pat = re.compile(rf"<boolean name=['\"]{key}['\"] value=['\"][^'\"]*['\"] />")
    entry = f'<boolean name="{key}" value="{value}" />'
    return pat.sub(entry, xml) if pat.search(xml) else xml


def _set_float(xml: str, key: str, value: str) -> str:
    pat = re.compile(rf"<(float|int) name=['\"]{key}['\"] value=['\"][^'\"]*['\"] />")
    entry = f'<float name="{key}" value="{value}" />'
    return pat.sub(entry, xml) if pat.search(xml) else xml


def main() -> None:
    args = sys.argv[1:]
    serial = "192.168.178.37:5555"
    if "--device" in args:
        serial = args[args.index("--device") + 1]
    pkg = adb.detect_package(serial)
    # The landscape config file (the TV runs landscape). Disable the auto-hide + timeout.
    adb.force_stop(serial, pkg)
    time.sleep(1.0)  # let it exit so it can't overwrite the file on shutdown
    changed = False
    for fname in (f"{pkg}_preferences_landscape.xml", f"{pkg}_preferences.xml"):
        rel = f"shared_prefs/{fname}"
        try:
            xml = adb._adb(serial, ["shell", "run-as", pkg, "cat", rel])
        except Exception:
            continue
        if "pref_key_hide_tool_bar" in xml or "pref_key_hide_tool_bar_timeout" in xml:
            new = _set_bool(xml, "pref_key_hide_tool_bar", "false")
            new = _set_float(new, "pref_key_hide_tool_bar_timeout", "0.0")
            if new != xml:
                with open(LOCAL_TMP, "w", encoding="utf-8", newline="\n") as f:
                    f.write(new)
                dev_tmp = "/data/local/tmp/fw_tb.xml"
                subprocess.run(["adb", "-s", serial, "push", LOCAL_TMP, dev_tmp], capture_output=True)
                subprocess.run(["adb", "-s", serial, "shell", "run-as", pkg, "cp", dev_tmp, rel],
                               capture_output=True)
                print(f"wrote {rel}")
                changed = True
    if not changed:
        print("nothing to change (auto-hide already off?)")
    adb.restart(serial, pkg)
    print("done")


if __name__ == "__main__":
    main()
