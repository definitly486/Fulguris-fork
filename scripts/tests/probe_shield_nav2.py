"""Probe #2: why the SHIELD local-asset page never loads.

Checks: (1) does the device have curl and can it reach the tunneled localhost:8899?
(2) what does logcat say when we navigate to the local asset (WebView console / net errors)?
(3) can the WebView load a real internet URL at all (isolate tunnel vs general nav)?
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

import adb
import cursor_tests as ct
from framework import AndroidDevice

SERIAL = "192.168.178.37:5555"
PKG = "net.slions.fulguris.full.download.debug"
device = AndroidDevice(SERIAL)
ct._ensure_server()
ct._ensure_reverse(device)

print("== device curl availability ==")
print("which curl:", adb._adb(SERIAL, ["shell", "which", "curl"]).strip() or "(none)")
print("getprop ro.build.version.release:",
      adb._adb(SERIAL, ["shell", "getprop", "ro.build.version.release"]).strip())

print("\n== raw connect test to tunneled port (device-side) ==")
# toybox nc may exist; try a raw TCP connect with a timeout and report the error.
out = adb._adb(SERIAL, ["shell", "nc", "-w", "2", "-zv", "127.0.0.1", str(ct.PORT)])
print("nc 127.0.0.1:", (out or "").strip() or "(no output / nc missing)")

print("\n== navigate to local asset, capture logcat ==")
adb._adb(SERIAL, ["logcat", "-c"])
url = f"http://localhost:{ct.PORT}/cursor_target.html?cb={int(time.time() * 1000)}"
print("navigate:", url)
device.navigate(url, reset=True)
time.sleep(3.0)
print("field_text:", repr(device.field_text()))
log = adb._adb(SERIAL, ["logcat", "-d"])
interesting = [l for l in log.splitlines()
               if any(k in l for k in
                      ("chromium", "Console", "net::", "ERR_", "chromium:", "WebViewChromium",
                       "cursor_target", "8899", "localhost"))]
print(f"-- {len(interesting)} interesting logcat lines --")
for l in interesting[:40]:
    print("  ", l)

print("\n== navigate to a real internet URL (does general nav work?) ==")
adb._adb(SERIAL, ["logcat", "-c"])
device.navigate("https://example.com", reset=True)
time.sleep(4.0)
print("field_text after example.com:", repr(device.field_text()))
