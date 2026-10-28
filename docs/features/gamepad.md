# Gamepad control (Android TV cursor)

How a gamepad — particularly a *two-stick* gamepad like an Xbox controller — and a
D-pad remote drive the on-screen cursor, clicking, and scrolling on Android TV.
The remote-centric walkthrough (toggle, click vs deliberate-hold context menu,
media-key wheel, fade) is in [remote.md](remote.md); this document holds the
full key-map table and the gamepad-specific mechanics.

Implementation: `fulguris.cursor.CursorController` (a self-contained package), wired
into `WebBrowserActivity`, which forwards `dispatchKeyEvent` /
`dispatchGenericMotionEvent` to it before anything else. Settings:
`UserPreferences.cursor*` (see *Settings* below).

## Key map

| Input | Cursor off | Cursor on |
|---|---|---|
| **Right stick** (`AXIS_Z` / `AXIS_RZ`) | Moves the cursor (no toggle needed) | Moves the cursor |
| **Left stick** | Native WebView page scroll | Native WebView page scroll (untouched) |
| **D-pad — from a two-stick gamepad** | Focus navigation | Focus navigation — yielded back even with the cursor on, because the right stick is the cursor's driver |
| **D-pad — from a D-pad-only remote / virtual keyboard** | Focus navigation | Moves the cursor; select clicks |
| **LB** (`KEYCODE_BUTTON_L1`) | — (no browser role; ignored) | Mouse-wheel scroll **up** at the cursor (3 notches, repeats while held) |
| **RB** (`KEYCODE_BUTTON_R1`) | — (no browser role; ignored) | Mouse-wheel scroll **down** at the cursor |
| **A / D-pad center / ENTER** | Normal meaning (activate focused view, etc.) | Click at the cursor while the web content is focused (a *deliberate* hold, 0.5–1 s default 1 s, is a long press at the cursor → context menu); **if focus is on a toolbar widget / field, the key goes to that control** — it never clicks the page |
| **Play/pause — short press** | Play/pause the page's `<video>` | Same |
| **Play/pause — long press** | Toggle the cursor on/off | Toggle the cursor on/off |
| **Fast-forward** (media key) | Seek the page's `<video>` +10 s | Mouse-wheel scroll **up** at the cursor |
| **Rewind** (media key) | Seek the page's `<video>` −10 s | Mouse-wheel scroll **down** at the cursor |
| B, X, Y, Start, Back, Guide, LT/RT, stick clicks | Normal meaning (no mapping) | Same |

So the same physical wheel action has two sources: the **media keys** on a TV remote
(FF ≡ LB = up, REW ≡ RB = down) and the **shoulder buttons** on a gamepad. A standard
gamepad has no media keys at all, so without LB/RB it would have no wheel input — the
shoulder buttons are *the* wheel for gamepads.

## Why these choices

- **Right stick drives the cursor at any time, without toggling.** On a two-stick
  gamepad it is the natural "mouse" input, and `onGenericMotionEvent` never consumes
  it (returns `false`), so the left stick's native page scroll and D-pad focus
  navigation are left untouched.
- **The D-pad is yielded back on two-stick gamepads, even with the cursor on.** The
  gamepad's D-pad is a secondary input on that device — the stick is the cursor's
  driver — so the D-pad keeps its normal role (focus navigation) rather than also
  steering the cursor. D-pad-only remotes have no stick, so their D-pad *does* drive
  the cursor while it is on (that is their only way to move it).
- **The confirm key is yielded to the focused control when the web content is not focused.**
  With the cursor on, A / D-pad center / ENTER clicks at the cursor only while the web content
  (the tab's WebView) holds input focus. When focus is on a toolbar widget, the address field or
  a menu, the key goes to that control instead of clicking the page under the cursor — the
  cursor must not trap the confirm key away from the browser's own UI. In HTML5 fullscreen the
  WebView keeps focus, so the cursor keeps its click there.
- **The confirm key is yielded to the focused control when the web content is not
  focused.** With the cursor on, A / D-pad center / ENTER clicks at the cursor only while
  the web content (the tab's WebView) holds input focus. When focus is on a toolbar
  widget, the address field or a menu, the key goes to that control instead of clicking
  the page under the cursor — the cursor must not trap the confirm key away from the
  browser's own UI. In HTML5 fullscreen the tab is INVISIBLE (the custom fullscreen view
  is shown instead), which strips the WebView's focus — so the provider counts the
  fullscreen view as focused web content, and the cursor keeps its click there.
- **LB / RB for the wheel, not the triggers or stick clicks.** Shoulder buttons are
  discrete and auto-repeat — exactly the feel of wheel notches — and they are free
  (no other feature uses them; off-cursor they are simply ignored). The LT/RT
  triggers are analog and read as "throttle", and the thumbstick clicks clash with
  using the sticks. This complements, not duplicates, the left stick: the stick
  scrolls the *whole page* the WebView way, while LB/RB dispatch a synthetic mouse
  **wheel** (`ACTION_SCROLL`) at the cursor point, so whatever is *under the cursor*
  scrolls — including nested scrollable panels (e.g. a sidebar) — and at a WebView
  edge it scrolls the page, just like a real mouse wheel.
- **Two distinct scroll speeds coexist on purpose** — coarse (left stick) and
  targeted (LB/RB) — mirroring a real mouse-plus-trackpad setup.

## Detecting a "two-stick gamepad"

`hasRightStick(device)` requires **both** `AXIS_Z` and `AXIS_RZ` to exist with a
*centered* motion range (`min < 0`), which excludes devices that report their
triggers on Z/RZ (range 0..1). The same check gates the right-stick driver *and* the
D-pad yield, so the two behaviours can never disagree about which device counts.

One Android quirk this relies on: an Xbox D-pad is a HAT axis (`SOURCE_JOYSTICK`
motion, `AXIS_HAT_X/Y`), not a real D-pad key. The framework's
`SyntheticInputStage` synthesizes DPAD `KeyEvent`s from unhandled HAT motion, and the
synthesized key **carries the original joystick source and device** — which is why
`hasRightStick(event.device)` sees the gamepad for those keys.

## Settings

| Preference key | Setting | Default |
|---|---|---|
| `pref_key_cursor_hotkey` | Allow the play/pause long-press to toggle the cursor (the menu item works regardless) | — |
| `pref_key_cursor_speed` | Cursor speed, 0–100 % | 30 |
| `pref_key_cursor_acceleration` | Acceleration while a direction is held, 0–100 % | 30 |
| `pref_key_cursor_fade_timeout` | Seconds of no movement after which the cursor fades out; 0 = never | 3 |
| `pref_key_cursor_action_hold` | Seconds the action key must be deliberately held for the context-menu long press (0.5–1 s, clamped to ≥ 0.5) | 1.0 |

Speed and acceleration are **physical** (cm/s and cm/s² converted to pixels via the
display DPI), so a given setting feels comparable on any screen.

## Related behaviours

- **Edge scroll:** with the cursor on and at the WebView's edge, continuing to move
  (D-pad or stick) dispatches the synthetic wheel at the cursor point instead of
  letting the cursor leave the screen.
- **HTML5 fullscreen:** the cursor overlay is re-parented above the fullscreen custom
  view and its synthetic events are re-targeted there, so the cursor and its wheel
  work over fullscreen video.
- **Menu item** ("Cursor"): shown on leanback or when a gamepad / joystick / D-pad
  device is connected, and kept live as devices connect/disconnect.

## Validating test groups

`scripts/tests/cursor_tests.py`, run with:

```powershell
python scripts/tests/run.py --all --group cursor-wheel     # FF/REW + LB/RB wheel at the cursor
python scripts/tests/run.py --all --group cursor-movement  # D-pad movement, edge scroll, gamepad D-pad yield
python scripts/tests/run.py --all --group cursor           # every cursor test
```

- `test_cursor_wheel_ff_rewind_scrolls` — with the cursor on, rewind / RB scroll the
  page down at the cursor and fast-forward / LB scroll it back up (read from the
  `sy<n>` title the local `cursor_target.html` reports as `window.scrollY`).
- `test_cursor_movement_gamepad_dpad_yields_to_focus_nav` — injects the gamepad's D-pad
  hat via `sendevent` (so the synthesized key carries the gamepad as source) and
  asserts the page does **not** scroll while the cursor is on, then asserts the
  stick-less D-pad still moves it. Skips with a note when no gamepad is connected.
