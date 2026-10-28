# D-pad remote control (Android TV cursor)

How a standard Android TV **D-pad remote** — no analog sticks — drives the
on-screen cursor: toggling it on, moving it, clicking, opening the context menu,
and scrolling. (For a *two-stick* gamepad — Xbox, DualShock, … — see
[gamepad.md](gamepad.md); the two documents are complements, and the full
key-map table lives there.)

Implementation: `fulguris.cursor.CursorController` (a self-contained package),
wired into `WebBrowserActivity`, which forwards `dispatchKeyEvent` /
`dispatchGenericMotionEvent` to it before anything else. Settings:
`UserPreferences.cursor*` (shared with the gamepad — see *Settings* below).

## Key map (D-pad remote)

| Input | Cursor off | Cursor on |
|---|---|---|
| **D-pad directions** | Focus navigation (normal UI) | Moves the cursor; auto-repeat accelerates it |
| **Select / D-pad center / ENTER** | Normal meaning (activate the focused view, confirm dialogs) | **Click** at the cursor *while the web content is focused*; a *deliberate* hold (0.5–1 s, default 1 s) is a **long press** at the cursor → context menu. **If focus is on a toolbar widget / field, the key goes to that control** — it never clicks the page |
| **Play/pause — short press** | Play/pause the page's `<video>` | Same (the hotkey is the *long* press) |
| **Play/pause — long press** | Toggle the cursor on/off | Toggle the cursor on/off (gated by `pref_key_cursor_hotkey`; the menu item works regardless) |
| **Fast-forward** (media key) | Seek the page's `<video>` +10 s | Mouse-wheel scroll **up** at the cursor (3 notches, repeats while held) |
| **Rewind** (media key) | Seek the page's `<video>` −10 s | Mouse-wheel scroll **down** at the cursor |
| **BACK** | Normal meaning (back in history, re-show a hidden tool bar, …) | Same — BACK re-shows a hidden tool bar (see [toolbar-hide-timeout.md](toolbar-hide-timeout.md)) |

A remote has **no right stick**, so `hasRightStick(device)` is false for it and
its D-pad keys are never yielded: with the cursor on, the D-pad is the remote's
only way to move the cursor. The same holds for **adb's virtual keyboard**
(`input keyevent`) — it has no stick either, which is how the automated tests
drive the remote path.

## Toggle: the play/pause long-press

The hardware hotkey is a **long press of `KEYCODE_MEDIA_PLAY_PAUSE`** (the
default `pref_key_cursor_hotkey`). Media keys do not reliably deliver a system
long-press, so the controller arms its own timer on `ACTION_DOWN` (threshold =
the system long-press timeout, clamped to at least 500 ms) and cancels it on
`ACTION_UP`; it also honors a real `FLAG_LONG_PRESS` event as a secondary
trigger. While timing the long press the `DOWN` is consumed so it never reaches
a page `MediaSession`. On `ACTION_UP` a completed long press is consumed
(toggle) and a short press is yielded back to the activity, which plays/pauses
the page's `<video>`.

With the cursor **off** the play/pause short press is bridged to the active
`<video>` via `evaluateJavascript` (generic; cross-origin iframes are not
reachable — a known limitation).

## Click vs context menu: the deliberate hold

While the cursor is on, the action key (`KEYCODE_DPAD_CENTER` /
`KEYCODE_ENTER` / `KEYCODE_NUMPAD_ENTER` / `KEYCODE_BUTTON_A`) performs the
primary interaction at the cursor:

- **Short press → click.** The click is a synthetic touch
  DOWN→MOVE→UP at the cursor point (synthetic *mouse button* events cannot be
  turned into a page click through the public API on Android WebView; the 2 px
  MOVE is what makes drag-only targets, e.g. a video scrub bar, seek).
- **Deliberate hold (0.5–1 s, `pref_key_cursor_action_hold`) → long press** at
  the cursor → the WebView's context menu for the element under it.

The click is deferred to the key `UP` so a held press can still be reclassified
as a long press while it is held; if the hold timer already fired, the `UP` is
consumed and no click follows.

**The confirm key follows focus.** All of the above applies while the *web
content* is focused. If focus is on a toolbar widget, the address field or a
menu, the confirm key activates that control instead of clicking the page under
the cursor — the cursor never traps the confirm key away from the browser's own
UI. (In HTML5 fullscreen the tab is INVISIBLE — the custom fullscreen view is shown
  instead — so the provider counts the fullscreen view as focused web content and the
  cursor keeps its click there.)

**The OS's own `FLAG_LONG_PRESS` is deliberately ignored on this path.** A human
"short click" on a remote is routinely held 400–700 ms — past the ~400 ms at
which the OS starts flagging the key's repeat events as long-press. Honoring the
flag would reclassify hesitant clicks as long presses and open the context menu
instead of clicking (this was a real bug). The hold threshold is therefore
user-configurable but clamped to at least 500 ms, well past the system flag.

The synthetic long press is a touch DOWN held for the system long-press timeout
+ 150 ms, with the terminating CANCEL sent ~300 ms *after* that — a cancel
before the long-press dialog appears (and steals window focus, ~560 ms after
the DOWN) wedges the renderer's input state just like a premature UP.

## Scrolling: the media keys are the wheel

With the cursor on, `KEYCODE_MEDIA_FAST_FORWARD` / `KEYCODE_MEDIA_REWIND`
dispatch a synthetic mouse wheel (`MotionEvent.ACTION_SCROLL`, 3 notches each,
`WHEEL_NOTCHES`) at the cursor point — the same input a gamepad produces with
its LB/RB shoulder buttons (see [gamepad.md](gamepad.md)). The engine hit-tests
whatever is under the cursor, so a nested scrollable panel (a sidebar, a
carousel) scrolls instead of the whole page, and at a WebView **edge** the
wheel scrolls the page while the cursor stays clamped to the edge ("edge
scroll"). Each press repeats while the key is held. With the cursor off the
same keys fall through to the ±10 s `<video>` seek.

## Fade

The cursor fades out after `pref_key_cursor_fade_timeout` seconds of no
movement (default 3 s; 0 = never) and fades straight back in on any movement
(D-pad step, wheel press, or the cursor re-showing a hidden tool bar). A single
D-pad tap applies an immediate physical step, so a discrete remote press always
nudges the cursor even though it releases almost instantly; holding the key
then accelerates via the `Choreographer` frame loop. Speed/acceleration are
physical (cm/s, cm/s² converted to pixels via display DPI) so a setting feels
comparable on any screen.

## HTML5 fullscreen

The overlay is re-parented above the fullscreen custom view and the synthetic
events are re-targeted there, so the cursor, its click, and the media-key wheel
work over fullscreen video (e.g. YouTube); reversed on exit.

## Interaction with the tool bar auto-hide

The cursor overlay is **not focusable**: while the cursor is on, the WebView
keeps input focus the whole time, so the "Hide tool bar after" auto-hide
([toolbar-hide-timeout.md](toolbar-hide-timeout.md)) arms and fires exactly as
without the cursor. With the tool bar hidden and the cursor on, **BACK is the
remote idiom to re-show it** — and re-showing the bar while the WebView holds
focus re-arms the countdown, so the cycle (hide → BACK → hide) works.

## Settings

Same preferences as the gamepad path (see [gamepad.md](gamepad.md)):
`pref_key_cursor_hotkey`, `pref_key_cursor_speed`,
`pref_key_cursor_acceleration`, `pref_key_cursor_fade_timeout`,
`pref_key_cursor_action_hold`.

## Validating test groups

`scripts/tests/cursor_tests.py` drives the remote path with adb's virtual
keyboard (no right stick → exactly the remote branch):

```powershell
python scripts/tests/run.py --all --group cursor-movement  # D-pad moves the cursor, edge scroll
python scripts/tests/run.py --all --group cursor-click     # hover, click, drag-target, hesitant press
python scripts/tests/run.py --all --group cursor-wheel     # media keys scroll at the cursor
python scripts/tests/run.py --all --group cursor-context   # deliberate hold opens the context menu
python scripts/tests/run.py --all --group cursor-toggle    # play/pause long-press toggle
python scripts/tests/run.py --all --group cursor-fade      # fade-out and wake
```

The tests read back what happened from the toolbar label (the mirrored page
title) rather than screenshots — the local pages under `scripts/tests/assets/`
set `document.title` to report hover, click coordinates, scroll position, and
context-menu state.
