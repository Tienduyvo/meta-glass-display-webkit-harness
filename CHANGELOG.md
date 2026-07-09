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

## 2026-07-09 — from user feedback on live testing (daily-ritual session)

### Fixed
- **Launcher: background `refresh` cut off playing audio mid-sentence.** A `refresh:<n>` app
  re-fetches and calls `render()`, which rebuilt the detail DOM and destroyed a playing
  `<audio>` element — so any program longer than the refresh interval was chopped (found on
  device: "sounds are being cut off mid sentence"). Now `refresh()` skips the re-render while
  audio is playing (`audioPlaying()` guard), so playback survives at ANY clip length
  regardless of the interval. Both launchers. **Gate:** `exports/verify_audio_backdrop.py`
  forces a refresh mid-playback and asserts the audio keeps playing.

### Added (immersive)
- **Launcher: `audioImages: [urls]` — foreground inspiring images during playback.** While an
  `audio` program plays in the detail view, the app's OWN bundled images (a self-contained
  list, NOT another app's collection) show full-bleed in the FOREGROUND, rotating every 12 s —
  an immersive "feel inspired" moment; tap toggles pause, ← exits, removed on pause/leave.
  daily-ritual ships 6 bundled images (`/media/inspire/*.png`: warm radial glows + uplifting
  words, bright-centre/dark-edge so they read on the additive display too). Supersedes the
  earlier dimmed-backdrop-from-wallpaper approach per user feedback ("separate, not from the
  wallpaper app; foreground not background"). Both launchers. **Gate:**
  `exports/verify_inspire.py` asserts the overlay is full-bleed on play, rotates, keeps audio
  alive across a refresh, and is removed on leave. (App content, per later user feedback: the
  inspire images are TEXT-FREE — words on-screen while audio plays is too much at once — and
  the seed keeps only real human LibriVox readings; the synthetic TTS programs were removed.)
  **Follow-up fix:** the overlay must NOT be gated on the audio `play` event — audio is
  device-limited on the glasses, so a play-gated overlay never showed there. `wireInspire()`
  now opens the overlay on entering an audio item's detail, independent of audio (best-effort
  playback). Also swapped the generated gradient images for 6 real nature photographs
  (Wikimedia Commons, CC-BY-SA, `/media/inspire/nature*.jpg` + ATTRIBUTION.txt). Gate:
  `exports/verify_inspire_noaudio.py` blocks `HTMLMediaElement.play()` and asserts the image
  still appears, loads, and rotates.

### Fixed
- **Launcher: ▶ Open (link/video) was a dead button wherever popups are blocked — including
  the glasses.** `openURL()` only fell back to `location.href` when `window.open` *threw*, but a
  blocked popup returns `null` without throwing, so on the glasses webview the action silently
  did nothing (found by the user on-device: "youtube link doesnt work"). Now a null return
  falls back to in-place navigation. Both launchers. **Gate:** `exports/repro_open_play.py`
  simulates the blocked-popup device (`window.open = () => null`), presses Enter on ▶ Open
  Play and asserts the URL changes; UI line noted in `apps/daily-ritual/verdict.md`.
  Lesson folded into testing practice: verify a link action by *driving the tap end-to-end*
  under device-realistic conditions, not by checking the target URL exists.

### Added (loop hardening — "agent stopped nowhere")
- **The loop can no longer be lost between sessions.** User finding: the agent still stranded
  the loop mid-flow — a crashed/compacted session bypasses the Stop hook entirely (no stop
  event → no enforcement), and re-orientation relied on a CLAUDE.md sentence (hope, not code).
  Two code-level fixes, completing the state-machine work:
  - **`SessionStart` hook** (`.claude/settings.json`, matcher `startup|resume|compact`) runs
    `tools/loop_state.py --session-start`: the machine-computed loop state is *injected into
    the agent's context* at every session start, resume, and compaction — deterministic
    re-orientation after any kind of session death.
  - **`tools/loop_runner.py`** (+ `runners/agent_loop.bat`) — the code-driven outer loop for
    unattended runs: CODE recomputes the state each pass and hands a fresh `claude -p` exactly
    ONE transition; stops at DONE or the COMMIT user gate, capped passes. The loop never lives
    in the model's head, so it can't be forgotten. (The pattern good loop-agent repos use:
    artifact-derived state + hook injection + an outer driver; the agent is a worker, the
    queue is code.)

### Added (loop hardening #2 — "the loop is not a loop")
- **User findings now REOPEN the loop (findings.md).** User insight: after real-device testing
  surfaced issues, the loop didn't restart — a PASS verdict was terminal, findings lived only in
  conversation, and the user ended up hand-driving fixes. Now: report an issue → the agent
  appends a `- [ ] <date> <finding>` line to **`apps/<slug>/findings.md`** *before* fixing;
  `loop_state.py` treats any open box as a **FIX** state that overrides a PASS verdict, so the
  state machine itself demands fix → re-evaluate → check-off. Intake rule documented in
  AGENTS.md §D. This closes the loop's last conversational (non-artifact) edge:
  build → verify → deploy → **user tests → findings.md → FIX** → re-verify.
- **Launcher: `rotate` config — ambient slideshow.** `rotate: <seconds>` on a `fullscreen`
  app auto-advances the open fullscreen view to the next item (min 3 s; manual ↑/↓ still
  works) — built for rotating wallpapers (user request), works for any ambient display.
  Both launchers; wallpaper ships with `rotate: 20` + 5 seeded glowing wallpapers.
  **Gate:** scripted check `exports/verify_wallpaper_rotate.py` (footer 1/5→2/5 after one
  period); UI look stays a human-eyeballed acceptance line (no-build rule).

### Added
- **Launcher: `audio` field type — directly embedded playback.** A field with
  `type:"audio"` (a direct .mp3/.m4a/.wav URL, self-hostable under `worker/public/media/`)
  renders an inline `<audio controls>` player in the detail view, and the glasses get a
  D-pad-reachable **🔊 Play / pause** action — audio without leaving the app (vs `video`/
  `link`, which stay "open a URL"). Both launchers. From the daily-ritual session ("is it
  possible to directly embed audio…this is just link to YouTube"). **Gate:**
  `tools/check.py` now validates every config field type against the known set **and**
  asserts each rendered type is handled by BOTH launchers (string-marker parity).
- **Launcher: no more blank empty states.** An empty collection used to render a dead
  screen — worst on the glasses, where the user can't type their way out. Both launchers
  now show a bright "Nothing here yet" hint that says what to do next (control-page apps →
  "set it up on your phone"; add-apps → "add on phone/desktop"; readOnly feeds → "fed from
  your PC, tools/push.py"); the fullscreen view's `no image` got the same treatment. From
  user testing ("often it's empty and user cannot do anything… what helps if they see
  nothing on meta glass"). **Gate:** standing EMPTY-STATE line auto-appended to every
  `tools/evaluate.py` soft checklist (simulate an empty collection, screenshot both
  surfaces); UI rendering itself is judged there per the no-build rule.
- **Process: empty states are now part of Define + Evaluate.** `AGENTS.md`: every
  per-surface plan must state what the user sees when the collection is EMPTY (plan a
  hint or seeded starter content), and the evaluate step must simulate real user intents
  (fresh install / all deleted / not yet pushed), not just the happy path. Presets are the
  companion pattern: presentation-timer's control page gained one-tap 1/5/10/15/20-min
  preset chips + seeded paused preset timers (`apps/presentation-timer/seed.json`), so the
  glasses list is usable (Enter → ▶ Resume) before any setup. (The chips/seed are
  app-level; the Define/Evaluate rule is the kit-level half.)

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
