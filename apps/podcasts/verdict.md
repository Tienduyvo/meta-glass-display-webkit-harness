# Podcasts — evaluation verdict (2026-07-11)

## HARD gate — flowtest
PASS — all assertions green against local `wrangler dev` (feed via bulk, all fields
round-trip incl. `audio`/`pos`, check/fav persist, delete removes, bulk replace,
soft-delete + un-delete).

## SOFT gate — agent-judge (eval_drive assertions + DOM checks; template-level data)
- [x] Pipeline resolves show names → public RSS via iTunes Search (keyless), pulls the
      newest episodes with direct https MP3 enclosures + show notes; Apple top-charts
      discovery honors the standing 75/25 mix (template run: 4+1; live profile run:
      6+2 = exactly 25%). CDATA-wrapped feeds parse (bug found & fixed: a 1030-episode
      feed yielded 0 before unwrapping CDATA in strip_tags).
- [x] Glasses list: show name renders BIG (badge), episode title ticker-scrolls; Enter →
      detail with art, duration, focusable **🔊 Play / pause**, readable show notes
      (2358px scrolls in the 502px viewport via progressive ↓), ✓/★/✕ actions; → =
      dismiss-and-next (eval_drive PASS on list, detail, dismiss).
- [x] Phone dashboard: episode cards (art, show chip, notes expand on tap) grouped
      My shows / Discover; tapping ▶ activates the persistent bottom player (asserted:
      playerbar visible + audio src set); positions PATCH to `pos` every 15 s and on
      pause — cards show "resumes at m:ss", replay resumes.
- [x] STANDING — EMPTY STATE: worded card on the dashboard ("ask Claude to add shows…");
      glasses get the launcher's fed-from-PC hint; template seed ships content.
- [x] Repo stays template-level: committed `shows.json`/`seed.json` generated with
      `--template` (generic shows); the user's real shows live only in the private
      profile scope.

## Known limits (stated in acceptance)
- Playback lives while the web app is open; display-sleep behavior awaits the owner's
  on-device test (decides a phase-2 persistent glasses player).
- Resume positions are dashboard-side; the glasses generic player starts from 0:00.

**Overall: PASS** (both halves green).

## Addendum — search & follow (owner ask, same day)
- [x] Dashboard search: one box filters loaded episodes instantly (asserted 4→2 on a
      term) AND searches the full open directory (iTunes via JSONP — endpoint lacks
      CORS but supports callback=); results show art/genre/episode count with a
      ＋ Follow button that appends the show to the PRIVATE profile row via the normal
      collection API (asserted: profile scope gained the followed show). Episodes
      arrive with the next pipeline run — stated in the UI status line.

<!-- Share-asked: the star/share/contribute hand-off was made to the user (loop SHARE step). -->
