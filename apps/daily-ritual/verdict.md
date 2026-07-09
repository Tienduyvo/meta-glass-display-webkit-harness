# Daily Ritual — evaluation verdict: PASS

Result: PASS (hard flowtest + soft screenshot gate both green)

Date: 2026-07-09 · evaluated against local `wrangler dev` (seeded with apps/daily-ritual/seed.json,
15 items) · screenshots in `exports/dr_*.png` · driver: `exports/eval_daily_ritual.py`
(Playwright + Edge, glasses 600×600 `#glass` + phone 390×800).

## HARD gate — flowtest

**PASS** — all 14 assertions green (create/list/round-trip text·media·slot, check-off persists,
favorite persists, delete, bulk replace, soft-delete + un-delete).

## SOFT gate — acceptance lines vs screenshots

- [x] **Morning first, big bright text, D-pad walk** — `dr_glass_list_top.png`: all visible top
  rows are 🌅 Morning; the affirmation text is the large bold white element of each row; footer
  shows `Daily Ritual · 15`; ArrowDown walked focus row-by-row (focused-row text printed each step).
- [x] **Media item → Enter → ▶ Open Play** — `dr_glass_detail_media.png`: detail shows the
  ▶ Open link and the focused `▶ Open Play` action (glow ring); URL verified live via YouTube
  oEmbed at build time (all 5 seed links returned 200 + title).
- [x] **Phone add bar with 🌅/🌙 tag** — `dr_phone_addbar.png`: gratitude text typed in the add
  bar, `slot` input pre-filled with the default `🌅 Morning` (editable to `🌙 Night`); slot
  round-trip covered by flowtest.
- [x] **No-media item shows no broken affordance** — `dr_glass_detail_nomedia.png`: only
  `✓ Check off` and `★ Favorite` actions; no ▶ Open. (Cosmetic: the empty `media` label still
  renders in the card — harmless, noted for a later polish pass.)
- [x] **Check on glasses persists + syncs** — `dr_glass_after_check.png`: after Enter the action
  reads `✓ Uncheck`; `dr_phone_list.png`/`dr_phone_addbar.png`: the same item renders checked
  (✓ highlighted, strikethrough) on the phone surface.
- [x] **Seed push renders** — `push.py daily_ritual --replace --file seed.json` → HTTP 200
  `upserted: 15`; launcher footer confirms 15 rows.

## Round 2 (2026-07-09, same day) — audio field + empty states

Re-evaluated after the kit gained the `audio` field type and empty-state hints
(driver: `exports/eval_daily_ritual2.py`, screenshots `exports/dr2_*.png`):

- [x] **Embedded audio plays inline** — `dr2_glass_audio_detail.png`: the seeded "Spoken:"
  item renders an `<audio>` player in the detail card; the focused **🔊 Play / pause Audio**
  action started real playback headlessly (element state after Enter: `paused: false,
  currentTime: 0.56s`, no error). Phone renders the same inline player
  (`dr2_phone_audio_detail.png`). Sample is self-hosted at `/media/affirmation-sample.wav`.
- [x] **STANDING — EMPTY STATE** — simulated with `bulk --replace []`:
  `dr2_glass_empty.png` (glasses) shows "✨ Nothing here yet. Add items on your phone or
  desktop — they appear here to use hands-free."; `dr2_phone_empty.png` shows the add bar +
  "Add your first item above ⬆". No blank views. Seed restored after (16 items).
- [x] **Hard gate re-run** — flowtest PASS including the new `audio` field round-trip
  (14/14 assertions, via the verify hook on every edit).

## Round 3 (2026-07-09) — real-device finding: ▶ Open Play dead on the glasses

User tested on the actual glasses: the YouTube ▶ Open Play action did nothing. Root cause was
kit-level: `openURL()` didn't handle `window.open` returning `null` (blocked popup — the normal
webview condition on the glasses), and round-1 verification had only checked that the URL was
live and the button rendered — the tap itself was never driven end-to-end.

- [x] **Repro then fix** — `exports/repro_open_play.py` simulates the blocked-popup device:
  before the fix, Enter on ▶ Open Play changed nothing (`pages 1 -> 1, url changed: False`);
  after adding the `location.href` fallback, the same tap lands on
  `https://www.youtube.com/watch?v=ZssjZnsN4Gg` (`url changed: True`). Fixed in both
  launchers, deployed.
- [x] **On-device retest: YouTube confirmed NOT viable on the glasses** — even with the
  popup-fallback fix, the glasses webview won't open YouTube (device limitation, matches the
  kit's "video playback is device-limited" rule). Resolution shipped: three self-hosted
  ~2-min TTS programs (`/media/morning-power.wav`, `morning-calm.wav`, `night-gratitude.wav`)
  seeded as 🎧 items — verified playing in-app on the glasses surface
  (`exports/verify_audio_programs.py`: `paused: false, currentTime: 1.8s`); YouTube links
  removed from the seed per user feedback ("ritual should be a couple of minutes"). The
  openURL fix stays (it repairs ▶ Open on phones/webviews that block popups).

## Verdict

Both halves green → **PASS** (rounds 1 and 2); round-3 fix verified by scripted repro,
pending the user's on-device confirmation. Known cosmetic nit (empty `media` label on
no-media details) is kit-level rendering, not app-blocking.
