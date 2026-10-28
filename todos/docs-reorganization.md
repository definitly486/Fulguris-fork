# Todo: Reorganize documentation (user manual in the wiki, dev docs in the repo)

**Status:** planned (a full implementation was attempted on 2026-08-24 and then **reverted** —
both trees are clean again; nothing from it was ever committed)

## Goal

The GitHub wiki (`subs/wiki`, a submodule with its own repo) currently mixes two audiences:

- **user-facing** pages: `Home.md` (a one-line stub), `Android-TV.md` (already a proper
  user-friendly manual page — keep it as the model)
- **developer-facing** pages: `Tips.md`, `Tools.md` + `Tools/` (8 sub-pages), `Devices.md`,
  `WebView.md`, `Content-Control.md`

Decision: the **wiki becomes the user manual only**. Developer docs move into the source
tree under `docs/developer/` (next to the existing `docs/features/`).

## Steps

### 1. Main repo — copy the dev pages into `docs/developer/`

Copy from `subs/wiki` (lowercase file names, matching the `docs/` convention; keep the
tool sub-pages with their original names under `tools/`):

| From (wiki)                | To (repo)                          |
| -------------------------- | ---------------------------------- |
| `Tips.md`                  | `docs/developer/tips.md`           |
| `Devices.md`               | `docs/developer/devices.md`        |
| `Content-Control.md`       | `docs/developer/content-control.md`|
| `WebView.md`               | `docs/developer/webview.md`        |
| `Tools.md`                 | `docs/developer/tools.md`          |
| `Tools/ADB.md`             | `docs/developer/tools/ADB.md`      |
| `Tools/Affinity Designer.md` | `docs/developer/tools/Affinity Designer.md` |
| `Tools/Android Studio.md`  | `docs/developer/tools/Android Studio.md` |
| `Tools/App Manager.md`     | `docs/developer/tools/App Manager.md` |
| `Tools/browserleaks.com.md`| `docs/developer/tools/browserleaks.com.md` |
| `Tools/Gradlew.md`         | `docs/developer/tools/Gradlew.md`  |
| `Tools/SVG Path Editor.md` | `docs/developer/tools/SVG Path Editor.md` |
| `Tools/WSA.md`             | `docs/developer/tools/WSA.md`      |

### 2. Fix the cross-links in the moved pages (39 links across 9 files)

All links use the wiki URL form `[label](/Slion/Fulguris/wiki/<Page>)`. Rewrite rules:

- The **8 tool pages** that were moved → relative links to the new files
  (e.g. `[ADB](tools/ADB.md)` from `tools.md`, `[ADB](ADB.md)` from within `tools/`).
- `Building` / `Testing` (never existed in the wiki) → link to `AGENTS.md`
  (the build/test workflow lives there; path from `docs/developer/tools/*` is
  `../../../AGENTS.md`, from `docs/developer/*` is `../../AGENTS.md`).
- Any other target that never existed in the wiki (`Geolocation`, `Privacy`, `Icons`,
  `Branding`, `ClientHints`, …) → **unlinked plain text** (no dead links).
- ⚠️ Do **not** touch `github.com/gorhill/uBlock/wiki/...` links inside
  `content-control.md` — those are external references, not our wiki.

A one-off regex script (`re.sub` over `\[([^\]]+)\]\(/Slion/Fulguris/wiki/([^)]+)\)`)
worked well for this — write it to `.temp/` rather than running inline.

### 3. Main repo — `README.md`

Replace the `# Documentation` section's single line
("Visit our wiki … development and testing tools"):

```markdown
# Documentation

* [User manual](https://github.com/Slion/Fulguris/wiki) - how to use Fulguris on phones, tablets and Android TV.
* [`docs/`](docs/) - developer documentation: feature notes in [`docs/features/`](docs/features/) and the development & testing tooling reference in [`docs/developer/`](docs/developer/).
```

### 4. Wiki repo (`subs/wiki`) — stage the deletions

`git rm` the 13 pages from step 1 (then remove the now-empty `Tools/` folder).
Keep `Home.md`, `Android-TV.md`, `_Sidebar.md`, `_Footer.md`.

### 5. Wiki repo — turn it into the user manual

- **`Home.md`** — landing page: "This is the user manual", start-here links
  (Getting Started, Android TV), and a "Not the manual you're after?" section pointing
  developers at [`AGENTS.md`](https://github.com/Slion/Fulguris/blob/main/AGENTS.md) and
  [`docs/`](https://github.com/Slion/Fulguris/tree/main/docs) in the main repo
  (branch is **`main`**, not `master` — the wiki branch is `master`).
- **`_Sidebar.md`** — two sections:
  - **User manual**: Home, Getting Started, Android TV
  - **Developers**: links into the repo (docs tree + AGENTS.md)
- **`Getting-Started.md`** (new) — first manual page. Outline that worked well:
  1. Installing (the 3 channels: Google Play / Slions.net / F-Droid, all co-installable)
  2. The layout (address bar, tab strip, menu ⋮, back/forward/reload; toolbar
     auto-hides on phones, always shown on TV unless "Hide tool bar after" is set)
  3. Browsing (address vs search, links, tabs, back/forward, reload)
  4. Bookmarks / history / downloads (all via Menu ⋮)
  5. A tour of the settings pages (General, Tabs, Privacy, Content blocking,
     Extensions, Menus, Downloads, Scrollbars, Page history/Requests, Backup, About —
     verify against `app/src/main/java/fulguris/settings/fragment/*`)
  6. First things to check on a new device

  Keep claims limited to what's verifiable in code/strings — do not invent UI labels.

## Gotchas learned during the attempt

- `subs/wiki` is a **git submodule** → it needs its own commit (separate from the app
  repo). The two halves of the move are independent; commit order doesn't matter.
- The wiki's `Tools.md` links to pages that were never created (`Building`, `Testing`,
  `Geolocation`, …) — pre-existing dead links, fixed as part of the move.
- `Android-TV.md` is already written for end users (cursor, game controllers, video,
  settings) — leave it untouched, it is the tone/structure reference for the manual.
- `Tips.md` and `Tools/ADB.md` etc. are fine as dev docs once moved; no content changes
  were needed beyond the link rewrites.
- After the move, the wiki sidebar is the only user-visible index — make sure every wiki
  page is reachable from it.

## Out of scope (possible follow-up manual pages)

- Settings in depth (privacy, content blocking, extensions, backups)
- Per-device guides (phone/tablet specifics, Chromebook/WSA for users)
- A "What's new" page sourced from `CHANGELOG.md`
