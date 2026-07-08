# Changelog — kit learnings

This file is the **"harden"** half of the build loop (see `AGENTS.md` §D). When a user tests a live
app and something breaks, fix it — and if the fix is **kit-level** (helps every fork, not just one
app), log it here and, where possible, leave behind a regression **gate** so it can't recur.
App-specific fixes do **not** belong here. Because this repo is a **template others fork**, kit-level
changes should be human-reviewed before they ship.

**Convention:** every escaped, kit-level bug should leave a fast, deterministic gate — prefer a
`tools/flowtest.py` assertion or a `tools/check.py` rule. Surface/UI checks that can't be automated
cheaply (no-build rule) stay as human-eyeballed lines in an app's `acceptance.md` / `verdict.md`
(the soft gate), not brittle end-to-end automation.

## 2026-07-09 — from user feedback on the build loop (stencil session)

### Changed
- **Runbook: define → plan surfaces → build (don't run with the idea).** AGENTS.md's Define phase
  previously discouraged clarifying questions ("at most 1–2 — often zero"); in practice agents
  jumped straight from a one-line idea to a built app. The loop now **opens with 2–3 important
  definition questions** (what one item holds, the consuming moment / does-it-belong-on-the-glasses,
  the key action) **plus an explicit per-surface plan** — glasses vs mobile vs desktop, each with
  what it shows/does or a *"skipped, because…"* — green-lit once before building. Questions stay
  front-loaded: after that single go-ahead the run is still unattended end-to-end. **Gate:**
  human-eyeballed — an app's `acceptance.md` must carry the surface plan and the answered
  questions/assumptions (question quality isn't scriptable; review it there).

## 2026-07-08 — from a live-testing session (flashcards + presentation timer)

### Fixed
- **Worker: bulk upsert didn't un-delete.** `POST /api/:collection/bulk` updated only `data`+`updated`
  on conflict, so a soft-deleted row (e.g. a push-fed feed's single `current` id) stayed hidden
  forever — the app reported "Synced" but showed nothing. The upsert now also wins on
  `seen`/`fav`/`deleted`. **Gate:** `flowtest.py` asserts *"bulk upsert un-deletes a soft-deleted row."*
- **Launcher: settings were keyboard-only.** "settings" opened only via the `S` key, so a phone with a
  wrong stored URL/password could get stuck offline with no way to fix it. Now a tappable ⚙ settings link.
- **Per-app HTML wasn't first-class.** `control.html` was a hand-committed duplicate that `sync_public`
  never mirrored and `check` never validated. Now sync copies/prunes/drift-checks per-app `*.html`,
  `check.py` syntax-checks per-app page scripts, and `verify_hook.py` trips on per-app HTML edits.

### Added
- **Page apps (endpoints).** A config may set `"control": "<file>.html"`; on phone/desktop the launcher
  opens that endpoint directly (credentials passed through, so it's zero-setup), while the glasses show
  the config-driven display. First user: the presentation timer.
- **Launcher HUD refresh.** Per-app accent colors + a focus glow, tuned for the additive glasses display.
- **Image fields.** Drag-and-drop on desktop, paste-or-link on mobile, auto-downscaled to keep D1 small.
