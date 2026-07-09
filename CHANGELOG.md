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

### Added
- **Launcher: fullscreen apps are now browse-in-place.** For a config with `fullscreen:true`
  (stencil, wallpaper), the glasses open **directly into the fullscreen view** (newest item, no
  list step) and **D-pad ↑/↓ switches to the prev/next item** without leaving it; the footer
  shows `n/total`. Came from the stencil Define round ("glasses with AR effect main driver…
  one stencil at a time, navigate with D-pad"). Both launchers. **Gate:** human-eyeballed lines
  in `apps/stencil/acceptance.md`/`verdict.md` (UI-only; no-build rule).

### Added (2)
- **The loop is now an enforced state machine.** Second user finding of the session: after fixing
  permissions, the loop still relied on the *user* asking "what's next". Now the state is explicit
  and machine-checked, the way mature repos do it (`git status` model + hook enforcement):
  - **`tools/loop_state.py`** computes each app's state from artifacts (DEFINE → VERIFY → FIX →
    SYNC → DEPLOY → COMMIT → DONE) — incl. a live HTTP compare of the deployed worker vs
    `worker/public` — and prints THE next action. `status.py` embeds the table.
  - **Stop hook** (`.claude/settings.json`): an agent stopping while an agent-actionable
    transition remains on an app it touched (git-dirty) gets blocked once and the next action fed
    back (`stop_hook_active` honored, so it can't loop). Clean/committed apps that predate a gate
    are *backlog*, never nagged.
  - **Runbook rule** (AGENTS.md "STATE MACHINE"): advance any state that needs no user input in
    the same turn; on red gates self-fix up to ~3 iterations before asking; end turns only at DONE
    or a user gate, handing over one crisp ask. **Gate:** the Stop hook itself.

### Added (3)
- **Clean & commit is a loop state.** `tools/commit_prep.py` prepares the hand-off: hygiene
  hard-gate (placeholder `database_id`, no tracked secret files, credential/UUID scan of dirty
  files, leftover junk) plus a suggested grouping of dirty files into logical conventional
  commits (per app / kit / harness / docs). `loop_state.py` gained a **CLEAN** state (hygiene
  failures are agent-actionable → Stop-hook enforced); COMMIT stays the user gate but arrives
  pre-structured. Runbook: message rules (imperative ≤ 72-char `type(scope):` subject, body =
  the why). **Gate:** `commit_prep.py` exits 1 on hygiene failure.

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
