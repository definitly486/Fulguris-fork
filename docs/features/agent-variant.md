# Agent flavor

A dedicated **PUBLISHER-dimension flavor** for **AI-agent automated testing**:
`agent`. Like the other publisher flavors (`download`, `playstore`, `fdroid`) it
adds an application-id suffix (`.agent`), and like them it pairs with the
standard `debug` / `release` build types:

| Variant                | Build type | Minified | Debuggable (`run-as`, logcat) | Application id              |
|------------------------|------------|----------|-------------------------------|-----------------------------|
| `slionsFullAgentDebug`   | `debug`    | no       | yes                           | `net.slions.fulguris.full.agent.debug`   |
| `slionsFullAgentRelease` | `release`  | yes      | no                            | `net.slions.fulguris.full.agent`        |

The agent flavor carries a **distinct launcher icon** (the app's lightning bolt,
cut horizontally into two pieces, so it reads as "split") so an agent-driven
install is distinguishable in the launcher, and a **distinct application id** so
it installs *alongside* a developer's own debug/release builds on the same device
instead of clobbering them.

## Why it exists

The automated test harness (`scripts/`) builds, installs, `run-as`es and relaunches
the app on real devices. If it used the plain `slionsFullDownloadDebug` variant,
every agent-driven build/install would overwrite the developer's own debug install
and wipe its state. The agent flavor gives agents their own, unmistakable package:
the split-bolt icon in the launcher (on the debug-green background for debug
builds) is the visual cue that "this is the test build, not mine".

- The **test harness builds `slionsFullAgentDebug`** — it needs a debuggable app
  (the cursor suite rewrites shared prefs via `run-as`, and the probes read
  `logcat`). `slionsFullAgentRelease` exists for testing minified/shrunk builds.
- The agent flavor **does not apply the Firebase plugins** (only `download` and
  `playstore` do, see `app/build.gradle`), so no `google-services.json` entry is
  needed and no Firebase SDK is linked. It is a local-only testing flavor and is
  never published anywhere.

## Files

- **`app/build.gradle`** — the `agent` product flavor (`dimension "PUBLISHER"`,
  `applicationIdSuffix ".agent"`, `SPONSORSHIP` = BRONZE like `download`).
- **`app/src/agent/res/drawable/ic_launcher_foreground.xml`** — the *split*
  bolt foreground (white): the app's bolt polygon cut horizontally at `y=13.9`
  into two filled pieces, with the lower (tail) piece shifted right by ~1.4
  units so the pieces don't line up — a clean "impact" gap between them.
  Flavor source set, so it covers both the debug and release variants.
- **`app/src/agent/res/drawable/ic_launcher_monochrome.xml`** — the same split
  bolt in black, for themed (Material You) icon rendering.
- **`app/src/agent/res/mipmap-anydpi-v26/ic_launcher{,_round}.xml`** — adaptive
  icons that keep the *standard* background color (debug builds get the
  debug-green background override from the `debug` source set) but use the
  split-bolt foreground (flavor source set, so it covers both the debug and
  release variants). Only `anydpi-v26` is overridden; the bitmap mipmaps in the
  other densities are unused by the adaptive icon on API 26+ and are harmless.
- **`app/src/agent/java/fulguris/settings/fragment/SponsorshipSettingsFragment.kt`**
  — the per-publisher implementation of the abstract
  `RedirectSponsorshipSettingsFragment` (referenced by name from the main
  settings code and preference XML), same redirect behavior as `download`.
- **`app/src/agent/java/fulguris/Firebase.kt`** — no-op stubs of
  `setAnalyticsCollectionEnabled` / `setCrashlyticsCollectionEnabled` (the main
  code calls them unconditionally; each publisher flavor provides its own
  implementation, `download`/`playstore` the real Firebase ones, `fdroid` and
  `agent` no-ops).

## Building & installing

The tooling in `scripts/tools/` is pointed at the agent flavor by default; pass
`--build-type agentRelease` to use the release build instead.

```powershell
python scripts/tools/build.py                              # build agentDebug (default)
python scripts/tools/build.py --build-type agentRelease
python scripts/tools/install.py --build --all              # build + install agentDebug on all devices
python scripts/tools/install.py --build --all --build-type agentRelease
```

The test runner is unchanged — it installs/launches the default Agent package:

```powershell
python scripts/tests/run.py --device SERIAL --group smoke
```

APK locations:

- `app/build/outputs/apk/slionsFullAgent/debug/*.apk`
- `app/build/outputs/apk/slionsFullAgent/release/*.apk`

## Android Studio default variant

The agent flavor must **not** be the IDE's default build variant — developers
still build and run `slionsFullDownloadDebug` from Android Studio. The IDE
derives its default from the first flavor of each dimension (adding `agent`
made `slionsFullAgentDebug` the default, since `agent` sorts before
`download`). `app/build.gradle` therefore sets `isDefault = true` once per
dimension — on `slions`, `full` and `download` — which pins the IDE default to
`slionsFullDownloadDebug` for everyone who opens the project, without touching
the (gitignored) per-user IDE state. The scripts are unaffected: they name the
agent variant explicitly (`AGENT_VARIANTS` in `scripts/tools/adb.py`).

## Gotchas

- **Never install the Agent build over a regular one or vice versa** — they are
  different packages and coexist by design.
- The agent application id stacks the usual suffixes: flavor `.full` + publisher
  `.agent` (+ build type `.debug`), i.e. `net.slions.fulguris.full.agent.debug`.
- The `variantFilter` in `build.gradle` does not restrict the agent flavor — it
  combines with any BRAND/VERSION, though only `slionsFull` is meaningful.
